"""GitHub-hosted local story generation for ASTRA caption-only Shorts.

Runs a small Apache-2.0 GGUF model on the GitHub Actions CPU runner.
No hosted inference API, Gemini, vidIQ, or paid AI service is called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROLES = ["hook", "stakes", "attempt", "setback", "discovery", "climax", "payoff"]
MODEL_REPO = "Qwen/Qwen3-4B-GGUF"
MODEL_FILE = "Qwen3-4B-Q4_K_M.gguf"

LANES = {
    "surprise": "A surprising but emotionally satisfying microfiction story.",
    "mystery": "A fair-play mystery with clues planted early and a logical reveal.",
    "sci-fi": "A grounded science-fiction microfiction built around one striking idea.",
    "emotional": "An emotionally resonant story with a specific human choice and earned payoff.",
    "thriller": "A tense, escalating thriller with a clear ticking clock and a clever resolution.",
    "moral_dilemma": "A moral dilemma where the protagonist's choice changes the meaning of the story.",
}


def _words(value: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", str(value).lower())


def _fingerprint(premise: str) -> str:
    tokens = _words(premise)
    normalized = " ".join(tokens)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def validate_candidate(data: dict, history: list[dict] | None = None) -> dict:
    """Validate the text-only seven-beat story before it enters the render path."""
    if not isinstance(data, dict):
        raise ValueError("Model output must be a JSON object")
    title = " ".join(str(data.get("title") or "").split())
    premise = " ".join(str(data.get("premise") or "").split())
    question = " ".join(str(data.get("question") or "").split())
    scenes = data.get("performance_scenes")
    if not 8 <= len(title) <= 80:
        raise ValueError("Title must be 8–80 characters")
    if not 35 <= len(_words(premise)) <= 90:
        raise ValueError("Premise must be 35–90 words")
    if not isinstance(scenes, list) or len(scenes) != 7:
        raise ValueError("Exactly seven performance_scenes are required")

    speech_lines = []
    for index, (scene, role) in enumerate(zip(scenes, ROLES), start=1):
        if not isinstance(scene, dict) or scene.get("role") != role:
            raise ValueError(f"Scene {index} must have role {role}")
        speech = " ".join(str(scene.get("speech") or "").split())
        count = len(_words(speech))
        if not 6 <= count <= 14:
            raise ValueError(f"Scene {index} narration must contain 6–14 words")
        speech_lines.append(speech)

    if not 8 <= len(_words(question)) <= 20 or not question.endswith("?"):
        raise ValueError("Story-specific engagement question must be 8–20 words and end with ?")
    if re.search(r"\b(like and subscribe|smash that like|follow for more|comment below)\b", question, re.I):
        raise ValueError("Engagement question must be story-specific, not a generic CTA")

    all_speech = " ".join(speech_lines + [question])
    total_words = len(_words(all_speech))
    if not 65 <= total_words <= 85:
        raise ValueError(f"Complete spoken script must be 65–85 words; got {total_words}")
    normalized_lines = [re.sub(r"[^a-z0-9 ]", "", line.lower()) for line in speech_lines]
    if len(set(normalized_lines)) != len(normalized_lines):
        raise ValueError("Repeated narration lines detected")
    forbidden = (
        "it was all a dream", "woke up and realized", "it was a simulation",
        "the real monster was", "and then everything changed",
    )
    if any(phrase in all_speech.lower() for phrase in forbidden):
        raise ValueError("Overused or disallowed plot phrase detected")

    premise_fp = _fingerprint(premise)
    premise_tokens = set(_words(premise))
    for prior in (history or [])[-100:]:
        old = set(_words(prior.get("premise", "")))
        if not old:
            continue
        overlap = len(premise_tokens & old) / max(1, len(premise_tokens | old))
        if overlap >= 0.48 or prior.get("fingerprint") == premise_fp:
            raise ValueError("Story premise is too similar to a recent ASTRA story")

    return {
        "title": title,
        "premise": premise,
        "question": question,
        "performance_scenes": [
            {"role": role, "speech": speech}
            for role, speech in zip(ROLES, speech_lines)
        ],
        "word_count": total_words,
        "premise_fingerprint": premise_fp,
    }


def _load_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    rows.append(item)
            except json.JSONDecodeError:
                continue
    return rows


def _build_prompt(lane: str, history: list[dict], seed: int) -> str:
    recent = [
        {"title": row.get("title", ""), "premise": row.get("premise", "")}
        for row in history[-25:]
    ]
    return (
        "Write one completely original English microfiction YouTube Short for RAYVAN. "
        "This is narration plus captions only: no visual descriptions, no animation directions. "
        f"Creative lane: {LANES[lane]} "
        "The story must have a concrete first-line hook, clear stakes, a failed attempt, "
        "a meaningful setback, a causal discovery, a decisive climax, and an earned payoff. "
        "Use exactly these seven role values in this exact order: " + ", ".join(ROLES) + ". "
        "Each speech line must have 6–14 words. The combined seven lines plus the final "
        "engagement question must total 65–85 spoken words, suitable for a 28–40 second Short. "
        "Make every beat advance the cause-and-effect chain. Avoid generic moral lessons, "
        "random twists, dream endings, predictable misunderstandings, and filler. "
        "The final question must be specific to the story and invite a genuine viewer opinion; "
        "it is spoken aloud, so keep it concise. Do not ask people to like, subscribe, or follow. "
        "Do not imitate or adapt existing copyrighted stories, franchises, characters, or plots. "
        "Use fresh names and a self-contained fictional premise. "
        "Do not repeat or closely imitate these recent ASTRA premises: "
        + json.dumps(recent, ensure_ascii=False) +
        ". Return only valid JSON with keys: title, premise, question, performance_scenes. "
        "performance_scenes must be an array of seven objects, each with only role and speech. "
        "No markdown fences, no commentary. /no_think "
        f"Creative seed: {seed}."
    )


def generate(output_path: str, history_path: str, lane: str = "surprise",
             seed: int = 1, model_path: str | None = None) -> dict:
    if lane not in LANES:
        raise ValueError("Unsupported creative lane")
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    model_file = model_path or hf_hub_download(
        repo_id=MODEL_REPO, filename=MODEL_FILE
    )
    history_file = Path(history_path)
    history = _load_history(history_file)
    llm = Llama(
        model_path=model_file, n_ctx=4096, n_threads=2,
        n_batch=256, verbose=False,
    )
    last_error = None
    validated = None
    for attempt in range(3):
        prompt = _build_prompt(lane, history, seed + attempt)
        result = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a professional short-form fiction writer. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.78 + attempt * 0.04,
            top_p=0.85,
            max_tokens=1400,
        )
        raw = result["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(raw)
            validated = validate_candidate(parsed, history)
            break
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            last_error = exc
    if validated is None:
        raise RuntimeError(f"Local model failed story quality gates after 3 attempts: {last_error}")

    candidate = {
        "schema_version": 1,
        "kind": "github_local_caption_story",
        "source": "qwen3_4b_local_github_actions",
        "content_id": "rayvan-" + validated["premise_fingerprint"][:20],
        "title": validated["title"],
        "premise": validated["premise"],
        "question": validated["question"],
        "performance_scenes": validated["performance_scenes"],
        "word_count": validated["word_count"],
        "premise_fingerprint": validated["premise_fingerprint"],
        "approved": False,
        "production_ready": False,
        "published": False,
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")

    history_file.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "title": candidate["title"],
        "premise": candidate["premise"],
        "fingerprint": candidate["premise_fingerprint"],
    }
    with history_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return candidate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--history", default="data/story_history.jsonl")
    parser.add_argument("--lane", choices=sorted(LANES), default="surprise")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--model-path")
    args = parser.parse_args(argv)
    candidate = generate(args.output, args.history, args.lane, args.seed, args.model_path)
    print(json.dumps({
        "content_id": candidate["content_id"],
        "title": candidate["title"],
        "word_count": candidate["word_count"],
        "quality_gate": "passed",
        "approved": False,
        "published": False,
    }, indent=2))


if __name__ == "__main__":
    main()
