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
EXTRA_SCENARIOS = (
    ("comedy", "a bustling bakery", "a mischievous squirrel", "a cake that kept changing colors", "the icing reacted to the warm kitchen lights", "served a rainbow dessert for the celebration", "cake"),
    ("comedy", "a puppet theater", "a nervous stagehand", "a puppet performing without strings", "a hidden fan was lifting its paper costume", "turned the surprise into a funny finale", "puppet"),
    ("adventure", "a volcanic island", "a curious sea otter", "a compass pointing toward the ocean", "a submerged metal sculpture was pulling the needle", "found the safe route around the reef", "ship"),
    ("adventure", "a cloud-top village", "a young glider pilot", "a vanished delivery basket", "the basket had landed on a drifting cloud", "retrieved the supplies with a wind-powered glider", "cloud"),
    ("friendship", "a busy train station", "a shy hedgehog", "two friends waiting at the wrong platform", "their invitations listed different departure times", "brought everyone together for the trip", "train"),
    ("friendship", "a woodland picnic", "a friendly rabbit", "a picnic basket that nobody claimed", "a newcomer had prepared it as a welcome gift", "invited the newcomer to join the celebration", "basket"),
    ("science fiction", "a lunar greenhouse", "a thoughtful astronaut", "plants growing toward the floor", "an experimental gravity plate was still switched on", "adjusted the plate and saved the seedlings", "garden"),
    ("science fiction", "a futuristic transit hub", "a young mechanic", "a train arriving before its departure", "two station clocks were showing different time zones", "synchronized the clocks and restored the timetable", "clock"),
    ("competition", "a floating sports arena", "a competitive dolphin", "the scoreboard awarding points backward", "the sensor had been installed upside down", "restarted the contest fairly", "ball"),
    ("competition", "a mountain music festival", "a young violinist", "a final note nobody could play", "the score contained a playful musical riddle", "invited the audience to complete the melody", "music"),
    ("fantasy", "a moonlit castle", "a young apprentice", "a staircase changing direction every hour", "a spell was following the castle's ancient sundial", "guided everyone safely to the banquet", "clock"),
    ("fantasy", "a village of giant mushrooms", "a tiny fairy", "lanterns floating away at dusk", "the lanterns were following enchanted fireflies", "led them back with a gentle song", "lantern"),
    ("rescue", "a coral lagoon", "a young sea turtle", "a seahorse tangled in discarded rope", "a nearby crab knew a safe way to loosen the knots", "freed the seahorse without damaging the reef", "river"),
    ("rescue", "a windy hilltop", "a brave sparrow", "a nest slipping from a branch", "a nearby vine could support the nest until the storm passed", "secured the nest and sheltered the chicks", "tree"),
    ("discovery", "a desert observatory", "a young stargazer", "a star appearing in the wrong constellation", "a polished weather balloon was reflecting distant lights", "recorded the optical illusion for future explorers", "telescope"),
    ("discovery", "a forgotten garden maze", "an inventive mole", "flowers blooming in a perfect spiral", "an underground water channel shaped the growth", "mapped the channel and revived the garden", "garden"),
)
SCENARIOS = SCENARIOS + EXTRA_SCENARIOS

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
INNER_CONFLICTS = (
    "The hero worried that asking for help would look like failure",
    "The hero wanted to win but knew a friend needed support",
    "The hero was afraid to admit an earlier mistake",
    "The hero struggled to trust a newcomer",
    "The hero was impatient with a slower teammate",
    "The hero doubted whether their unusual idea could work",
    "The hero feared disappointing someone they admired",
    "The hero wanted to keep a promise even when plans changed",
)
CHARACTER_ARCS = (
    ("feared asking for help", "decided to ask a friend for help", "realized that teamwork made them stronger"),
    ("wanted all the credit", "publicly credited the teammate who solved the clue", "learned that sharing success felt better than winning alone"),
    ("was afraid to admit a mistake", "admitted the mistake and corrected it", "earned trust by telling the truth"),
    ("distrusted a newcomer", "invited the newcomer to lead the next step", "discovered that trust grows through listening"),
    ("rushed ahead without listening", "stopped and carefully listened to the quieter teammate", "learned that patience can reveal the best answer"),
    ("doubted their own unusual idea", "tested the idea with the group", "gained confidence through careful experimentation"),
    ("worried about disappointing their mentor", "explained the difficult choice to their mentor", "found that integrity mattered more than approval"),
    ("wanted to keep a promise at any cost", "changed the plan to protect everyone safely", "understood that caring for people mattered more than rigid plans"),
)
# Each emotional choice unlocks a concrete step in the external investigation.
# These bridges are indexed alongside CHARACTER_ARCS and must stay aligned.
ARC_PLOT_BRIDGES = (
    ("The missing assistance had blocked the search.", "The friend joined the search and uncovered the clue needed for the solution."),
    ("The overlooked teammate held the missing evidence.", "Giving the teammate credit encouraged them to share the evidence that unlocked the solution."),
    ("The concealed mistake had sent the investigation in the wrong direction.", "The admission corrected the false lead and revealed where to look next."),
    ("The newcomer knew a route the others had dismissed.", "Trusting the newcomer opened that route and revealed the crucial clue."),
    ("Rushing past the quiet teammate had hidden a warning.", "Listening revealed the warning and made the next step safe."),
    ("The untested idea was the only remaining lead.", "Testing the idea produced the evidence needed to proceed."),
    ("Fear of disapproval had kept the real dilemma secret.", "Explaining the choice brought guidance that made a safe solution possible."),
    ("Following the original plan would put someone at risk.", "Changing the plan protected the group and opened a safer way to solve the problem."),
)

