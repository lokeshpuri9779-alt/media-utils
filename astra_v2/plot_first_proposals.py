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



def proposals(limit=100, excluded_plot_hashes=()):
    seen = set(excluded_plot_hashes)
    # Include existing authored stories in novelty history by default.
    history = catalog(limit=2000)
    seen.update(item["plot_fingerprint"] for item in history)
    output = []
    for problem, crisis, clue, resolution in DRAFT_PROBLEMS:
        visuals = scene_sequence(problem)
        for arc_index, (obstacle, recovery) in enumerate(DRAFT_CAUSAL_ARCS[problem]):
            key = f"plot-first:{problem}:{arc_index}"
            beats = [
                f"The village faced a crisis when {crisis}; a trusted messenger volunteered to investigate before the deadline.",
                f"The first rescue plan failed because {obstacle}; the messenger saw that repeating it would make the danger worse.",
                f"After examining {clue}, the messenger changed course by {recovery}, giving the neighbors a clear way to help.",
                f"The new plan worked: {resolution}; the messenger checked the result and shared the lesson with the village.",
            ]
            fingerprint = hashlib.sha256(" ".join(beats).casefold().encode()).hexdigest()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            story = {
                "content_id": "astra-proposal-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                "title": f"The {problem.title()} — Alternative {arc_index + 1}",
                "genre": "fiction",
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
