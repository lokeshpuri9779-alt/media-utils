"""Deterministic plot-first *proposals*, never publication approvals.

Uses compatible causal arcs per problem, not arbitrary actor/setback swaps.
The finite source is deliberately not advertised as unlimited originality.
"""
import hashlib
from astra_v2.story_forge import DRAFT_PROBLEMS, DRAFT_CAUSAL_ARCS, catalog
from astra_v2.story_editorial import editorial_issues


SCENES = {
    "bridge": ("river", "bridge", "workshop", "river"),
    "bell": ("village", "tower", "library", "tower"),
    "garden": ("garden", "river", "workshop", "garden"),
    "compass": ("forest", "mountain", "library", "forest"),
    "lighthouse": ("coast", "lighthouse", "workshop", "coast"),
    "ferry": ("harbor", "ship", "workshop", "harbor"),
}
DEFAULT_SCENES = ("village", "workshop", "library", "village")


def scene_sequence(problem):
    name = problem.casefold()
    return next((scenes for word, scenes in SCENES.items() if word in name),
                DEFAULT_SCENES)



ROLES = (
    ("the patient mechanic", "protect the town's only safe route", "refused to risk a rushed repair"),
    ("the observant ranger", "keep the youngest neighbors safe", "stopped the team from ignoring a warning"),
    ("the determined apprentice", "earn trust by solving the problem carefully", "admitted the first idea was wrong"),
    ("the resourceful caretaker", "preserve a place everyone depended on", "asked for help instead of hiding the damage"),
    ("the curious cartographer", "find a reliable path for everyone", "checked the evidence before making a promise"),
)


def character_arc(index):
    return ROLES[index % len(ROLES)]


# Consequences are tied to the repaired system, not a generic celebration.
CONSEQUENCES = {
    "bridge": ("the crossing stayed closed until a load test passed", "the first cart crossed only after the supports held"),
    "bell": ("the town used runners while the signal was silent", "the restored signal reached the farthest street"),
    "garden": ("the seedlings were moved to higher ground", "fresh soil held moisture without flooding the roots"),
    "compass": ("the group marked its last safe position", "the return route matched the landmarks on the map"),
    "lighthouse": ("the harbor kept boats offshore until the light was reliable", "three passing boats saw the steady beam"),
    "ferry": ("passengers waited on shore instead of boarding an unsafe vessel", "the ferry completed a supervised crossing"),
}
DEFAULT_CONSEQUENCE = (
    "the team stopped using the damaged system while repairs were checked",
    "a careful trial showed the repaired system could be trusted",
)


def consequence_for(problem):
    name = problem.casefold()
    return next((outcome for word, outcome in CONSEQUENCES.items() if word in name),
                DEFAULT_CONSEQUENCE)


def proposals(limit=100, excluded_plot_hashes=()):
    seen = set(excluded_plot_hashes)
    # Include existing authored stories in novelty history by default.
    history = catalog(limit=2000)
    seen.update(item["plot_fingerprint"] for item in history)
    output = []
    for problem, crisis, clue, resolution in DRAFT_PROBLEMS:
        visuals = scene_sequence(problem)
        immediate_cost, verified_result = consequence_for(problem)
        for arc_index, (obstacle, recovery) in enumerate(DRAFT_CAUSAL_ARCS[problem]):
            key = f"plot-first:{problem}:{arc_index}"
            hero, motivation, decision = character_arc(arc_index)
            beats = [
                f"The village faced a crisis when {crisis}; {hero} stepped forward to {motivation}.",
                f"The first rescue plan failed because {obstacle}; {hero} {decision}, while {immediate_cost}.",
                f"After examining {clue}, {hero} chose to {recovery}, even though the neighbors had to abandon their original plan.",
                f"The revised plan changed the outcome: {resolution}; {verified_result}, so {hero} could finally reopen the service.",
            ]
            fingerprint = hashlib.sha256(" ".join(beats).casefold().encode()).hexdigest()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            story = {
                "content_id": "astra-proposal-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                "title": f"The {problem.title()} — Alternative {arc_index + 1}",
                "genre": "fiction",
                "character_role": hero,
                "character_motivation": motivation,
                "character_decision": decision,
                "consequence": immediate_cost,
                "verification": verified_result,
                "kind": "unreviewed_causal_draft",
                "production_ready": False,
                "plot_fingerprint": fingerprint,
                "story_beats": [
                    {"story_beat": role, "headline": label, "speech": speech,
                     "visual": visual, "label": label}
                    for role, label, speech, visual in zip(
                        ("reveal", "build", "twist", "payoff"),
                        ("THE CRISIS", "THE FAILED PLAN", "THE CLUE", "THE RESULT"),
                        beats, visuals)
                ],
            }
            story["editorial_issues"] = editorial_issues(story, history)
            output.append(story)
            if len(output) >= limit:
                return output
    return output
