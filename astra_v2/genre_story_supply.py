"""Additional deterministic story families for autonomous supply."""
import hashlib

SCENARIOS = (
    ("comedy", "a seaside carnival", "a clumsy penguin", "a runaway prize balloon", "a gust carried it into a kite contest", "steered it home with a giant paper kite", "balloon"),
    ("adventure", "a glowing canyon", "a young explorer", "a vanished footbridge", "sunlight revealed stepping stones beneath the water", "led the group across the safe stones", "bridge"),
    ("friendship", "a rooftop garden", "a shy dragon", "a missing birthday gift", "a bird had woven its ribbon into a nest", "made a new gift and protected the nest", "garden"),
    ("science fiction", "an orbiting station", "a curious robot", "an unexplained blinking light", "an old research drone was signaling for help", "guided the drone safely back to the station", "signal"),
    ("competition", "a mountain racecourse", "a determined turtle", "a missing finish-line flag", "a storm had blown it onto a rescue trail", "helped the rescuers before finishing the race", "flag"),
    ("fantasy", "an enchanted forest", "a novice wizard", "trees singing the wrong melody", "two magical wind chimes had traded places", "returned the chimes and restored the forest song", "forest"),
    ("rescue", "a snowy valley", "a resourceful mountain goat", "a lost puppy across a frozen stream", "a sheltered path lay behind a fallen pine", "guided the puppy along the safe path", "snow"),
    ("discovery", "an underwater library", "a playful octopus", "a book glowing after sunset", "the pages reflected an ancient mosaic", "showed the reef its forgotten history", "book"),
)
MOTIVATIONS = (
    "wanted to prove they could help without being asked",
    "hoped to keep a promise to a close friend",
    "needed to protect something entrusted to their care",
    "was afraid of disappointing the whole team",
    "wanted to make amends for an earlier mistake",
    "hoped to discover why an old tradition mattered",
    "wanted to help a newcomer feel welcome",
    "needed to choose between winning and doing the right thing",
)
PARTNERS = (
    "a skeptical inventor",
    "a cheerful musician",
    "a cautious gardener",
    "a bold young pilot",
    "a forgetful librarian",
    "a quiet animal rescuer",
    "a retired athlete",
    "an imaginative mapmaker",
)
STRATEGIES = (
    "They split into two teams to check different clues",
    "They built a small model before taking any risks",
    "They asked someone who had witnessed the first event",
    "They traced the unusual pattern back to its source",
    "They tested their first assumption against a second clue",
    "They tried to understand the other person's point of view",
    "They turned an accidental mistake into a useful experiment",
    "They took a longer but safer route around the obstacle",
)
PAYOFF_STYLES = (
    "A funny misunderstanding became the joke everyone retold",
    "An unlikely friendship grew from the shared challenge",
    "The team celebrated a fair victory instead of a shortcut",
    "A small act of generosity inspired the whole community",
    "The hero admitted a mistake and earned back trust",
    "A quiet teammate received the recognition they deserved",
    "The discovery opened the door to another adventure",
    "The group started a new tradition together",
)
NARRATIVE_STRUCTURES = (
    ("misunderstanding", "The hero first believed a friend was responsible, but decided to listen before judging.", "A conversation revealed the surprising truth behind the confusion.", "The friends cleared up the misunderstanding and rebuilt trust."),
    ("rivalry-to-teamwork", "A rival challenged the hero to solve the problem first, turning the task into a contest.", "The rival noticed a clue that the hero had missed, and competition became cooperation.", "Both rivals combined their ideas and shared the victory."),
    ("failed-invention", "The hero invented a quick solution, but the invention caused a harmless new complication.", "A tiny design mistake explained why the invention behaved unexpectedly.", "The hero redesigned it and demonstrated the safer version."),
    ("unexpected-helper", "The hero overlooked a quiet teammate while asking everyone else for advice.", "The quiet teammate knew the crucial detail and finally spoke up.", "The hero gave the teammate credit and they finished together."),
    ("difficult-choice", "The hero had to choose between personal success and helping someone in trouble.", "A new clue showed that helping first would also reveal a better path forward.", "The hero chose kindness and found a satisfying solution."),
    ("race-against-time", "The hero had only a short time before an important event would begin.", "A careful shortcut appeared after the team abandoned a risky first plan.", "The team completed the task safely just in time."),
    ("role-reversal", "The hero expected to lead, but a younger companion offered an unusual plan.", "The companion understood a detail that the experienced hero had missed.", "The hero followed the companion's lead and celebrated the new leader."),
    ("small-kindness", "The hero stopped to help a stranger even though a bigger task was waiting.", "The stranger's knowledge unexpectedly explained the bigger problem.", "Their kindness came full circle when the stranger helped everyone succeed."),
)
COMPLICATIONS = (
    "The first plan failed when the weather changed",
    "A rival misunderstood the clue and ran the wrong way",
    "The smallest teammate noticed a detail everyone else missed",
    "A sudden interruption forced the team to improvise",
    "The obvious shortcut turned out to be unsafe",
    "A friend had to admit an embarrassing mistake",
    "A harmless distraction nearly spoiled the plan",
    "The team discovered they had less time than expected",
)
LESSONS = (
    "They learned that asking for help is a strength",
    "The friends celebrated teamwork over individual glory",
    "They laughed together at their earlier misunderstanding",
    "They discovered that patience can be surprisingly brave",
    "The group learned to protect others while solving problems",
    "Everyone appreciated the quiet teammate's clever idea",
    "They found that a mistake can lead to a good discovery",
    "They promised to listen before jumping to conclusions",
)


