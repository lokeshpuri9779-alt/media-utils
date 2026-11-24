"""GitHub-hosted local story generation for ASTRA caption-only Shorts.

Runs a small Apache-2.0 GGUF model on the GitHub Actions CPU runner.
No hosted inference API, Gemini, vidIQ, or paid AI service is called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

ROLES = ["hook", "stakes", "attempt", "setback", "discovery", "climax", "payoff"]
PUZZLE_ROLES = ["challenge", "thinking_pause", "answer", "explanation"]
FACT_ROLES = ["curiosity_hook", "surprising_fact", "explanation", "why_it_matters"]
QUIZ_ROLES = ["quiz_hook", "question_or_options", "answer_reveal", "explanation"]
NEWS_ROLES = ["news_hook", "what_changed", "context", "why_it_matters"]
STRUCTURES = {
    **{lane: PUZZLE_ROLES for lane in ("brain_puzzle", "logic_puzzle", "riddle", "guess_the_number")},
    **{lane: QUIZ_ROLES for lane in ("quick_quiz", "spot_the_lie", "two_truths_one_lie", "india_gk")},
    **{lane: FACT_ROLES for lane in (
        "weird_facts", "science_explained", "history_gk", "geography_gk", "world_gk",
        "myth_vs_fact", "psychology", "money_business", "tech_explained", "space_facts",
        "nature_facts", "human_body", "inventions", "mini_case_study", "ranked_countdown", "what_if"
    )},
    **{lane: NEWS_ROLES for lane in ("current_news", "trending_topics")},
}
STRUCTURE_NAMES = {
    **{lane: "puzzle_challenge_reveal" for lane in
       ("brain_puzzle", "logic_puzzle", "riddle")},
    "guess_the_number": "estimation_challenge_reveal",
    **{lane: "quiz_question_reveal" for lane in
       ("quick_quiz", "spot_the_lie", "two_truths_one_lie", "india_gk")},
    **{lane: "fact_explainer" for lane in (
        "weird_facts", "science_explained", "history_gk", "geography_gk",
        "world_gk", "myth_vs_fact", "psychology", "money_business",
        "tech_explained", "space_facts", "nature_facts", "human_body",
        "inventions", "mini_case_study", "ranked_countdown", "what_if"
    )},
    **{lane: "news_context_impact" for lane in ("current_news", "trending_topics")},
}
MODEL_REPO = "Qwen/Qwen3-4B-GGUF"
MODEL_REVISION = "bc640142c66e1fdd12af0bd68f40445458f3869b"
MODEL_FILE = "Qwen3-4B-Q4_K_M.gguf"
STOPWORDS = set("a an and are as at be been before but by for from had has have he her his in into is it its of on or our she that the their them then there they this to was were when where which while who with would you your".split())

SOURCED_FACTUAL_LANES = {
    "weird_facts", "science_explained", "history_gk", "geography_gk",
    "world_gk", "myth_vs_fact", "psychology", "money_business",
    "tech_explained", "india_gk", "space_facts", "nature_facts",
    "human_body", "inventions", "mini_case_study", "ranked_countdown",
    "guess_the_number", "quick_quiz", "spot_the_lie", "two_truths_one_lie",
    "what_if", "current_news", "trending_topics",
}

LANES = {
    "surprise": "Original microfiction with a surprising, earned payoff.",
    "mystery": "A fair-play mystery with clues planted early and a logical reveal.",
    "sci-fi": "Grounded science-fiction built around one striking, understandable idea.",
    "emotional": "An emotionally resonant story with a specific human choice and earned payoff.",
    "thriller": "A tense, escalating thriller with a ticking clock and clever resolution.",
    "moral_dilemma": "A moral dilemma where the protagonist's choice changes the meaning of the story.",
    "weird_facts": "A verified-feeling, genuinely surprising true fact explained clearly; never invent a fact.",
    "science_explained": "A fascinating science concept explained simply with an everyday analogy.",
    "history_gk": "A memorable world-history knowledge bite with context and a surprising detail.",
    "geography_gk": "A surprising geography fact about places, borders, nature, or the planet.",
    "world_gk": "A high-value general-knowledge explainer across world culture, civics, and knowledge.",
    "myth_vs_fact": "Correct a popular misconception by clearly separating myth from established fact.",
    "brain_puzzle": "A fair, solvable brain teaser; give viewers time to think before revealing the answer.",
    "logic_puzzle": "A compact logic puzzle with enough information for one defensible solution.",
    "riddle": "A clever, original riddle with a satisfying, unambiguous answer.",
    "quick_quiz": "A fast three-question quiz with clear answers and a memorable explanation.",
    "psychology": "An evidence-aware psychology insight; distinguish research from speculation.",
    "money_business": "A practical business, money, or economics concept explained with a simple example.",
    "tech_explained": "A useful technology or AI concept explained accurately for a general audience.",
    "india_gk": "A memorable India-focused GK bite spanning geography, history, culture, or civics.",
    "space_facts": "An astonishing but accurate space and astronomy fact explained simply.",
    "nature_facts": "A surprising animal, wildlife, or nature fact with a clear explanation.",
    "human_body": "An accurate human-body or health-science explainer; avoid medical advice.",
    "inventions": "The surprising origin, mechanism, or impact of an invention or engineering idea.",
    "spot_the_lie": "A three-statement fact game with exactly one false statement and a clear reveal.",
    "two_truths_one_lie": "A fast two-truths-and-one-lie challenge using verifiable statements.",
    "guess_the_number": "A surprising numerical estimation challenge with a defensible sourced answer.",
    "what_if": "A thought-provoking what-if scenario grounded in plausible science or clearly labelled fiction.",
    "mini_case_study": "A compact real-world business, science, or history case with a lesson supported by facts.",
    "ranked_countdown": "A short ranked countdown with clear criteria and accurate, non-arbitrary ranking.",
    "current_news": "A concise explainer of a genuinely recent news development using supplied sources only.",
    "trending_topics": "A useful explainer of a currently trending topic using supplied trend and news sources only.",
}


def _words(value: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", str(value).lower())


def _fingerprint(premise: str) -> str:
    tokens = _words(premise)
    normalized = " ".join(tokens)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _content_tokens(premise: str) -> set[str]:
    return {token for token in _words(premise) if len(token) > 2 and token not in STOPWORDS}


ENGAGEMENT_FORMATS = {
    "brain_puzzle": ["timed_challenge", "predict_then_reveal", "spot_the_flaw", "memory_test"],
    "logic_puzzle": ["timed_challenge", "predict_then_reveal", "elimination_game"],
    "riddle": ["mystery_question", "clue_by_clue", "predict_then_reveal"],
    "quick_quiz": ["three_round_quiz", "confidence_check", "score_yourself"],
    "spot_the_lie": ["find_the_lie", "evidence_reveal", "confidence_check"],
    "two_truths_one_lie": ["find_the_lie", "three_claims_one_fake", "evidence_reveal"],
    "guess_the_number": ["estimation_challenge", "closest_wins", "predict_then_reveal"],
    "weird_facts": ["curiosity_gap", "myth_buster", "unexpected_connection", "explain_the_why"],
    "science_explained": ["what_if", "everyday_mystery", "unexpected_connection"],
    "history_gk": ["history_mystery", "forgotten_detail", "timeline_twist"],
    "geography_gk": ["map_mystery", "borderline_impossible", "geography_surprise"],
    "india_gk": ["india_quiz", "history_mystery", "myth_buster", "unexpected_connection"],
    "current_news": ["what_changed", "why_it_matters", "fact_check"],
    "trending_topics": ["trend_explainer", "what_changed", "fact_check"],
    "what_if": ["scenario_simulation", "choose_the_outcome", "consequence_chain"],
    "psychology": ["self_test", "prediction", "behaviour_reveal"],
    "money_business": ["business_case", "choose_the_strategy", "prediction"],
}
CREATIVE_TONES = ["curious", "playful", "tense", "awe-filled", "thoughtful", "urgent-but-calm"]
OPENING_PATTERNS = ["cold_open_question", "bold_contradiction", "strange_detail", "stakes_first", "direct_challenge", "unexpected_number"]
PAYOFF_TYPES = ["clear_explanation", "logical_reveal", "practical_lesson", "surprising_connection", "consequence", "emotional_resolution"]

def _rotate(options: list[str], seed: int) -> str:
    return options[abs(int(seed)) % len(options)]

def creative_direction(lane: str, seed: int) -> dict:
    """Select a reproducible creative treatment independent of the subject lane."""
    return {
        "engagement_format": select_engagement_format(lane, seed),
        "tone": _rotate(CREATIVE_TONES, seed // 3),
        "opening_pattern": _rotate(OPENING_PATTERNS, seed // 5),
        "payoff_type": _rotate(PAYOFF_TYPES, seed // 7),
    }

DEFAULT_ENGAGEMENT_FORMATS = [
    "mystery_question", "choose_your_side", "unexpected_connection",
    "predict_then_reveal", "mini_case_study", "counterintuitive_explanation",
]

def _candidate_json_schema(lane: str = "surprise") -> dict:
    """Constrain local decoding to the lane-specific scene structure."""
    roles = STRUCTURES.get(lane, ROLES)
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "premise": {"type": "string"},
            "question": {"type": "string"},
            "performance_scenes": {
                "type": "array",
                "minItems": len(roles),
                "maxItems": len(roles),
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string", "enum": roles},
                        "speech": {"type": "string"},
                    },
                    "required": ["role", "speech"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["title", "premise", "question", "performance_scenes"],
        "additionalProperties": False,
    }

def select_engagement_format(lane: str, seed: int) -> str:
    """Deterministically rotate interaction patterns without adding dependencies."""
    options = ENGAGEMENT_FORMATS.get(lane, DEFAULT_ENGAGEMENT_FORMATS)
    return options[abs(int(seed)) % len(options)]


def _fallback_title(title: str, premise: str) -> str:
    """Recover malformed titles from a valid premise without fragile word slicing."""
    title = " ".join(str(title or "").split()).strip(" .,:;-")
    if 8 <= len(title) <= 80:
        return title
    # A normal multiword title can be shortened at a word boundary.
    if len(title) > 80 and " " in title:
        shortened = title[:80].rsplit(" ", 1)[0].strip(" .,:;-")
        if len(shortened) >= 8:
            return shortened
    # Discard empty, too-short, or unbroken oversized model output.
    clean = re.sub(r"[^A-Za-z0-9' -]", " ", str(premise or ""))
    words = clean.split()
    fallback = " ".join(word.capitalize() for word in words[:10])
    fallback = fallback[:80].rsplit(" ", 1)[0].strip(" .,:;-")
    if len(fallback) < 8:
        fallback = "A Curious Story"
    return fallback[:80]


def validate_candidate(data: dict, history: list[dict] | None = None, lane: str = "surprise") -> dict:
    """Validate the text-only seven-beat Short before it enters the render path."""
    if not isinstance(data, dict):
        raise ValueError("Model output must be a JSON object")
    premise = " ".join(str(data.get("premise") or "").split())
    title = " ".join(str(data.get("title") or "").split())
    question = " ".join(str(data.get("question") or "").split())
    scenes = data.get("performance_scenes")
    expected_roles = STRUCTURES.get(lane, ROLES)
    compact_structure = len(expected_roles) <= 4
    min_scene_words, max_scene_words = (10, 18) if compact_structure else (6, 14)
    title = _fallback_title(title, premise)
    if not 8 <= len(title) <= 80:
        raise ValueError("Title must be 8–80 characters")
    if not isinstance(scenes, list) or len(scenes) != len(expected_roles):
        raise ValueError(f"Expected exactly {len(expected_roles)} performance_scenes for {lane}")

    speech_lines = []
    for index, (scene, role) in enumerate(zip(scenes, expected_roles), start=1):
        if not isinstance(scene, dict) or scene.get("role") != role:
            raise ValueError(f"Scene {index} must have role {role}")
        speech = " ".join(str(scene.get("speech") or "").split())
        count = len(_words(speech))
        if not min_scene_words <= count <= max_scene_words:
            raise ValueError(f"Scene {index} narration must contain {min_scene_words}–{max_scene_words} words")
        speech_lines.append(speech)

    # Small local models sometimes underfill metadata fields. The spoken script is
    # the source of truth, so recover a missing/short premise from its narration.
    if not 35 <= len(_words(premise)) <= 90:
        premise = " ".join(speech_lines)
        premise = " ".join(premise.split()[:90])
        if not 35 <= len(_words(premise)) <= 90:
            raise ValueError("Premise must be recoverable as 35–90 words")

    if not 8 <= len(_words(question)) <= 20 or not question.endswith("?"):
        raise ValueError("Audience engagement question must be 8–20 words and end with ?")
    if re.search(r"\b(like and subscribe|smash that like|follow for more|comment below)\b", question, re.I):
        raise ValueError("Engagement question must be content-specific, not a generic CTA")

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
    premise_tokens = _content_tokens(premise)
    for prior in (history or [])[-100:]:
        old = _content_tokens(prior.get("premise", ""))
        if not old:
            continue
        overlap = len(premise_tokens & old) / max(1, len(premise_tokens | old))
        if overlap >= 0.48 or prior.get("fingerprint") == premise_fp:
            raise ValueError("Content premise is too similar to a recent ASTRA Short")

    return {
        "title": title,
        "premise": premise,
        "question": question,
        "performance_scenes": [
            {"role": role, "speech": speech}
            for role, speech in zip(expected_roles, speech_lines)
        ],
        "word_count": total_words,
        "premise_fingerprint": premise_fp,
    }



def find_duplicate_premises(candidates: list[dict], history: list[dict] | None = None,
                            threshold: float = 0.48) -> list[dict]:
    """Find exact or high-overlap premises against history and earlier accepted batch items."""
    if not 0.0 < threshold <= 1.0:
        raise ValueError("Similarity threshold must be in (0, 1]")
    accepted_prior = list(history or [])
    duplicates = []
    for index, candidate in enumerate(candidates):
        premise = str(candidate.get("premise") or "")
        tokens = _content_tokens(premise)
        fingerprint = str(candidate.get("premise_fingerprint") or candidate.get("fingerprint") or "")
        if not premise.strip() or not tokens:
            duplicates.append({
                "candidate_index": index, "prior_index": None,
                "similarity": 1.0, "reason": "premise_missing",
            })
            continue
        duplicate = None
        for prior_index, prior in enumerate(accepted_prior):
            prior_fingerprint = str(
                prior.get("premise_fingerprint") or prior.get("fingerprint") or ""
            )
            prior_premise = str(prior.get("premise") or "")
            prior_tokens = _content_tokens(prior_premise)
            if fingerprint and fingerprint == prior_fingerprint:
                duplicate = {
                    "candidate_index": index, "prior_index": prior_index,
                    "similarity": 1.0, "reason": "exact_fingerprint",
                }
                break
            if not prior_tokens:
                continue
            overlap = len(tokens & prior_tokens) / max(1, len(tokens | prior_tokens))
            if overlap >= threshold:
                duplicate = {
                    "candidate_index": index, "prior_index": prior_index,
                    "similarity": round(overlap, 3), "reason": "premise_token_overlap",
                }
                break
        if duplicate:
            duplicates.append(duplicate)
        else:
            # Rejected duplicates must not poison comparisons for later candidates.
            accepted_prior.append(candidate)
    return duplicates


def accepted_unique_candidates(candidates: list[dict], history: list[dict] | None = None,
                               threshold: float = 0.48) -> tuple[list[dict], list[dict]]:
    """Return accepted candidates and duplicate diagnostics using the shared gate."""
    duplicates = find_duplicate_premises(candidates, history, threshold)
    rejected_indices = {item["candidate_index"] for item in duplicates}
    accepted = [
        candidate for index, candidate in enumerate(candidates)
        if index not in rejected_indices
    ]
    return accepted, duplicates


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


def _build_prompt(lane: str, history: list[dict], seed: int,
                  sources: list[dict] | None = None,
                  retry_feedback: str | None = None) -> str:
    recent = [
        {"title": row.get("title", ""), "premise": row.get("premise", "")}
        for row in history[-5:]
    ]
    source_block = json.dumps(sources or [], ensure_ascii=False)
    factual = lane in SOURCED_FACTUAL_LANES
    if factual:
        evidence_rule = (
            "Use ONLY the supplied source pack for factual claims. Every concrete factual claim, "
            "number, date, study result, historical detail, or named example must be supported "
            "by the supplied evidence. Cross-check the central claim against both independent "
            "publishers; if only one source supports a detail, attribute it clearly and qualify "
            "it as single-source. Do not invent causes, quotes, statistics, or outcomes. If "
            "sources disagree or are too thin, state only what is supported and omit the rest. "
            "Mention a publisher/source naturally in narration. For news, do not present an old "
            "story as breaking news. "
        )
    else:
        evidence_rule = (
            "Do not imitate or adapt existing copyrighted stories, franchises, characters, or plots. "
            "Use fresh names and a self-contained fictional premise. Clearly label hypothetical "
            "scenarios as hypothetical rather than presenting them as observed fact. "
        )
    puzzle_rule = (
        "For puzzles and riddles, state all necessary conditions, make the answer logically "
        "deducible, and place the answer after a clear thinking pause such as 'Lock in your guess'. "
        "Never use an ambiguous trick answer. "
        if lane in {"brain_puzzle", "logic_puzzle", "riddle", "quick_quiz", "spot_the_lie", "two_truths_one_lie", "guess_the_number"} else ""
    )
    roles = STRUCTURES.get(lane, ROLES)
    compact_structure = len(roles) <= 4
    scene_min, scene_max = (10, 18) if compact_structure else (6, 14)
    structure_name = STRUCTURE_NAMES.get(lane, "seven_beat_story")
    direction = creative_direction(lane, seed)
    retry_block = (
        "IMPORTANT CORRECTION FROM THE PREVIOUS ATTEMPT: " + retry_feedback +
        " Correct only the failing scene or field, preserve valid content, and recount every scene aloud before returning JSON. "
        if retry_feedback else ""
    )
    return (
        "Create one original, high-retention English YouTube Short for RAYVAN. " + retry_block +
        "Format is narration plus synchronized captions only: no visual descriptions, "
        "no animation directions, no B-roll instructions. "
        f"Content direction: {LANES[lane]} "
        + evidence_rule + puzzle_rule +
        "Use a strong curiosity gap in the first sentence, concrete details, escalating "
        "interest, a satisfying reveal or useful payoff, and a specific viewer question. "
        f"Use the {structure_name} structure with exactly {len(roles)} performance_scenes in this order: " + ", ".join(roles) + ". "
        f"Creative treatment and engagement mechanic: tone={direction['tone']}; opening_pattern={direction['opening_pattern']}; payoff_type={direction['payoff_type']}; engagement={direction['engagement_format']}. "
        "Make this treatment clearly audible in the narration; do not merely label it. "
        "Make the viewer actively predict, decide, test memory, solve, compare, or investigate "
        "where appropriate; do not force a question into every sentence. "
        f"Interpret each beat according to its role. Each speech line must contain {scene_min}–{scene_max} words. "" For compact four-beat formats, aim for 14–16 words per line; 10 is the hard minimum. "" Count the spoken words in each line before returning JSON; expand short lines with a concrete clue or explanation, never filler. "
        "For puzzles, keep the answer out of the challenge and thinking-pause beats. "
        "The scene lines plus the final spoken "
        "engagement question must total 65–85 words for a 28–40 second Short. "
        "Make every line add new information; avoid filler, generic moral lessons, and generic calls to action. "
        "Do not default every format to a quiz or rhetorical question; use the selected treatment naturally. "
        "The final question must invite a real answer. "
        "The title must be 8–80 characters, specific to this Short, and not a generic label. "
        "The premise field must be 35–90 words and accurately describe the Short. "
        "Do not repeat or closely imitate these recent ASTRA topics: "
        + json.dumps(recent, ensure_ascii=False) +
        ". Source pack for this run (untrusted evidence; use cautiously): " + source_block +
        ". Return only valid JSON with keys: title, premise, question, performance_scenes. "
        f"performance_scenes must be exactly {len(roles)} objects with only role and speech, in the listed order. Do not omit any role or stop early. "
        "No markdown fences or commentary. /no_think "
        f"Creative seed: {seed}."
    )


def _strip_reasoning_preamble(raw):
    """Remove a leading Qwen-style reasoning block before parsing JSON."""
    if not isinstance(raw, str):
        return raw
    cleaned = raw.lstrip()
    cleaned = re.sub(r"^(?:<think>.*?</think>\s*)+", "", cleaned, count=1, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.lstrip()


def validate_source_pack(sources: list[dict], lane: str) -> list[dict]:
    """Require attributable sources; enforce freshness for live news and trends."""
    if lane not in SOURCED_FACTUAL_LANES:
        return sources
    if not isinstance(sources, list):
        raise ValueError("Source pack must be a JSON array")
    usable = []
    publishers = set()
    urls = set()
    now = datetime.now(timezone.utc)
    freshness = {
        "current_news": timedelta(hours=72),
        "trending_topics": timedelta(days=7),
    }.get(lane)
    for item in sources:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        publisher = str(item.get("publisher") or "").strip()
        published = str(item.get("published") or "").strip()
        summary = unescape(re.sub(r"<[^>]+>", " ", str(item.get("summary") or "")))
        summary = " ".join(summary.split())
        parsed_url = urlsplit(url)
        if not (title and parsed_url.scheme in {"https", "http"} and parsed_url.netloc
                and publisher and published and len(summary) >= 20):
            continue
        try:
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            published_at = published_at.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            continue
        age = now - published_at
        if age < -timedelta(hours=24):
            continue
        if freshness and age > freshness:
            continue
        normalized_publisher = re.sub(r"[^a-z0-9]+", "", publisher.lower())
        normalized_url = url.lower().rstrip("/")
        if not normalized_publisher or normalized_publisher in {"rssfeed", "googletrends"}:
            continue
        if normalized_publisher in publishers or normalized_url in urls:
            continue
        publishers.add(normalized_publisher)
        urls.add(normalized_url)
        usable.append({
            "title": title[:240], "url": url[:500], "published": published[:80],
            "publisher": publisher[:100], "summary": summary[:500],
        })
    if len(usable) < 2:
        freshness_note = (
            f" published within {int(freshness.total_seconds() // 3600)} hours"
            if freshness else ""
        )
        raise ValueError(
            f"{lane} requires at least two usable evidence items from distinct publishers"
            f"{freshness_note}, with title, URL, publication date, publisher, and summary"
        )
    return usable[:4]


def generate(output_path: str, history_path: str, lane: str = "surprise",
             seed: int = 1, model_path: str | None = None,
             sources_path: str | None = None) -> dict:
    if lane not in LANES:
        raise ValueError("Unsupported creative lane")
    history_file = Path(history_path)
    history = _load_history(history_file)
    sources = []
    if sources_path:
        sources = json.loads(Path(sources_path).read_text(encoding="utf-8"))
        if not isinstance(sources, list):
            raise ValueError("Source pack must be a JSON array")
    if lane in SOURCED_FACTUAL_LANES:
        sources = validate_source_pack(sources, lane)

    # Reject missing or stale evidence before importing inference runtimes or
    # downloading the model, so an invalid factual job fails fast and cheaply.
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    model_file = model_path or hf_hub_download(
        repo_id=MODEL_REPO, filename=MODEL_FILE, revision=MODEL_REVISION
    )
    llm = Llama(
        model_path=model_file, n_ctx=4096, n_threads=2,
        n_batch=256, verbose=False,
    )
    last_error = None
    retry_feedback = None
    validated = None
    for attempt in range(3):
        prompt = _build_prompt(lane, history, seed + attempt, sources, retry_feedback)
        messages = [
            {"role": "system", "content": "You are a precise, engaging short-form YouTube writer and explainer. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ]
        result = llm.create_chat_completion(
            messages=messages,
            response_format={"type": "json_schema", "schema": _candidate_json_schema(lane)},
            temperature=0.78 + attempt * 0.04,
            top_p=0.85,
            presence_penalty=1.5,
            max_tokens=1300,
        )
        choices = result.get("choices") or []
        choice = choices[0] if choices else {}
        message = choice.get("message") or {}
        raw = message.get("content")
        if not isinstance(raw, str) or not raw.strip():
            # Some local model/runtime combinations can return an empty message
            # with constrained decoding. Retry once in JSON-object mode before
            # rejecting the candidate; all semantic gates still run below.
            fallback = llm.create_chat_completion(
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.72 + attempt * 0.04,
                top_p=0.85,
                presence_penalty=1.5,
                max_tokens=1300,
            )
            fallback_choices = fallback.get("choices") or []
            fallback_choice = fallback_choices[0] if fallback_choices else {}
            fallback_message = fallback_choice.get("message") or {}
            raw = fallback_message.get("content")
            if not isinstance(raw, str) or not raw.strip():
                finish_reason = choice.get("finish_reason", "unknown")
                fallback_finish = fallback_choice.get("finish_reason", "unknown")
                last_error = ValueError(
                    "Empty model response in schema and JSON-object modes "
                    f"(finish_reason={finish_reason}; fallback={fallback_finish})"
                )
                continue
        try:
            raw = _strip_reasoning_preamble(raw)
            parsed = json.loads(raw)
            validated = validate_candidate(parsed, history, lane)
            break
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            # Preserve a short, sanitized sample so CI tells us whether the
            # model emitted a thinking preamble, truncated JSON, or plain text.
            preview = repr(raw[:400]) if isinstance(raw, str) else repr(raw)
            finish_reason = choice.get("finish_reason", "unknown")
            retry_feedback = f"{type(exc).__name__}: {exc}"
            last_error = ValueError(
                f"Candidate rejected ({type(exc).__name__}: {exc}; "
                f"finish_reason={finish_reason}; response_preview={preview})"
            )
    if validated is None:
        raise RuntimeError(f"Local model failed story quality gates after 3 attempts: {last_error}")

    candidate = {
        "schema_version": 1,
        "kind": "github_local_caption_content",
        "content_type": lane,
        "structure_type": STRUCTURE_NAMES.get(lane, "seven_beat_story"),
        **creative_direction(lane, seed),
        "source": "qwen3_4b_local_github_actions",
        "research_sources": sources,
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
    parser.add_argument("--sources-file")
    args = parser.parse_args(argv)
    candidate = generate(args.output, args.history, args.lane, args.seed, args.model_path, args.sources_file)
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
