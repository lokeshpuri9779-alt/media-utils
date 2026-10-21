"""Original narrative design patterns, not excerpts or adaptations.

These abstract mechanisms were informed by studying storytelling structures in
moral-story collections. No book text, distinctive characters or plots are used.
All outputs are advisory, and no story is approved for publication here.
"""

PATTERNS = {
    "generosity_under_pressure": {
        "weakness": "The protagonist wants to help but fears losing a scarce resource.",
        "choice": "They must decide who receives help when a tempting reward is offered.",
        "consequence": "Their choice changes another person's trust and future cooperation.",
        "lesson": "Generosity is tested by opportunity cost, not good intentions alone.",
    },
    "cleverness_over_force": {
        "weakness": "The protagonist lacks the strength or resources to confront a threat.",
        "choice": "They observe what the threat wants and create a safe alternative.",
        "consequence": "The threat's own assumptions create an opening for resolution.",
        "lesson": "Careful observation can outperform direct confrontation.",
    },
    "reciprocal_help": {
        "weakness": "Two neighbors underestimate what the other can contribute.",
        "choice": "One takes a small risk to protect the other without expecting payment.",
        "consequence": "Later, the second neighbor can solve a different problem.",
        "lesson": "Useful cooperation can come from unexpected directions.",
    },
    "overconfidence_and_repair": {
        "weakness": "An early success makes the protagonist dismiss a warning.",
        "choice": "They can defend their reputation or test their assumption.",
        "consequence": "Admitting the error creates a better, verifiable solution.",
        "lesson": "Progress depends on correction rather than appearances.",
    },
    "fairness_of_design": {
        "weakness": "A shared service unintentionally excludes someone.",
        "choice": "The protagonist redesigns the service rather than blaming the user.",
        "consequence": "A practical test confirms that everyone can participate.",
        "lesson": "Fairness is reflected in what a system lets people do.",
    },
    "small_actions_compound": {
        "weakness": "Everyone expects someone else to take responsibility.",
        "choice": "The protagonist commits to a small, visible contribution.",
        "consequence": "Other people respond and the collective problem changes.",
        "lesson": "Shared responsibility starts with an individual action.",
    },
}


def pattern_for(index):
    """Deterministic structural prompt; never a completed or approved story."""
    if not isinstance(index, int) or index < 0:
        raise ValueError("index must be a nonnegative integer")
    key = tuple(PATTERNS)[index % len(PATTERNS)]
    return {"pattern_id": key, **PATTERNS[key], "production_ready": False,
            "publication_approved": False}


def prompt_for(index):
    """Return an original-story design constraint, not source-book content."""
    item = pattern_for(index)
    return (
        "Invent an original setting, cast, physical problem, and causal solution. "
        "Do not reproduce a known fable or a book's characters, sequence of events, "
        "or distinctive dialogue. Make the moral emerge from observable consequences. "
        f"Weakness: {item['weakness']} Choice: {item['choice']} "
        f"Consequence: {item['consequence']} Lesson: {item['lesson']}"
    )