def balanced_genre_index(index, recent):
    """Choose an underrepresented genre deterministically from recent accepted proposals."""
    from collections import Counter
    counts = Counter(
        str(item.get("genre"))
        for item in recent[-500:]
        if isinstance(item, dict) and item.get("genre")
    )
    lowest = min(counts.get(row[0], 0) for row in SCENARIOS)
    options = [offset for offset, row in enumerate(SCENARIOS) if counts.get(row[0], 0) == lowest]
    return options[index % len(options)]


def genre_proposal(index, scenario_index=None):
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        raise ValueError("Invalid proposal index")
    genre, setting, hero, problem, reveal, solution, visual = SCENARIOS[(index if scenario_index is None else scenario_index) % len(SCENARIOS)]
    complication = COMPLICATIONS[(index // len(SCENARIOS)) % len(COMPLICATIONS)]
    lesson = LESSONS[(index // (len(SCENARIOS) * len(COMPLICATIONS))) % len(LESSONS)]
    motivation = MOTIVATIONS[(index // 3) % len(MOTIVATIONS)]
    partner = PARTNERS[(index // 5) % len(PARTNERS)]
    strategy = STRATEGIES[(index // 7) % len(STRATEGIES)]
    payoff_style = PAYOFF_STYLES[(index // 11) % len(PAYOFF_STYLES)]
    structure_id, opening, middle, ending = NARRATIVE_STRUCTURES[(index // 13) % len(NARRATIVE_STRUCTURES)]
    beats = [
        ("reveal", f"At {setting}, {hero} encountered {problem}. Everyone stopped what they were doing. The hero {motivation} and teamed up with {partner}. {opening}", visual),
        ("build", f"The hero tried a simple solution, but it did not work. {complication}. {strategy}. {middle}", "book"),
        ("twist", f"The overlooked detail explained everything: {reveal}. The group realized that the original problem had a different cause than they first assumed. They tested the explanation before acting.", visual),
        ("payoff", f"With the mystery understood, the hero {solution}. {ending} {lesson}. {payoff_style}.", visual),
    ]
    narration = " ".join(speech for _, speech, _ in beats).casefold()
    return {
        "content_id": "astra-genre-" + hashlib.sha256(f"genre-{index}".encode()).hexdigest()[:20],
        "title": f"{genre.title()}: {problem.title()}",
        "genre": genre,
        "plot_structure": structure_id,
        "premise_id": f"{genre}:{problem}",
        "outcome_id": solution,
        "kind": "unreviewed_causal_draft",
        "production_ready": False,
        "proposal_index": index,
        "plot_fingerprint": hashlib.sha256(narration.encode()).hexdigest(),
        "story_beats": [{"story_beat": name, "speech": speech, "visual": visual} for name, speech, visual in beats],
    }
