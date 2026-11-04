class CreativeReject(RuntimeError):
    """Expected fail-closed rejection of a weak, unsafe, or incomplete creative candidate."""

class StoryBackgroundPreflightReject(CreativeReject):
    """Missing verified scene art; structured evidence never implies approval."""

    def __init__(self, report):
        if not isinstance(report, dict) or report.get("status") != "blocked":
            raise ValueError("Background preflight rejection requires blocked report")
        self.report = {
            "status": "blocked",
            "reason": str(report.get("reason") or "missing_backgrounds"),
            "shot_count": report.get("shot_count"),
            "missing_shots": list(report.get("missing_shots") or []),
            "publication_approval": False,
            "semantic_quality": "not_verified",
        }
        super().__init__(
            "Fiction background preflight rejected before rendering: "
            + self.report["reason"])
