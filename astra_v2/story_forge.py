"""Zero-cost autonomous story supply from authored causal plots.

Each scenario has its own setup, escalation, revelation and payoff. This is
a finite pool, not an LLM or a guarantee of endlessly original fiction.
All outputs remain subject to the existing full render and publication gates.
"""
import hashlib
import re

PLOTS = [
    ("hedgehog-raincoat", "The Hedgehog and the Raincoat", "animal comedy",
     [("A RAINY PARADE", "A hedgehog promised to lead the village parade just as the rain began.", "forest", "RAINY DAY"),
      ("THE UMBRELLA POPPED", "Every umbrella he borrowed snagged on his prickly back and sprang open.", "door", "POP"),
      ("LEAVES AND STRING", "He stitched broad leaves into a raincoat and tested it under the fountain.", "forest", "NEW IDEA"),
      ("THE PARADE MARCHED", "His leaf raincoat kept him dry, and soon every animal wore a colorful leaf cape.", "forest", "PARADE SAVED")]),
    ("turtle-river-post", "The Turtle and the River Letter", "animal adventure",
     [("A LETTER DRIFTED BY", "A turtle caught a sealed letter drifting down the river after a storm.", "ship", "LOST LETTER"),
      ("THE BRIDGE WAS GONE", "He reached the crossing and found the wooden footbridge swept away.", "forest", "NO CROSSING"),
      ("THE STONES MADE A PATH", "He spotted a line of flat stones and guided the letter safely across.", "forest", "STEP BY STEP"),
      ("A BIRTHDAY SURPRISE", "The letter reached a grandmother just in time for her birthday celebration.", "door", "DELIVERED")]),
    ("owl-library-light", "The Owl and the Last Library Light", "animal mystery",
     [("THE LIGHT STAYED ON", "An owl noticed one window glowing in the abandoned library every night.", "door", "WHO IS INSIDE"),
      ("A SECRET READER", "He followed tiny footprints through the dust and heard pages turning.", "book", "SOFT FOOTSTEPS"),
      ("THE MOUSE'S PROMISE", "A mouse was reading aloud to a blind old rabbit who could not travel.", "book", "THE SECRET"),
      ("A LIBRARY REOPENS", "The owl invited the village to help, and the library opened again for everyone.", "door", "WELCOME BACK")]),
    ("otter-floating-stage", "The Otter and the Floating Stage", "animal comedy",
     [("THE SHOW WAS CANCELLED", "An otter discovered the village stage flooded before the music festival.", "ship", "FLOODED STAGE"),
      ("THE RAFT SPUN AWAY", "She built a floating platform, but it kept spinning whenever the band played.", "ship", "ROUND AND ROUND"),
      ("ANCHORS OF STONE", "She tied four ropes to river stones and steadied the stage.", "ship", "STEADY NOW"),
      ("MUSIC ON THE WATER", "The band performed on the river while the whole village danced along the shore.", "forest", "ENCORE")]),
    ("rabbit-snow-clock", "The Rabbit and the Frozen Clock", "animal mystery",
     [("THE CLOCK STOPPED", "A rabbit found the town clock frozen just before the winter market opened.", "clock", "TIME STOOD STILL"),
      ("A WARM SCARF", "She wrapped the gears in her scarf, but the clock still would not move.", "clock", "NOT ENOUGH"),
      ("SUNLIGHT THROUGH GLASS", "She moved a mirror to reflect morning sunlight onto the icy mechanism.", "clock", "FIRST TICK"),
      ("THE MARKET OPENED", "The clock chimed again and the market stalls opened right on time.", "door", "RIGHT ON TIME")]),
    ("mouse-bakery-map", "The Mouse and the Flour Map", "animal mystery",
     [("FOOTPRINTS IN FLOUR", "A mouse found mysterious footprints across the bakery floor before dawn.", "door", "WHO WAS HERE"),
      ("A TRAIL TO THE CELLAR", "She followed the flour trail through three rooms and down the cellar steps.", "door", "FOLLOW THE CLUES"),
      ("A LOST LITTLE DUCK", "A duckling had wandered inside to escape the rain and fallen asleep.", "duck", "FOUND YOU"),
      ("BREAKFAST FOR TWO", "The baker reunited the duckling with its family and shared warm bread.", "door", "HOME AGAIN")]),
    ("fox-kite-rescue", "The Fox and the Mountain Kite", "animal adventure",
     [("A KITE DISAPPEARED", "A fox watched a child's handmade kite vanish over the windy mountain ridge.", "forest", "GONE WITH WIND"),
      ("THE NARROW PATH", "She climbed a rocky trail but a fallen branch blocked the shortcut.", "forest", "ROAD BLOCK"),
      ("THE LONG WAY ROUND", "She followed the stream uphill and found the kite caught in a pine tree.", "tree", "FOUND IT"),
      ("A NEW TAIL", "She repaired the torn kite with ribbons and returned it for the village festival.", "forest", "FLY AGAIN")]),
    ("squirrel-moon-seeds", "The Squirrel and the Moon Seeds", "animal fantasy",
     [("SILVER SEEDS", "A squirrel discovered shimmering seeds beneath an old oak after a meteor shower.", "forest", "WHAT ARE THESE"),
      ("A GARDEN OF SPARKS", "He planted them in the dark and watched tiny blue lights emerge from the soil.", "forest", "GLOWING ROOTS"),
      ("THE STORM ARRIVED", "Wind threatened the seedlings, so he sheltered them with a ring of stones.", "forest", "PROTECT THEM"),
      ("A PATH OF LIGHT", "The glowing plants lit a safe path home for animals traveling at night.", "forest", "LIGHT THE WAY")]),
    ("beaver-bridge", "The Beaver and the Broken Bridge", "animal adventure",
     [("THE BRIDGE VANISHED", "A beaver found the village bridge washed away after the storm.", "forest", "RIVER CROSSING"),
      ("A BOAT OF BRANCHES", "She built a raft, but the current carried it toward the waterfall.", "ship", "TOO FAST"),
      ("THE ROOTS HELD FAST", "She tied the raft to the roots of an old willow and made a safe crossing.", "forest", "A NEW PATH"),
      ("THE VILLAGE CROSSED", "Everyone crossed safely, and the beaver planted new willows beside the river.", "forest", "SAFE AGAIN")]),
    ("firefly-lighthouse", "The Firefly Lighthouse", "whimsical adventure",
     [("THE LIGHT WENT OUT", "A firefly watched the lighthouse go dark while fishing boats were still at sea.", "signal", "NO LIGHT"),
      ("A THOUSAND FRIENDS", "She gathered fireflies from the marsh, but the wind scattered their glow.", "forest", "STRONG WIND"),
      ("THE GLASS LANTERN", "The keeper opened the old glass lantern so their lights could shine together.", "signal", "ONE BRIGHT BEAM"),
      ("THE BOATS CAME HOME", "The boats followed the glowing tower safely into the harbor.", "ship", "WELCOME HOME")]),
    ("squirrel-bell", "The Squirrel and the Silent Bell", "animal comedy",
     [("NO SCHOOL BELL", "A squirrel noticed the school bell had fallen silent on the day of the big fair.", "door", "NO RING"),
      ("A ROPE TOO HEAVY", "He pulled the rope until it lifted him high above the playground.", "robot", "UP WE GO"),
      ("THE SWINGING BRANCH", "He tied the rope to a swinging branch and waited for a gust of wind.", "forest", "CLEVER TRICK"),
      ("THE FAIR BEGAN", "The bell rang and everyone hurried outside for the fair.", "signal", "DING DONG")]),
    ("crab-moonlight", "The Crab and the Moonlit Path", "animal fantasy",
     [("THE BEACH WAS DARK", "A young crab could not find the path home after the tide covered the sand.", "planet", "LOST AT NIGHT"),
      ("FOLLOW THE SHELLS", "He followed shining shells until a wave washed them away.", "forest", "WAVES RETURN"),
      ("A MIRROR OF WATER", "He noticed the moon reflected in shallow pools pointing toward the dunes.", "planet", "MOON CLUE"),
      ("HOME BEFORE DAWN", "The crab followed the reflections and reached his family before sunrise.", "forest", "HOME SAFE")]),
    ("pigeon-clock", "The Pigeon Who Fixed Noon", "animal comedy",
     [("NOON CAME EARLY", "A pigeon watched the station clock ring twelve while the sun was still rising.", "signal", "WRONG TIME"),
      ("A GEAR WAS LOOSE", "He squeezed into the tower and found a loose wooden gear.", "robot", "CLOCK TROUBLE"),
      ("ONE PERFECT FEATHER", "A dropped feather wedged the gear just long enough for the keeper to repair it.", "robot", "TINY FIX"),
      ("RIGHT ON TIME", "The clock rang at noon and the pigeon earned a window seat in the tower.", "door", "TICK TOCK")]),
    ("fox-rain-garden", "The Fox and the Rain Garden", "animal adventure",
     [("THE GARDEN DRIED UP", "A fox found the forest garden wilting during a long dry week.", "forest", "NO RAIN"),
      ("THE CLOUD MOVED ON", "She chased a passing cloud, but the wind carried it over the hills.", "planet", "TOO FAR"),
      ("A HIDDEN SPRING", "She heard water beneath a stone and uncovered an old spring.", "forest", "WATER FOUND"),
      ("THE FLOWERS RETURNED", "The fox guided the spring into the garden and new flowers bloomed.", "forest", "NEW LIFE")]),
    ("mole-star-map", "The Mole and the Star Map", "animal mystery",
     [("A MAP UNDERGROUND", "A mole found a map of the night sky buried beneath his tunnel.", "planet", "STRANGE MAP"),
      ("THE STARS DID NOT MATCH", "He brought it outside, but none of the stars were where the map showed.", "planet", "WRONG SKY"),
      ("THE MAP WAS UPSIDE DOWN", "An owl turned the map around and revealed the path to an old observatory.", "door", "TURN IT OVER"),
      ("A NEW TELESCOPE", "Together they restored the observatory so every animal could watch the stars.", "planet", "LOOK UP")]),
    ("duck-postcard", "The Duck and the Lost Postcard", "animal adventure",
     [("A POSTCARD ARRIVED", "A duck found a postcard floating in the pond with no address.", "ship", "MYSTERY MAIL"),
      ("THREE WRONG HOUSES", "She visited the mill, the bakery and the old barn, but nobody knew the sender.", "door", "KEEP LOOKING"),
      ("A PICTURE OF A NEST", "The drawing on the card matched a nest hidden behind the willow tree.", "forest", "THE CLUE"),
      ("A FAMILY REUNITED", "She delivered the card to a traveling goose who had finally returned home.", "forest", "SPECIAL DELIVERY") ]),
    ("raccoon-paint-mixup", "The Raccoon and the Mixed-Up Paint", "animal comedy",
     [("THE MURAL WAS RUINED", "A raccoon spilled every paint jar while preparing the town mural.", "forest", "WHAT A MESS"),
      ("THE COLORS WOULD NOT SEPARATE", "He tried scooping the paint back, but every color turned muddy brown.", "door", "OH NO"),
      ("A NEW KIND OF PICTURE", "He pressed fallen leaves into the wet paint and discovered beautiful textured patterns.", "forest", "WAIT A SECOND"),
      ("THE TOWN LOVED IT", "The villagers helped stamp their own leaf shapes, turning the accident into a mural.", "forest", "MASTERPIECE")]),
    ("penguin-sled-switch", "The Penguin and the Runaway Sled", "animal comedy",
     [("THE SLED WOULD NOT STOP", "A penguin's delivery sled slipped downhill with all the festival cakes aboard.", "ship", "RUNAWAY"),
      ("A SNOWBANK EXPLODED", "He piled snow in its path, but the sled burst straight through the soft mound.", "forest", "SPLASH"),
      ("THE SCARF BECAME A SAIL", "He tied his long scarf between two poles and steered the sled into the wind.", "ship", "TURN LEFT"),
      ("CAKES FOR EVERYONE", "The sled stopped beside the festival table, and not one cake had fallen.", "door", "PERFECT DELIVERY")]),
    ("frog-echo-concert", "The Frog and the Echo Concert", "animal mystery",
     [("THE SONG CAME BACK WRONG", "A frog practicing for a concert heard a second voice answer from the canyon.", "forest", "WHO SANG THAT"),
      ("AN EMPTY STAGE", "She searched the cliffs and found nobody, yet the mysterious harmony continued.", "door", "NO ONE THERE"),
      ("THE HOLLOW REEDS", "She discovered that wind passing through hollow reeds made notes matching her melody.", "forest", "THE SECRET"),
      ("THE CANYON SANG", "She arranged the reeds around the stage and performed a duet with the wind.", "forest", "ENCORE")]),
    ("badger-midnight-pie", "The Badger and the Midnight Pie", "animal comedy",
     [("THE PIE VANISHED", "A badger opened his bakery at midnight and found the contest pie missing.", "door", "WHERE IS IT"),
      ("CRUMBS LED OUTSIDE", "He followed a trail of crumbs to the garden, where the trail suddenly ended.", "forest", "A DEAD END"),
      ("THE WHEELBARROW MOVED", "A sleepy tortoise rolled out from beneath a wheelbarrow with the pie balanced on top.", "forest", "SURPRISE"),
      ("THE JUDGES LAUGHED", "The pie arrived just in time, and the tortoise earned a prize for careful delivery.", "door", "FIRST PRIZE")]),

]

