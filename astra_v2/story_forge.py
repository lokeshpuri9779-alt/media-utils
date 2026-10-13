"""Zero-cost autonomous story supply from authored causal plots.

Each scenario has its own setup, escalation, revelation and payoff. This is
a finite pool, not an LLM or a guarantee of endlessly original fiction.
All outputs remain subject to the existing full render and publication gates.
"""
import hashlib

PLOTS = [
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
      ("A FAMILY REUNITED", "She delivered the card to a traveling goose who had finally returned home.", "forest", "SPECIAL DELIVERY")]),
]

def catalog(excluded_ids=None, excluded_titles=None, limit=32):
    excluded = set(excluded_ids or ())
    titles = {str(t).casefold().strip() for t in (excluded_titles or ())}
    result = []
    for key, title, genre, beats in PLOTS:
        cid = "rayvan-forge-" + hashlib.sha256(key.encode()).hexdigest()[:16]
        if cid in excluded or title.casefold() in titles:
            continue
        result.append({
            "genre": "fiction", "kind": "authored_causal_story",
            "production_ready": True, "content_id": cid,
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