# Observable consequence of each decision, carried from discovery into resolution.
ARC_CONSEQUENCES = (
    ("The friend stayed with the team and kept helping.", "The hero thanked the friend and invited them to future adventures."),
    ("The teammate's contribution remained visible to everyone.", "The hero shared the final celebration and credit with the teammate."),
    ("The corrected mistake stayed acknowledged rather than hidden.", "The hero openly explained the repair and accepted responsibility."),
    ("The newcomer continued guiding the group after the discovery.", "The hero welcomed the newcomer as a trusted partner."),
    ("The quiet teammate's warning remained part of the safer plan.", "The hero made space for the teammate's voice at the celebration."),
    ("The tested idea became the team's evidence-based plan.", "The hero recorded what the experiment taught everyone."),
    ("The mentor understood why the difficult choice was necessary.", "The hero stood by the choice and discussed its consequences."),
    ("The safer plan continued protecting everyone through the finish.", "The hero renewed the promise in a safer and kinder form."),
)

CHARACTER_DECISIONS = (
    "They chose to listen instead of interrupting",
    "They shared the credit instead of claiming the prize",
    "They admitted the mistake before anyone was blamed",
    "They trusted a teammate with a different approach",
    "They slowed down to protect someone vulnerable",
    "They tested their idea instead of insisting they were right",
    "They asked for help despite feeling embarrassed",
    "They kept the promise by finding a safer alternative",
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


def balanced_structure_index(index, recent):
    """Choose a less-used narrative structure from the rolling proposal window."""
    from collections import Counter
    counts = Counter(
        str(item.get("plot_structure"))
        for item in recent[-500:]
        if isinstance(item, dict) and item.get("plot_structure") in {
            row[0] for row in NARRATIVE_STRUCTURES
        }
    )
    minimum = min(counts.get(row[0], 0) for row in NARRATIVE_STRUCTURES)
    options = [
        offset for offset, row in enumerate(NARRATIVE_STRUCTURES)
        if counts.get(row[0], 0) == minimum
    ]
    return options[index % len(options)]


def genre_proposal(index, scenario_index=None, structure_index=None):
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        raise ValueError("Invalid proposal index")
    genre, setting, hero, problem, reveal, solution, visual = SCENARIOS[(index if scenario_index is None else scenario_index) % len(SCENARIOS)]
    complication = COMPLICATIONS[(index // len(SCENARIOS)) % len(COMPLICATIONS)]
    lesson = LESSONS[(index // (len(SCENARIOS) * len(COMPLICATIONS))) % len(LESSONS)]
    motivation = MOTIVATIONS[(index // 3) % len(MOTIVATIONS)]
    partner = PARTNERS[(index // 5) % len(PARTNERS)]
    strategy = STRATEGIES[(index // 7) % len(STRATEGIES)]
    payoff_style = PAYOFF_STYLES[(index // 11) % len(PAYOFF_STYLES)]
    arc_problem, arc_choice, arc_growth = CHARACTER_ARCS[(index // 19) % len(CHARACTER_ARCS)]
    blocked_plot, unlocked_plot = ARC_PLOT_BRIDGES[(index // 19) % len(ARC_PLOT_BRIDGES)]
    lasting_effect, acknowledged_effect = ARC_CONSEQUENCES[(index // 19) % len(ARC_CONSEQUENCES)]
    structure_id, opening, middle, ending = NARRATIVE_STRUCTURES[((index // 13) if structure_index is None else structure_index) % len(NARRATIVE_STRUCTURES)]
    beats = [
        ("reveal", f"At {setting}, {hero} encountered {problem}. Everyone stopped what they were doing. The hero {motivation} and teamed up with {partner}. {opening} The hero {arc_problem}.", visual),
        ("build", f"To solve {problem}, the hero tried a simple solution, but it did not work. {complication}. {strategy}. {blocked_plot} The hero {arc_choice}. {unlocked_plot} {middle}", "book"),
        ("twist", f"The overlooked detail explained everything: {reveal}. The group realized that the original problem had a different cause than they first assumed. They tested the explanation before acting. {lasting_effect}", visual),
        ("payoff", f"Because {reveal}, the hero {solution}, addressing {problem}. {acknowledged_effect} The hero {arc_growth}. {payoff_style}.", visual),
    ]
    # Scene identifiers should track distinct story events rather than
    # repeating the opening prop for the reveal and resolution.
    # All identifiers are existing renderer-facing visual categories.
    scene_visuals = {
        "comedy": ("balloon", "puppet", "cake"),
        "adventure": ("bridge", "ship", "cloud"),
        "friendship": ("garden", "train", "basket"),
        "science fiction": ("signal", "clock", "garden"),
        "competition": ("flag", "ball", "music"),
        "fantasy": ("forest", "clock", "lantern"),
        "rescue": ("snow", "river", "tree"),
        "discovery": ("book", "telescope", "garden"),
    }
    alternatives = scene_visuals[genre]
    used = {visual, "book"}
    revised = []
    for position, (beat_name, speech, scene) in enumerate(beats):
        if position >= 2 and scene in used:
            scene = next((candidate for candidate in alternatives
                          if candidate not in used), scene)
        revised.append((beat_name, speech, scene))
        used.add(scene)
    beats = revised
    narration = " ".join(speech for _, speech, _ in beats).casefold()
    return {
        "content_id": "astra-genre-" + hashlib.sha256(f"genre-{index}".encode()).hexdigest()[:20],
        "title": f"{genre.title()}: {problem.title()}",
        "genre": genre,
        "plot_structure": structure_id,
        "character_arc_id": arc_problem,
        "plot_dependency_id": (index // 19) % len(ARC_PLOT_BRIDGES),
        "consequence_id": (index // 19) % len(ARC_CONSEQUENCES),
        "premise_id": f"{genre}:{problem}",
        "outcome_id": solution,
        "kind": "unreviewed_causal_draft",
        "production_ready": False,
        "proposal_index": index,
        "plot_fingerprint": hashlib.sha256(narration.encode()).hexdigest(),
        "story_beats": [{"story_beat": name, "speech": speech, "visual": visual} for name, speech, visual in beats],
    }