def plot_fingerprint(beats):
    """Fingerprint story narration, excluding cosmetic titles and labels."""
    narration = " ".join(speech for _, speech, _, _ in beats).casefold()
    normalized = " ".join(re.sub(r"[^a-z0-9 ]", " ", narration).split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def catalog(excluded_ids=None, excluded_titles=None, limit=32, excluded_plot_hashes=None, history=None):
    excluded = set(excluded_ids or ())
    titles = {str(t).casefold().strip() for t in (excluded_titles or ())}
    result = []
    seen_plots = set(excluded_plot_hashes or ())
    for record in (history or ()):
        if not isinstance(record, dict):
            continue
        excluded.add(str(record.get("content_id") or ""))
        title = str(record.get("title") or "").casefold().strip()
        if title:
            titles.add(title)
        fingerprint = str(record.get("plot_fingerprint") or "")
        if fingerprint:
            seen_plots.add(fingerprint)
    for key, title, genre, beats in PLOTS:
        cid = "rayvan-forge-" + hashlib.sha256(key.encode()).hexdigest()[:16]
        fingerprint = plot_fingerprint(beats)
        if cid in excluded or title.casefold() in titles or fingerprint in seen_plots:
            continue
        seen_plots.add(fingerprint)
        result.append({
            "genre": "fiction", "kind": "authored_causal_story",
            "production_ready": True, "content_id": cid,
            "plot_fingerprint": fingerprint,
            "title": title, "hook": beats[0][0],
            "question": beats[0][1], "answer": beats[-1][1],
            "source": "", "keywords": ["original fiction", genre],
            "story_beats": [
                {"headline": h, "speech": speech, "visual": visual,
                 "label": label, "story_beat": role,
                 "sub": "AN ORIGINAL RAYVAN STORY", "duration": 2.1}
                for role, (h, speech, visual, label) in
                zip(("reveal", "build", "twist", "payoff"), beats)
            ],
        })
        if len(result) >= limit:
            break
    return result
