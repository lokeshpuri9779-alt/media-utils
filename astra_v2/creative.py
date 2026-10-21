"""Reusable Creative Director adapter and independent video integrity gate."""
import json
import hashlib
import os
import subprocess


class CreativeSkip(Exception):
    """No sufficiently good original candidate is available in this slot."""

    def __init__(self, reason, *, selection=None):
        super().__init__(reason)
        self.selection = selection


def inspect_video(path, fmt="short"):
    if not path.is_file() or path.stat().st_size < 30_000:
        raise CreativeSkip("missing_or_tiny_video")
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=35, check=False,
    )
    if proc.returncode:
        raise CreativeSkip("ffprobe_decode_failed")
    data = json.loads(proc.stdout)
    video = next((x for x in data.get("streams", []) if x.get("codec_type") == "video"), {})
    audio = next((x for x in data.get("streams", []) if x.get("codec_type") == "audio"), {})
    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    seconds = float((data.get("format") or {}).get("duration") or 0)
    good = (60 <= seconds <= 3600 and width >= 640 and height >= 360 and width > height and bool(audio)) if fmt == "long" else (seconds > 0 and width >= 360 and height >= 640 and height > width and bool(audio))
    if not good:
        raise CreativeSkip("video_audio_orientation_or_duration_failed")
    return {"seconds": round(seconds, 2), "size": path.stat().st_size,
            "width": width, "height": height}


def story_description_text(story):
    """Use authored narration for reviewed stories without legacy Q/A fields."""
    question, answer = story.get("question"), story.get("answer")
    if question and answer:
        return str(question) + "\n" + str(answer)
    speeches = [str(beat.get("speech") or "").strip()
                for beat in (story.get("story_beats") or [])
                if isinstance(beat, dict) and str(beat.get("speech") or "").strip()]
    if not speeches:
        raise ValueError("Story has no description narration")
    return "\n".join(speeches)


def narration_word_count(story):
    """Count spoken words, not headings or on-screen labels."""
    return sum(len(str(beat.get("speech") or "").split())
               for beat in (story.get("story_beats") or []))


def script_duration_preflight(story, minimum_words=0):
    """No narration word-count or duration target; keep all story beats."""
    return True


def publisher_history_ids(state):
    """Reserve all publisher identities, including unconfirmed pending uploads."""
    ids = set()
    for bucket in ("published", "pending", "reserved"):
        records = state.get(bucket, {})
        if not isinstance(records, dict):
            raise ValueError("Invalid publisher history: " + bucket)
        ids.update(str(cid) for cid in records)
        ids.update(str(record["content_id"]) for record in records.values()
                   if isinstance(record, dict) and record.get("content_id"))
    return ids


