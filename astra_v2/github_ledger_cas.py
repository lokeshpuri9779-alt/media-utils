"""GitHub state-ref compare-and-swap adapter for ASTRA's storage ledger.

Uses GitHub's Git Data REST API. Ref updates MUST be non-force fast-forwards,
so a competing writer's new commit cannot be overwritten. The adapter is
opt-in and does not publish, upload media, or create storage capacity.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from astra_v2.github_storage_ledger import transact, validate

LEDGER_PATH = "astra-storage-ledger.json"


class GitHubLedgerCAS:
    def __init__(self, repository, *, branch="astra-state", token=None):
        if not isinstance(repository, str) or len(repository.split("/")) != 2:
            raise ValueError("invalid_repository")
        if not isinstance(branch, str) or not branch or "/" in branch:
            raise ValueError("invalid_branch")
        self.repository = repository
        self.branch = branch
        self.token = token if token is not None else os.environ.get("GH_TOKEN", "")
        if not self.token:
            raise RuntimeError("github_token_required")
        self.root = "https://api.github.com/repos/" + repository

    def _api(self, method, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.root + path, data=body, method=method,
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def read(self):
        branch = urllib.parse.quote(self.branch, safe="")
        ref = self._api("GET", "/git/ref/heads/" + branch)
        sha = ref["object"]["sha"]
        commit = self._api("GET", "/git/commits/" + sha)
        tree = self._api("GET", "/git/trees/" + commit["tree"]["sha"])
        matches = [entry for entry in tree.get("tree", [])
                   if entry.get("path") == LEDGER_PATH and entry.get("type") == "blob"]
        if len(matches) != 1:
            raise RuntimeError("storage_ledger_not_initialized")
        blob = self._api("GET", "/git/blobs/" + matches[0]["sha"])
        if blob.get("encoding") != "base64":
            raise RuntimeError("unexpected_ledger_encoding")
        import base64
        state = json.loads(base64.b64decode(blob["content"]).decode("utf-8"))
        return sha, validate(state)

    def compare_and_swap(self, expected_sha, state):
        validate(state)
        # The new commit's only parent is the read version. A non-force ref
        # update will reject it if another writer advanced the branch.
        parent = self._api("GET", "/git/commits/" + expected_sha)
        blob = self._api("POST", "/git/blobs", {
            "content": json.dumps(state, sort_keys=True, separators=(",", ":")),
            "encoding": "utf-8"})
        tree = self._api("POST", "/git/trees", {
            "base_tree": parent["tree"]["sha"],
            "tree": [{"path": LEDGER_PATH, "mode": "100644",
                      "type": "blob", "sha": blob["sha"]}]})
        commit = self._api("POST", "/git/commits", {
            "message": "ASTRA storage reservation ledger update",
            "tree": tree["sha"], "parents": [expected_sha]})
        try:
            self._api("PATCH", "/git/refs/heads/" + urllib.parse.quote(self.branch, safe=""),
                      {"sha": commit["sha"], "force": False})
        except urllib.error.HTTPError as exc:
            if exc.code in (409, 422):
                return False
            raise
        return True

    def transaction(self, transform, *, attempts=5):
        return transact(self.read, self.compare_and_swap, transform, attempts=attempts)