def make_candidate(path, excluded_ids, excluded_titles):
    import cloud_once as legacy
    from ypp_safety import enforce
    # First use original curated premium stories; only fall back to the
    # broader learned idea engine if none passes every existing quality gate.
    from premium_stories import catalog
    from astra_v2.original_stories import catalog as original_catalog
    from astra_v2.original_stories import story as make_original_story
    from astra_v2.original_replenishment import catalog as replenishment_catalog
    from astra_v2.procedural_stories import catalog as procedural_catalog
    from astra_v2.anthology_stories import catalog as anthology_catalog
    from astra_v2.free_story_engine import catalog as free_catalog
    from astra_v2.story_forge import catalog as forge_catalog
    from astra_v2.production_story_gate import approved_authored_candidates
    from astra_v2.omniroute_local import catalog as routed_catalog
    from studio_renderer import render_short
    from quality_lab import evaluate_studio_render
    # Original fiction has a unique storyboard, consistent RAYVAN identity and
    # no copied video. It still MUST pass the real full-render Creative Director.
    # A serialized preload must not substitute an unrelated standalone story.
    # Each lane gets its designated episode; if it cannot pass QA, report that
    # episode's failure rather than silently publishing a different storyline.
    series_stories = routed_catalog(excluded_ids, excluded_titles=excluded_titles)
    serialized_preload = os.getenv("ASTRA_SERIALIZED_PRELOAD", "0") == "1"
    from astra_v2.editorial_creative_source import load_editorial_stories
    editorial_stories = load_editorial_stories()
    premium_stories = (series_stories if serialized_preload else
                       series_stories + editorial_stories + approved_authored_candidates(forge_catalog(excluded_ids, excluded_titles, limit=2048)) + anthology_catalog() + free_catalog() + original_catalog()
                       + replenishment_catalog(make_original_story) + catalog()
                       + procedural_catalog(excluded_ids, limit=128))
    # Count truly eligible stories, not just unseen template IDs.
    # Diagnostics only: never bypass the publication or creative gates.
    from astra_v2.publication_quality import publication_rejection
    supply = {"total": len(premium_stories), "seen": 0, "not_ready": 0,
              "publication_rejected": {}, "eligible": 0}
    for story in premium_stories:
        if (story.get("content_id") in excluded_ids
                or str(story.get("title", "")).casefold().strip() in excluded_titles):
            supply["seen"] += 1
        elif not (story.get("production_ready") or story.get("validation_candidate")):
            supply["not_ready"] += 1
        else:
            rejection = publication_rejection(story)
            if rejection:
                reasons = supply["publication_rejected"]
                reasons[rejection] = reasons.get(rejection, 0) + 1
            else:
                supply["eligible"] += 1
    print("ASTRA_STORY_SUPPLY=" + json.dumps(supply, sort_keys=True))
    # Explicitly opted-in paid model may propose a new story; the generated
    # storyboard still goes through the same renderer and QA as curated work.
    from astra_v2.openai_creative import enabled as openai_enabled, generate as openai_generate
    # Merge every available exclusion source; a partial external ledger must
    # never mask previously confirmed videos in publisher state.
    history_ids = set()
    history_titles = set()
    history_hashes = set()
    history_plot_keys = set()
    history_narratives = []
    for history_path, is_publisher_state in (
        (os.getenv("ASTRA_STORY_HISTORY_PATH", "astra_story_history.json"), False),
        (os.getenv("ASTRA_PUBLISHER_STATE_PATH", "astra_v2_state.json"), True),
    ):
        try:
            with open(history_path, "r", encoding="utf-8") as history_file:
                history = json.load(history_file)
            if is_publisher_state:
                published = history.get("published", {})
                if not isinstance(published, dict):
                    raise ValueError("Invalid publisher history")
                history_ids.update(publisher_history_ids(history))
                # Pending and reserved uploads are also unsafe to reuse:
                # the remote upload may have succeeded before local confirmation.
                pending = history.get("pending", {})
                reserved = history.get("reserved", {})
                if not isinstance(pending, dict) or not isinstance(reserved, dict):
                    raise ValueError("Invalid pending or reserved history")
                records = list(published.values()) + list(pending.values()) + list(reserved.values())
            else:
                records = history.get("stories", []) if isinstance(history, dict) else history
                if not isinstance(records, list):
                    raise ValueError("Invalid story history")
            for record in records:
                if not isinstance(record, dict):
                    continue
                if record.get("content_id"):
                    history_ids.add(str(record["content_id"]))
                if record.get("title"):
                    history_titles.add(str(record["title"]).casefold().strip())
                if record.get("plot_fingerprint"):
                    history_hashes.add(str(record["plot_fingerprint"]))
                if record.get("plot_key"):
                    history_plot_keys.add(str(record["plot_key"]))
                if record.get("story_beats"):
                    history_narratives.append(record)
        except FileNotFoundError:
            continue
        except (ValueError, TypeError, OSError) as exc:
            raise CreativeSkip("story_history_unavailable:" + type(exc).__name__) from exc
    # Even if the publisher state has not been restored in this job,
    # explicit exclusion arguments remain the authoritative safety net.
    # Never generate a previously published identity in a parallel lane.
    excluded_ids.update(history_ids)
    excluded_titles.update(history_titles)
    from astra_v2.shorts_novelty import is_near_duplicate
    from astra_v2.story_planning import is_planned_story
    # Generate after loading all ledgers, so model proposals see actual history.
    # OmniRoute free-tier model proposals retain every existing publication and QA gate.
    from astra_v2.omniroute import enabled as omni_enabled, generate as omni_generate
    if omni_enabled() and not serialized_preload:
        try:
            generated = omni_generate(excluded_ids, excluded_titles, history_narratives)
            if generated:
                # AI generation is not editorial approval. Promote only through
                # the independent reviewer and existing hash-bound manifest gate.
                if os.getenv("ASTRA_AUTONOMOUS_EDITORIAL", "0") == "1":
                    from astra_v2.independent_editorial_reviewer import assess
                    from astra_v2.story_forge import plot_fingerprint
                    candidate = dict(generated)
                    candidate["kind"] = "authored_causal_story"
                    candidate["plot_fingerprint"] = candidate.get("plot_fingerprint") or plot_fingerprint(
                        [("", b.get("speech", ""), "", "") for b in candidate.get("story_beats", [])])
                    from astra_v2.proposal_history import load_history
                    from pathlib import Path
                    publisher_file = os.getenv("ASTRA_PUBLISHER_STATE_PATH", "astra_v2_state.json")
                    history_file = os.getenv("ASTRA_STORY_HISTORY_PATH", "astra_story_history.json")
                    if not Path(publisher_file).is_file() or not Path(history_file).is_file():
                        raise ValueError("editorial_requires_complete_publication_history")
                    complete_history = load_history(publisher_file, history_file)
                    verdict = assess(candidate, complete_history)
                    from astra_v2.editorial_review_journal import record_review
                    record_review(candidate, verdict, os.getenv('ASTRA_EDITORIAL_AUDIT_PATH', 'runtime-health/ai-editorial-reviews.json'), complete_history)
                    if verdict["approved"]:
                        premium_stories.insert(0, candidate)
                        print("ASTRA_OMNIROUTE_EDITORIAL_APPROVED=" + candidate["content_id"])
                    else:
                        print("ASTRA_OMNIROUTE_EDITORIAL_REJECTED=" + json.dumps(verdict["issues"]))
                else:
                    print("ASTRA_OMNIROUTE_EDITORIAL_DISABLED=1")
        except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            print("ASTRA_OMNIROUTE_GENERATION_FAILED=" + type(exc).__name__ + ":" + str(exc)[:350])
    if openai_enabled() and not serialized_preload:
        try:
            generated = openai_generate(excluded_ids, excluded_titles, history_narratives)
            if generated:
                premium_stories.insert(0, generated)
        except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            print("OpenAI story skipped:", type(exc).__name__)
    # Attribute history exclusions before discarding candidates. This is
    # diagnostic only; preserve the exact original filter conditions.
    history_filter = {"before": len(premium_stories), "remaining": 0,
                      "id": 0, "title": 0, "fingerprint": 0,
                      "plot_key": 0, "near_duplicate": 0,
                      "unplanned_original": 0}
    remaining_stories = []
    for story in premium_stories:
        if story.get("content_id") in history_ids:
            history_filter["id"] += 1
        elif str(story.get("title", "")).casefold().strip() in history_titles:
            history_filter["title"] += 1
        elif story.get("plot_fingerprint") in history_hashes:
            history_filter["fingerprint"] += 1
        elif story.get("plot_key") in history_plot_keys:
            history_filter["plot_key"] += 1
        elif not (not is_near_duplicate(story, history_narratives)):
            history_filter["near_duplicate"] += 1
        elif (str(story.get("content_id") or "").startswith("rayvan-original-")
              and not is_planned_story(story)):
            history_filter["unplanned_original"] += 1
        else:
            remaining_stories.append(story)
    premium_stories = remaining_stories
    history_filter["remaining"] = len(premium_stories)
    print("ASTRA_STORY_HISTORY_FILTER=" + json.dumps(history_filter, sort_keys=True))
    print("ASTRA_STORY_HISTORY_EXCLUSIONS=" + json.dumps({
        "ids": len(history_ids), "titles": len(history_titles),
        "fingerprints": len(history_hashes), "plot_keys": len(history_plot_keys),
        "remaining_candidates": len(premium_stories)
    }, sort_keys=True))
    # This is the actual remaining publishable pool after merging every history
    # ledger. Earlier supply diagnostics cannot account for publisher-state IDs.
    publishable_remaining = sum(
        1 for candidate in premium_stories
        if (candidate.get("production_ready") or candidate.get("validation_candidate"))
        and not publication_rejection(candidate)
        and candidate.get("content_id") not in excluded_ids
        and str(candidate.get("title", "")).casefold().strip() not in excluded_titles
    )
    print("ASTRA_STORY_SUPPLY_AFTER_HISTORY=" + json.dumps({
        "remaining": publishable_remaining, "pool": len(premium_stories),
    }, sort_keys=True))
    if not serialized_preload and publishable_remaining <= 4:
        print("ASTRA_STORY_SUPPLY_WARNING=" + json.dumps({
            "remaining": publishable_remaining,
            "total": len(premium_stories),
            "reason": "finite_original_story_inventory",
            "action": "replenish_with_new_reviewed_plots",
        }))
    print("Premium pool:", len(premium_stories), "seen IDs:", len(excluded_ids),
          "seen titles:", len(excluded_titles))
    # Parallel preload lanes deterministically own disjoint story IDs.
    lane_count = max(1, int(os.getenv("ASTRA_PRELOAD_LANES", "1")))
    lane_index = int(os.getenv("ASTRA_PRELOAD_LANE", "0"))
    if not 0 <= lane_index < lane_count:
        raise ValueError("Invalid preload lane index")
    if lane_count > 1:
        premium_stories = [story for story in premium_stories
                           if story.get("series_id")
                           and (int(story["episode"]) - 1) % lane_count == lane_index] + [
                               story for story in premium_stories
                               if not story.get("series_id")
                               and int.from_bytes(hashlib.sha256(str(story.get("content_id", "")).encode()).digest()[:8], "big") % lane_count == lane_index]
    from astra_v2.publication_quality import publication_rejection
    selection = {"considered": 0, "not_ready": 0, "policy_rejected": {},
                 "already_seen": 0, "duration_rejected": 0,
                 "render_qa_rejected": 0, "render_exception": {},
                 "approved": 0}
    for story in premium_stories:
        selection["considered"] += 1
        if not (story.get("production_ready") or story.get("validation_candidate")):
            selection["not_ready"] += 1
            continue
        # Do not spend rendering time on stories the publisher will reject.
        rejection = publication_rejection(story)
        if rejection:
            selection["policy_rejected"][rejection] = selection["policy_rejected"].get(rejection, 0) + 1
            print("Story publication preflight rejected:", story.get("content_id"), rejection)
            continue
        if story["content_id"] in excluded_ids or story["title"].casefold().strip() in excluded_titles:
            selection["already_seen"] += 1
            continue
        if not script_duration_preflight(story):
            selection["duration_rejected"] += 1
            print("ASTRA_CANDIDATE_DURATION_REJECTED=" + json.dumps({"content_id": story.get("content_id"), "reason": "script_duration_preflight_failed"}, sort_keys=True))
            continue
        try:
            rendered = render_short(story, path)
            evaluation = evaluate_studio_render(story, rendered, video_path=path)
            if not evaluation.get("pass"):
                selection["render_qa_rejected"] += 1
                print("ASTRA_CANDIDATE_RENDER_QA_REJECTED=" + json.dumps({"content_id": story.get("content_id"), "reason": "creative_render_qa_failed"}, sort_keys=True))
                from astra_v2.stage_feedback import record
                director = evaluation.get("director") or {}
                for component, score in (director.get("component_scores") or {}).items():
                    stage = str(component).lower().replace("-", "_")
                    stage = {"visual_quality": "visuals", "visual": "visuals",
                             "novelty": "story", "coherence": "script",
                             "technical": "render", "retention": "hook",
                             "motion": "animation"}.get(stage, stage)
                    if stage not in ("research", "story", "script", "hook", "characters",
                                     "visuals", "animation", "camera", "lighting", "audio",
                                     "captions", "pacing", "render", "quality", "metadata",
                                     "thumbnail", "publish", "analytics", "learning"):
                        stage = "quality"
                    record(stage, str(component), "unknown", evidence={"score": score, "candidate": story.get("content_id")}, action="Compare score to component threshold before classifying failure", candidate_id=story.get("content_id"))
                record("render", "studio_render", "fail", evidence={"hard_failures": director.get("hard_failures"), "media_failures": (evaluation.get("media_qa") or {}).get("hard_failures"), "layer_failures": (evaluation.get("layer_qa") or {}).get("failures")}, action=str(director.get("repair_plan") or "")[:250], candidate_id=story.get("content_id"))
                print("Premium QA rejected:", story["content_id"],
                      json.dumps({"action": (evaluation.get("director") or {}).get("action"),
                                  "scores": (evaluation.get("director") or {}).get("component_scores"),
                                  "reasons": (evaluation.get("director") or {}).get("floor_failures"),
                                  "repairs": (evaluation.get("director") or {}).get("repair_plan"),
                                  "hard_failures": (evaluation.get("director") or {}).get("hard_failures"),
                                  "media_failures": (evaluation.get("media_qa") or {}).get("hard_failures"),
                                  "layer_failures": (evaluation.get("layer_qa") or {}).get("failures"),
                                  "duration": rendered.get("duration")}, default=str))
                continue
            selection["approved"] += 1
            from astra_v2.stage_feedback import record
            record("quality", "creative_director", "pass", evidence={"scores": (evaluation.get("director") or {}).get("component_scores") or {}}, candidate_id=story.get("content_id"))
            record("render", "studio_render", "pass", evidence={"duration": rendered.get("duration"), "renderer": rendered.get("renderer")}, candidate_id=story.get("content_id"))
            legacy.CONTENT_META = {
                "genre": story["genre"], "content_id": story["content_id"],
                "source": story.get("source"), "plot_key": story.get("plot_key", ""),
                "plot_fingerprint": story.get("plot_fingerprint", ""),
                "story_beats": [{"speech": str(beat.get("speech") or "")} for beat in story.get("story_beats", [])],
                # Preserve explicit, reviewed character records for later
                # post-publication continuity; never infer them from narration.
                "character_id": story.get("character_id"),
                "character_name": story.get("character_name"),
                "character_approved": story.get("character_approved") is True,
                "character_episode": story.get("character_episode"),
                "creative_director": evaluation["director"],
                "renderer": rendered.get("renderer"), "format": "short",
            }
            title = story["title"]
            if story["genre"] == "fiction":
                attribution = "\nAn original fictional microstory; all characters and events are fictional."
            else:
                attribution = "\nSource: " + story.get("source", "")
            description = (story_description_text(story)
                + attribution
                + "\nOriginal visuals; AI-assisted synthetic narration. #Shorts"
                + "\nSubscribe: https://www.youtube.com/channel/" + legacy.expected_channel_id())
            print("ASTRA_STORY_SELECTION=" + json.dumps(selection, sort_keys=True))
            break
        except Exception as exc:
            kind = type(exc).__name__
            selection["render_exception"][kind] = selection["render_exception"].get(kind, 0) + 1
            print("ASTRA_CANDIDATE_RENDER_EXCEPTION=" + json.dumps({"content_id": story.get("content_id"), "exception_type": type(exc).__name__}, sort_keys=True))
            print("Premium candidate rejected:", story.get("content_id"),
                  type(exc).__name__, str(exc)[:250])
    else:
        print("ASTRA_STORY_SELECTION=" + json.dumps(selection, sort_keys=True))
        if lane_count > 1:
            raise CreativeSkip('no_approved_candidate_in_preload_lane', selection=selection)
        # Do not waste a full render on the unreviewed legacy template pool.
        # The existing final publication gate remains mandatory if opted in.
        if os.getenv("ASTRA_ALLOW_LEGACY_FALLBACK", "0") != "1":
            raise CreativeSkip("no_approved_original_story_available", selection=selection)
        try:
            title, description = legacy.make_short(
                path, excluded_ids=excluded_ids, excluded_titles=excluded_titles)
        except RuntimeError as exc:
            message = str(exc).lower()
            if any(word in message for word in (
                "quality", "creative", "novelty", "fresh", "no candidates", "weak",
            )):
                raise CreativeSkip(str(exc)[:250]) from exc
            raise
    meta = dict(legacy.CONTENT_META)
    content_id = str(meta.get("content_id") or "").strip()
    # The legacy renderer can return a technically approved but unpublished
    # template. Reject it here before any later upload/queue handoff.
    final_rejection = publication_rejection({"content_id": content_id, "title": title})
    if final_rejection:
        raise CreativeSkip(final_rejection)
    if not (title and description and content_id):
        raise CreativeSkip("missing_story_identity_or_script")
    # A previous legacy-loop edge case could return its final rejected render.
    # V2 independently checks the final Creative Director decision.
    director = meta.get("creative_director") or {}
    if not director or not director.get("publish_allowed", False):
        raise CreativeSkip("creative_director_did_not_approve")
    if meta.get("genre") in {"space", "tech", "football", "current"} and not meta.get("source"):
        raise CreativeSkip("unsourced_factual_claim")
    if meta.get("copyright_unlicensed") or meta.get("reused_third_party_media"):
        raise CreativeSkip("unlicensed_material_flagged")
    verdict = enforce(title, description, meta, legacy.load_performance())
    if verdict.get("pass") is False:
        raise CreativeSkip("monetization_safety_rejected")
    media = inspect_video(path)
    synthetic = bool(verdict.get("ai_disclosure_required"))
    return {"title": title, "description": description, "content_id": content_id,
            "media": media, "synthetic": synthetic,
            "genre": str(meta.get("genre") or ""), "format": "short",
            "plot_key": str(meta.get("plot_key") or ""),
            "plot_fingerprint": str(meta.get("plot_fingerprint") or ""),
            "story_beats": meta.get("story_beats") or [],
            "character_id": meta.get("character_id"),
            "character_name": meta.get("character_name"),
            "character_approved": meta.get("character_approved") is True,
            "character_episode": meta.get("character_episode"),
            "renderer": str(meta.get("renderer") or "unknown")}


def make_long_candidate(path, excluded_ids, excluded_titles):
    """Use existing source-backed long episodes, only when eligible and QA-passing."""
    import os
    if os.getenv("ASTRA_LONG_ENABLED", "1") != "1":
        return None
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import cloud_once as legacy
    from longform import choose_episode
    from ypp_safety import enforce
    episode = choose_episode(legacy.load_performance(), datetime.now(ZoneInfo("Asia/Kolkata")), excluded_ids=excluded_ids)
    if not episode or episode in excluded_ids:
        return None
    try:
        title, desc = legacy.make_long(path, episode)
    except RuntimeError as exc:
        if "quality" in str(exc).lower() or "creative" in str(exc).lower():
            print("ASTRA_LONG_QA_REJECTED=" + str(exc)[:1800])
            return None
        raise
    # Produce a real-video-frame cover for long-form episodes without paid APIs.
    # Keep the video publishable if cover extraction fails.
    try:
        from astra_v2.cover_frames import extract_long_cover
        extract_long_cover(path)
    except (OSError, RuntimeError, ValueError, ImportError) as cover_error:
        print("ASTRA_LONG_COVER_UNAVAILABLE=" + type(cover_error).__name__)
    meta = dict(legacy.CONTENT_META)
    cid = str(meta.get("content_id") or episode)
    if cid in excluded_ids or title.casefold().strip() in excluded_titles:
        return None
    if not meta.get("source") or meta.get("copyright_unlicensed"):
        raise CreativeSkip("longform_requires_sourced_and_licensed_media")
    verdict = enforce(title, desc, meta, legacy.load_performance())
    if verdict.get("pass") is False:
        raise CreativeSkip("longform_safety_rejected")
    return {"title": title, "description": desc, "content_id": cid,
            "media": inspect_video(path, fmt="long"),
            "synthetic": bool(verdict.get("ai_disclosure_required")),
            "genre": str(meta.get("genre") or "educational"), "format": "long"}
