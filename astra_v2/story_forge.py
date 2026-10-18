"""Zero-cost autonomous story supply from authored causal plots.

Each scenario has its own setup, escalation, revelation and payoff. This is
a finite pool, not an LLM or a guarantee of endlessly original fiction.
All outputs remain subject to the existing full render and publication gates.
"""
import hashlib
import re
from astra_v2.pillow_duo_stories import PLOTS as PILLOW_DUO_PLOTS
from astra_v2.editorial_batch_oct2026 import PLOTS as EDITORIAL_OCT2026_PLOTS
from astra_v2.crossgenre_directed_24 import PLOTS as CROSSGENRE_DIRECTED_24
from astra_v2.authored_replenishment_oct2026 import PLOTS as AUTHORED_REPLENISHMENT_OCT2026
from astra_v2.authored_batch_341 import PLOTS as AUTHORED_BATCH_341
from astra_v2.authored_batch_364 import PLOTS as AUTHORED_BATCH_364
from astra_v2.authored_batch_407 import PLOTS as AUTHORED_BATCH_407
from astra_v2.authored_batch_420 import PLOTS as AUTHORED_BATCH_420
from astra_v2.authored_batch_421 import PLOTS as AUTHORED_BATCH_421
from astra_v2.authored_batch_422 import PLOTS as AUTHORED_BATCH_422

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

    ("koala-night-train", "The Koala and the Last Night Train", "animal adventure",
     [("THE TRAIN LEFT EARLY", "A koala arrived at the station and saw the last train rolling away with his medicine parcel.", "clock", "TOO LATE"),
      ("THE TUNNEL WAS CLOSED", "He raced down a shortcut but found the old tunnel blocked by fallen rocks.", "door", "NO WAY THROUGH"),
      ("THE SIGNAL MIRROR", "He climbed the signal tower and flashed his pocket mirror toward the conductor.", "signal", "LOOK HERE"),
      ("THE TRAIN RETURNED", "The conductor stopped at the next platform and brought the parcel back before sunrise.", "ship", "JUST IN TIME")]),
    ("rabbit-lantern-swap", "The Rabbit and the Borrowed Lantern", "animal mystery",
     [("EVERY LANTERN WENT BLUE", "A rabbit hung festival lanterns, but every flame glowed blue when the music began.", "forest", "BLUE LIGHT"),
      ("THE PAINT WAS NORMAL", "She checked the glass and the candles, yet nothing explained the strange color.", "door", "NO CLUE"),
      ("THE BLUE PAPER SHADOW", "She discovered a blue paper banner reflecting its color onto every white lantern.", "book", "THERE IT IS"),
      ("A RAINBOW FESTIVAL", "The villagers hung banners in different colors and made the brightest festival yet.", "forest", "RAINBOW NIGHT")]),
    ("fox-floating-market", "The Fox and the Floating Market", "animal adventure",
     [("THE MARKET FLOATED AWAY", "A fox woke to find the river market drifting downstream after its mooring snapped.", "ship", "DRIFTING AWAY"),
      ("THE ROPE WAS TOO SHORT", "She tried to pull the market home, but her longest rope could not reach the dock.", "ship", "NOT ENOUGH"),
      ("A CHAIN OF BOATS", "She asked the fishermen to connect their boats and pass a new rope across the current.", "ship", "WORK TOGETHER"),
      ("BREAKFAST ON THE RIVER", "The floating market returned safely and opened with hot breakfast for its rescuers.", "door", "MARKET OPEN")]),
    ("mole-singing-pipes", "The Mole and the Singing Pipes", "animal mystery",
     [("THE FLOOR BEGAN TO SING", "A mole heard musical notes rising through the bakery floor every morning.", "door", "WHO IS SINGING"),
      ("THE OVEN WAS SILENT", "He checked the oven and the cellar, but the mysterious tune kept changing.", "door", "STILL SINGING"),
      ("WIND IN THE WATER PIPES", "He traced the melody to a loose pipe cap that whistled whenever the wind blew.", "forest", "MYSTERY SOLVED"),
      ("A NEW BAKERY SONG", "The baker tuned the pipe caps and greeted customers with a different song each day.", "door", "SING ALONG")]),

]


# Combinatorial drafts supplement the authored library. They are deliberately
# NOT marked production-ready: variants need editorial review before publishing.
DRAFT_ACTORS = ("badger", "beaver", "deer", "duck", "ferret", "goat", "hare", "lynx", "otter", "panda", "raccoon", "wolf")
DRAFT_PROBLEMS = (
    ("broken bridge", "a bridge collapsed before the village delivery", "a chain of stepping stones", "the stranded parcel reached its owner"),
    ("missing bell", "the town bell vanished before the morning ceremony", "a trail of brass dust", "the ceremony began with the recovered bell"),
    ("flooded garden", "a sudden flood covered the community garden", "a hidden drainage channel", "the vegetables survived and fed the village"),
    ("lost compass", "the expedition compass disappeared in the fog", "the moss on the northern trees", "the explorers found the route home"),
    ("dark lighthouse", "the lighthouse went dark during a storm", "a polished mirror and lantern", "the fishing boats returned safely"),
    ("stolen recipe", "the festival recipe vanished from the bakery", "flour footprints on the cellar stairs", "the bakers recovered the recipe"),
    ("silent orchestra", "every instrument went quiet before the concert", "a loose curtain blocking the stage acoustics", "the audience heard the concert"),
    ("runaway balloon", "the festival balloon drifted above the rooftops", "a long ribbon caught in a weather vane", "the balloon landed without harm"),
    ("frozen fountain", "the village fountain froze before the market", "warm water from the nearby mill", "the fountain flowed again"),
    ("vanishing footprints", "mysterious footprints ended at the riverbank", "a concealed wooden walkway", "the missing traveler was found"),
    ("collapsed tunnel", "the mountain tunnel closed before the supply run", "an old miners' side passage", "the supplies arrived on time"),
    ("broken telescope", "the observatory telescope failed before the eclipse", "a loose focusing wheel", "everyone watched the eclipse"),
    ("lost invitation", "the royal invitation blew into the forest", "a paper corner caught on a thorn", "the invited guests arrived"),
    ("stuck windmill", "the windmill stopped before harvest", "a rope tangled around its axle", "the mill ground grain again"),
    ("empty well", "the village well ran dry overnight", "an underground spring behind loose stones", "clean water returned"),
    ("missing lantern", "the mountain guide lost the only lantern", "glowing fireflies beside the trail", "the hikers reached shelter"),
    ("cracked dam", "water leaked through the old pond wall", "clay hidden beneath the reeds", "the pond stayed full"),
    ("lost painting", "the gallery painting disappeared before opening", "a fresh paint mark on a delivery cart", "the exhibition opened"),
    ("stalled ferry", "the ferry engine stopped midstream", "a spare paddle beneath the deck", "the passengers reached shore"),
    ("silent clock", "the station clock stopped before departure", "a small gear lodged beneath the dial", "the trains left on schedule"),
)
DRAFT_SETBACKS = (
    ("the first rope snapped under the strain", "a stronger knot tied around an iron hook"),
    ("the heavy rain erased the first clue", "a dry footprint beneath the wooden roof"),
    ("the narrow passage was blocked by fallen branches", "a hidden opening behind the old gate"),
    ("the villagers doubted the rescue could work", "a careful demonstration that won their help"),
    ("the first tool broke before the job was finished", "a forgotten spare in the workshop"),
)

# Editorial triage only. Passing does not grant publication approval.
COMPATIBLE_SETBACKS = {
    "broken bridge": (0, 2, 3, 4),
    "missing bell": (1, 3),
    "flooded garden": (0, 2, 3, 4),
    "lost compass": (1, 2, 3),
    "dark lighthouse": (0, 3, 4),
    "stolen recipe": (1, 3),
    "silent orchestra": (3, 4),
    "runaway balloon": (0, 3, 4),
    "frozen fountain": (2, 3, 4),
    "vanishing footprints": (1, 2, 3),
    "collapsed tunnel": (0, 2, 3, 4),
    "broken telescope": (3, 4),
    "lost invitation": (1, 3),
    "stuck windmill": (0, 3, 4),
    "empty well": (2, 3, 4),
    "missing lantern": (1, 3),
    "cracked dam": (0, 3, 4),
    "lost painting": (1, 3),
    "stalled ferry": (0, 3, 4),
    "silent clock": (3, 4),
}

def editorial_screen():
    """Collapse actor swaps and incompatible setbacks into a rewrite queue."""
    selected, rejected, seen = [], [], set()
    for record in draft_catalog():
        key, title, genre, beats = record
        problem = next((p for p in COMPATIBLE_SETBACKS if ("-" + p.replace(" ", "-") + "-") in key), None)
        # Drafts are emitted in fixed five-arc order per actor/problem.
        setback = int(key.rsplit("-", 1)[1]) % len(DRAFT_SETBACKS)
        signature = (problem, setback)
        if problem is None or setback not in COMPATIBLE_SETBACKS[problem]:
            rejected.append((key, "causal_mismatch"))
        elif signature in seen:
            rejected.append((key, "character_swap_duplicate"))
        else:
            seen.add(signature)
            selected.append(record)
    return {"rewrite_queue": selected, "rejected": rejected}

DRAFT_CAUSAL_ARCS = {
    "broken bridge": (
        ("the temporary boards slid off the wet riverbank", "building a braced crossing above the strongest current"),
        ("the rope disappeared into the rushing water", "fastening a new line to a secure upstream anchor"),
        ("the narrow path ended at a flooded ditch", "marking a stable route around the damaged section"),
        ("the first crossing frightened the younger villagers", "testing each plank together before anyone crossed"),
        ("the borrowed hammer cracked the support beam", "using the miller's spare timber to reinforce the span"),
    ),
    "missing bell": (
        ("the tower stairs were locked for repairs", "asking the caretaker to unlock the safe access door"),
        ("the search led to the wrong market stall", "following the distinctive brass dust toward the workshop"),
        ("the old storage passage was blocked", "finding the tower's second service entrance"),
        ("the crowd accused the wrong visitor", "checking the delivery register before making accusations"),
        ("the first inspection found only an empty hook", "searching the repair cart for the missing bell"),
    ),
    "flooded garden": (
        ("a dirt wall sent water toward the houses", "opening the old drain away from the vegetable beds"),
        ("the runoff washed away the first channel", "lining the diversion trench with flat stones"),
        ("the garden gate trapped the floodwater inside", "lifting the gate and clearing the downstream ditch"),
        ("the volunteers disagreed about where to dig", "marking the lowest safe outlet with a measuring string"),
        ("the borrowed shovel broke in the mud", "using the gardener's long-handled spade to clear debris"),
    ),
    "lost compass": (
        ("the path vanished into thick fog", "following the marked ridge instead of guessing directions"),
        ("a stream erased the footprints ahead", "using the moss and fixed trail signs to confirm north"),
        ("the group reached a fork with no signs", "checking the ridge contour against an old guidepost"),
        ("two hikers disagreed about the correct direction", "comparing landmarks before choosing the route"),
        ("the map became soaked and unreadable", "tracing the established trail markers back to camp"),
    ),
    "dark lighthouse": (
        ("the exposed flame blew out in the storm", "sheltering a lantern behind the tower window"),
        ("the backup lantern had no usable wick", "borrowing a sealed lamp from the harbor office"),
        ("the tower door jammed in the wind", "entering through the sheltered service passage"),
        ("the fishermen could not distinguish the signal", "using a repeated flash pattern agreed with the captains"),
        ("the first mirror slipped from its stand", "securing the reflector to a heavy wooden frame"),
    ),
    "stolen recipe": (
        ("the flour trail ended in the crowded market", "checking the bakery's locked storeroom first"),
        ("a spilled sack covered the footprints", "following the paper scraps toward the cellar"),
        ("the cellar door stuck behind stacked crates", "moving the crates carefully with the apprentice"),
        ("the bakers blamed a visitor without evidence", "checking who moved the recipe box during cleaning"),
        ("the first search damaged a loose notebook page", "sorting the scattered sheets on a clean table"),
    ),
    "silent orchestra": (
        ("the drummer's louder rhythm drowned out the strings", "checking whether the stage curtains blocked the sound"),
        ("the first rehearsal ended with exhausted players", "listening from the back row before changing the arrangement"),
        ("the musicians faced away from the audience", "turning the music stands toward the open hall"),
        ("the conductor insisted the instruments were broken", "testing one instrument from the audience seats"),
        ("the curtain pulley jammed halfway open", "asking the stage crew to free the rope safely"),
    ),
    "runaway balloon": (
        ("the trailing cord snapped in the gust", "using the emergency tether kept beside the launch platform"),
        ("the balloon drifted beyond the low rooftops", "alerting the ground crew at the far field"),
        ("the narrow alley blocked the rescue cart", "taking the cart around the square to the open meadow"),
        ("the crowd pulled the ropes in different directions", "assigning one signal caller to coordinate the crew"),
        ("the first grappling hook missed the ribbon", "waiting until the balloon passed the safe landing field"),
    ),
    "frozen fountain": (
        ("hammering cracked a decorative stone", "circulating warm water through the frozen outlet"),
        ("the hot water cooled before reaching the blockage", "insulating the pipe while gently warming the joint"),
        ("the first drain was blocked by fallen leaves", "clearing the leaves before testing the flow"),
        ("the workers argued about using open flames", "choosing a safe low-temperature thawing method"),
        ("the old wrench slipped on the icy valve", "using a properly fitted tool after warming the handle"),
    ),
    "vanishing footprints": (
        ("the footprints disappeared in river mud", "looking for marks on the dry boards nearby"),
        ("the rain washed away the shallow tracks", "searching beneath the covered landing for fresh clues"),
        ("the bridge ended at a locked storage gate", "asking the ferryman who last used the walkway"),
        ("the villagers followed the wrong set of tracks", "comparing the boot pattern with the missing traveler's shoes"),
        ("the first lantern failed beside the bank", "searching at daylight along the safe marked path"),
    ),
    "collapsed tunnel": (
        ("loose stones kept falling near the entrance", "closing the unsafe approach and consulting the old route map"),
        ("the first shovel could not shift the rubble", "finding the miners' maintained side passage"),
        ("the mountain trail was too steep for supplies", "using the lower service path shown on the sign"),
        ("the group wanted to climb over the collapse", "keeping everyone outside the danger zone while scouting"),
        ("the cart wheel broke on the rocky detour", "borrowing a smaller handcart for the safe passage"),
    ),
    "broken telescope": (
        ("polishing the glass did not improve the image", "checking the focus wheel and eyepiece alignment"),
        ("the tripod shook whenever someone approached", "stabilizing the legs on the observatory platform"),
        ("the eyepiece was fitted backward", "asking the astronomer to reinstall the correct lens"),
        ("the crowd demanded a view before the instrument was ready", "testing the telescope safely before admitting visitors"),
        ("the focusing knob spun without moving the lens", "tightening the loose set screw inside the housing"),
    ),
    "lost invitation": (
        ("the wind scattered the letters into wet grass", "collecting the envelopes beneath the sheltered hedges"),
        ("the address ink blurred in the rain", "matching each wax seal with the invitation register"),
        ("the garden gate locked before the courier returned", "asking the caretaker to open the side entrance"),
        ("two guests claimed the same envelope", "checking the royal guest list against the seals"),
        ("the courier's satchel strap broke", "borrowing a covered basket to protect the recovered letters"),
    ),
    "stuck windmill": (
        ("the rope tightened around the axle", "locking the sails before removing the tangled line"),
        ("the blades would not turn despite strong wind", "checking the brake lever before touching the gears"),
        ("the mill ladder was blocked by grain sacks", "clearing the maintenance route with the miller"),
        ("the villagers pushed the sails in different directions", "assigning the miller to coordinate the safe repair"),
        ("the first tool slipped off the jammed pulley", "using the correct spanner to free the mechanism"),
    ),
    "empty well": (
        ("digging beside the well only loosened dry clay", "examining the old spring channel behind the stones"),
        ("the bucket returned with only mud", "clearing sediment from the intake opening"),
        ("the well cover hid the inspection hatch", "opening the hatch with the mason's help"),
        ("the villagers blamed the dry weather alone", "checking the blocked feeder channel before digging deeper"),
        ("the first hook bent inside the shaft", "using the mason's lifting tool to clear the obstruction"),
    ),
    "missing lantern": (
        ("the first candle went out in the wind", "following the marked trail toward the ranger cabin"),
        ("the trail forked beside a steep ravine", "checking the safe route markers by moonlight"),
        ("the hikers lost sight of the nearest shelter", "staying together and using the ridge's familiar landmarks"),
        ("the group wanted to split up and search", "keeping everyone together until the ranger arrived"),
        ("the spare torch had an empty battery", "using the ranger's emergency signal markers"),
    ),
    "cracked dam": (
        ("the leaf patch washed out of the crack", "pressing clay behind a woven branch barrier"),
        ("the water undermined the first pile of stones", "reinforcing the bank above the leaking channel"),
        ("the reed bed hid the damaged section", "marking the leak before clearing vegetation"),
        ("the villagers argued over draining the whole pond", "testing a small controlled repair first"),
        ("the borrowed spade snapped against a rock", "using the beaver's broad digging tool to reach the clay"),
    ),
    "lost painting": (
        ("the first search followed the wrong delivery cart", "checking fresh paint streaks against the frame"),
        ("rain washed the muddy tracks from the courtyard", "looking beneath the covered loading platform"),
        ("the gallery storeroom was locked", "asking the curator to inspect the delivery inventory"),
        ("visitors accused the cleaners without evidence", "checking the transport log before searching anyone"),
        ("the packing blanket hid the edge of the frame", "unfolding the delivery cart's coverings with the curator"),
    ),
    "stalled ferry": (
        ("the towing rope broke against the current", "organizing the passengers to use emergency paddles"),
        ("the engine would not restart in the rain", "steering toward the sheltered landing without the motor"),
        ("reeds caught the ferry's rudder", "freeing the obstruction from the deck with a boat hook"),
        ("the passengers all paddled at different speeds", "calling a steady rhythm for coordinated strokes"),
        ("the spare oar cracked against a rock", "using the remaining paddles to reach the nearby pier"),
    ),
    "silent clock": (
        ("turning the hands did not restart the mechanism", "checking the gears behind the dial"),
        ("the pendulum stopped again after one swing", "removing the loose screw wedged near its pivot"),
        ("the inspection hatch stuck shut", "asking the clockmaker to open the maintenance panel"),
        ("the passengers argued about the real time", "checking the conductor's reliable watch first"),
        ("the first screwdriver slipped inside the housing", "using a correctly sized tool to secure the loose gear"),
    ),
}

def draft_catalog(limit=996):
    """Supply exactly 996 uniquely identified plot *drafts*, not reviewed stories."""
    output = []
    for actor in DRAFT_ACTORS:
        for problem, crisis, clue, resolution in DRAFT_PROBLEMS:
            for setback, solution in DRAFT_SETBACKS:
                key = f"{actor}-{problem.replace(' ', '-')}-{len(output)}"
                # Use a problem-specific failed attempt; random generic setbacks
                # previously made many combinations nonsensical.
                obstacle, recovery = DRAFT_CAUSAL_ARCS[problem][DRAFT_SETBACKS.index((setback, solution))]
                beats = [
                    ("THE PROBLEM", f"A {actor} discovered that {crisis}, while the village waited anxiously for help before sunset.", "forest", "URGENT"),
                    ("THE FIRST ATTEMPT FAILED", f"The {actor} tried a quick repair, but {obstacle}, making the original plan impossible to finish.", "door", "NOT YET"),
                    ("A BETTER IDEA", f"Remembering {clue}, the {actor} chose a safer approach: {recovery}, and asked the neighbors to assist.", "book", "NEW PLAN"),
                    ("THE RESCUE", f"After everyone followed the revised plan, {resolution}, and the {actor} checked that the solution would last.", "forest", "SAVED"),
                ]
                output.append((key, f"The {actor.title()} and the {problem.title()} — {len(output) + 1}", "animal adventure", beats))
                if len(output) >= limit:
                    return output
    return output

def plot_fingerprint(beats):
    """Fingerprint story narration, excluding cosmetic titles and labels."""
    narration = " ".join(speech for _, speech, _, _ in beats).casefold()
    normalized = " ".join(re.sub(r"[^a-z0-9 ]", " ", narration).split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()



# A small, manually rewritten set. These are story scripts, not automatic
# approvals: visual/audio QA and publication safeguards still apply.
REWRITTEN_PLOTS = [
    ("beaver-bridge-detour", "The Beaver's Midnight Bridge", "animal adventure", [
        ("THE LAST DELIVERY", "A beaver promised to deliver medicine before sunset, but the village bridge collapsed beneath the first cart.", "forest", "BRIDGE DOWN"),
        ("THE RIVER ROSE", "He tried floating the cart across, until rising water swept his rope downstream and soaked the wooden wheels.", "forest", "PLAN FAILED"),
        ("THE OLD MILL", "A waterwheel nearby gave him an idea: he lashed spare boards into a narrow bridge anchored against the mill.", "door", "NEW CROSSING"),
        ("JUST IN TIME", "The neighbors steadied the boards while the beaver carried the medicine across, reaching the waiting family before dark.", "forest", "DELIVERED"),
    ]),
    ("otter-lighthouse-mirror", "The Otter and the Dark Lighthouse", "animal adventure", [
        ("LIGHTS OUT", "A sudden storm extinguished the harbor lighthouse while three fishing boats were still navigating toward the rocky shore.", "forest", "NO SIGNAL"),
        ("THE LANTERN FAILED", "An otter climbed the tower with a lantern, but the wind blew out its flame before anyone could see it.", "door", "STORM"),
        ("A FLASH OF SILVER", "Noticing moonlight on a metal tray, she positioned polished mirrors to reflect a sheltered lantern across the harbor.", "book", "MIRROR SIGNAL"),
        ("HOME THROUGH THE FOG", "The captains followed the steady flashes between the rocks, and every boat entered the harbor safely.", "forest", "ALL SAFE"),
    ]),
    ("hare-lost-invitation", "The Hare and the Missing Invitation", "animal comedy", [
        ("THE ROYAL PICNIC", "A hare was responsible for delivering the royal picnic invitations, until a sudden gust scattered them into the forest.", "forest", "INVITES LOST"),
        ("WRONG ADDRESSES", "He chased one letter through the rain, only to discover its ink had blurred into unreadable streaks.", "door", "OH NO"),
        ("THE WAX SEALS", "He noticed each envelope carried a different animal crest, and matched those crests to the houses along the trail.", "book", "SMART CLUE"),
        ("EVERYONE ARRIVED", "The hare delivered the final invitation just before noon, and the picnic guests surprised him with the biggest carrot cake.", "forest", "PICNIC SAVED"),
    ]),
    ("raccoon-gallery-cart", "The Raccoon and the Vanished Painting", "animal mystery", [
        ("EMPTY FRAME", "The gallery's prize painting disappeared an hour before opening, leaving a clean rectangle on the dusty wall.", "door", "MISSING ART"),
        ("A FALSE TRAIL", "A raccoon followed muddy pawprints outside, but they led only to the gardener's abandoned boots.", "forest", "WRONG CLUE"),
        ("THE BLUE STREAK", "A fresh blue paint streak on a delivery cart matched the frame, so she checked beneath its folded blankets.", "book", "FOUND IT"),
        ("THE EXHIBITION OPENS", "The painting had slipped behind the cart during unloading; the raccoon rehung it as the first visitors arrived.", "door", "CASE CLOSED"),
    ]),
    ("panda-windmill-rope", "The Panda and the Stubborn Windmill", "animal comedy", [
        ("NO FLOUR TODAY", "The village windmill stopped spinning on baking day, leaving the panda baker with sacks of unground wheat.", "forest", "MILL STOPPED"),
        ("A LOUD CREAK", "He pushed a sail with a long pole, but a tangled rope tightened around the axle and stopped it again.", "door", "STUCK AGAIN"),
        ("THE SAFETY KNOT", "After securing the sails, he climbed the maintenance ladder and untied the knot using a small wooden lever.", "book", "ROPE RELEASED"),
        ("BREAD FOR EVERYONE", "The windmill turned freely once more, and the baker shared fresh warm loaves with the helpers who held the ladder.", "forest", "FRESH BREAD"),
    ]),
    ("fox-fountain-thaw", "The Fox and the Frozen Fountain", "animal adventure", [
        ("THE WINTER MARKET", "The fox arrived to prepare the market fountain, but an overnight freeze had blocked every pipe beneath the square.", "forest", "FROZEN SOLID"),
        ("THE WRONG FIX", "He chipped at the ice with a hammer, cracking a decorative tile while the water remained trapped underground.", "door", "STOP HAMMERING"),
        ("A WARMER ROUTE", "The baker showed him a warm drainage channel, so they circulated gently heated water around the frozen outlet.", "book", "GENTLE HEAT"),
        ("THE FIRST SPLASH", "The fountain flowed before the market opened, and the fox replaced the cracked tile with help from the mason.", "forest", "MARKET READY"),
    ]),
    ("owl-clock-gear", "The Owl and the Station Clock", "animal mystery", [
        ("THE CLOCK STOPPED", "At dawn the station clock froze at midnight, and the passengers began missing their trains despite arriving early.", "door", "WRONG TIME"),
        ("A RISKY SHORTCUT", "An owl tried pushing the clock hands forward, but the gears jammed and the minute hand slipped loose.", "door", "GEARS JAMMED"),
        ("THE TINY SCREW", "Looking behind the dial, she spotted a fallen screw wedged between two gears and removed it with careful tweezers.", "book", "SMALL CLUE"),
        ("BACK ON TRACK", "After resetting the mechanism against the conductor's watch, she heard the clock chime as the next train arrived.", "forest", "ON TIME"),
    ]),
    ("goat-garden-drain", "The Goat and the Floating Garden", "animal adventure", [
        ("GARDEN UNDERWATER", "A sudden downpour flooded the shared vegetable garden, and a goat watched the seedlings disappear beneath muddy water.", "forest", "FLOOD"),
        ("THE WALL COLLAPSED", "He built a mud barrier across the path, but the rising water pushed through and washed the barrier away.", "door", "NOT ENOUGH"),
        ("THE OLD CHANNEL", "A grandmother remembered a buried stone drain, so the goat cleared its opening and guided water toward the meadow.", "book", "DRAIN FOUND"),
        ("SEEDLINGS SAVED", "The garden slowly emptied, and the neighbors replanted the damaged rows together before the next sunny morning.", "forest", "GARDEN SAVED"),
    ]),
    ("lynx-telescope-focus", "The Lynx and the Eclipse", "animal mystery", [
        ("THE SKY SHOW", "The village gathered for a rare eclipse, but the observatory telescope displayed nothing except a blurry gray circle.", "forest", "BLURRY SKY"),
        ("THE LENS WAS CLEAN", "A lynx polished the glass again and again, yet every adjustment made the image even less clear.", "door", "STILL BLURRY"),
        ("ONE LOOSE WHEEL", "She found the focusing wheel wobbling on its shaft, tightened the hidden screw and tested the alignment safely.", "book", "FOCUS FIXED"),
        ("A SHARED VIEW", "With proper solar filters in place, the visitors took turns viewing the eclipse through the restored telescope.", "forest", "SKY REVEALED"),
    ]),
    ("duck-ferry-paddles", "The Duck and the Stalled Ferry", "animal adventure", [
        ("MIDRIVER TROUBLE", "A ferry stalled halfway across the river, leaving the passengers drifting slowly toward a bend full of reeds.", "forest", "ENGINE STOPPED"),
        ("THE ROPE SNAPPED", "A duck tried towing the heavy ferry with a rope, but the current pulled it tight until the knot broke.", "door", "ROPE BROKE"),
        ("TWO SPARE PADDLES", "The captain found emergency paddles beneath the seats, and the duck organized the passengers to row in rhythm.", "book", "ROW TOGETHER"),
        ("SAFE AT THE PIER", "Their coordinated strokes guided the ferry to a sheltered pier, where a mechanic finally repaired the engine.", "forest", "SAFE LANDING"),
    ]),
    ("badger-well-spring", "The Badger and the Empty Well", "animal adventure", [
        ("NO WATER LEFT", "The village well ran dry before breakfast, and a badger discovered that every bucket scraped against bare stone.", "forest", "WELL EMPTY"),
        ("DIGGING DEEPER", "He dug beside the wall for hours, but the earth crumbled and no water appeared beneath the dry clay.", "door", "DRY GROUND"),
        ("THE COOL STONES", "A patch of unusually cool stones revealed an old spring channel, which the badger cleared with the village mason.", "book", "SPRING FOUND"),
        ("WATER RETURNS", "Clean water trickled back into the well, and the neighbors built a cover to protect their newly restored supply.", "forest", "FRESH WATER"),
    ]),
    ("ferret-bell-brass", "The Ferret and the Missing Bell", "animal mystery", [
        ("SILENT MORNING", "The town bell disappeared before the harvest ceremony, leaving a ferret caretaker staring at the empty wooden tower.", "door", "BELL GONE"),
        ("A MISLEADING SOUND", "He chased a ringing noise toward the market, but it came from a peddler's basket of tiny handbells.", "forest", "FALSE ALARM"),
        ("THE BRASS TRAIL", "A trail of brass filings led behind the blacksmith's shed, where workers had moved the bell for emergency repairs.", "book", "MYSTERY SOLVED"),
        ("THE FIRST CHIME", "The repaired bell returned to its tower just as the crowd assembled, and its bright chime opened the celebration.", "forest", "CEREMONY SAVED"),
    ]),
    ("deer-tunnel-passage", "The Deer and the Hidden Passage", "animal adventure", [
        ("THE ROAD BLOCKED", "A landslide sealed the mountain tunnel while a deer was transporting warm blankets to the village beyond the ridge.", "forest", "TUNNEL CLOSED"),
        ("A DANGEROUS DETOUR", "She searched the steep cliff path, but loose stones slid beneath her feet and forced her to turn back.", "door", "TURN BACK"),
        ("THE MINER'S MAP", "Inside the old watch hut, she discovered a miners' map showing a safe side passage around the blocked entrance.", "book", "SECRET ROUTE"),
        ("BLANKETS DELIVERED", "With a guide checking the passage first, the deer carried the blankets through and reached the waiting villagers.", "forest", "WARM AGAIN"),
    ]),
    ("wolf-lantern-fireflies", "The Wolf and the Missing Lantern", "animal adventure", [
        ("LOST AT DUSK", "A wolf guided hikers along the mountain trail until their only lantern slipped from a pack into the rushing stream.", "forest", "NO LIGHT"),
        ("THE WRONG TURN", "He followed a pale reflection between the trees, but it was moonlight on water beside a steep drop.", "door", "DANGER AHEAD"),
        ("THE FIREFLY PATH", "Tiny fireflies gathered near the sheltered valley, revealing familiar trail markers that led toward the ranger's cabin.", "book", "FOLLOW THE SIGNS"),
        ("SHELTER AT LAST", "The wolf kept everyone together until they reached the cabin, where a ranger offered blankets and a new lantern.", "forest", "SAFE TONIGHT"),
    ]),
    ("beaver-dam-clay", "The Beaver and the Leaking Pond", "animal adventure", [
        ("THE POND SHRINKS", "A beaver discovered water escaping through a crack in the pond wall just before the annual duckling swim.", "forest", "LEAK FOUND"),
        ("THE PATCH WASHED AWAY", "He packed leaves into the crack, but the current carried them away and the water level continued dropping.", "door", "PATCH FAILED"),
        ("CLAY BENEATH REEDS", "Under the reeds he found sticky clay, then pressed it into the crack behind a woven barrier of branches.", "book", "STRONGER PATCH"),
        ("THE SWIM GOES ON", "The leak slowed to a stop, and the ducklings crossed the restored pond while the beaver checked his repair.", "forest", "POND SAVED"),
    ]),
    ("squirrel-recipe-flour", "The Squirrel and the Stolen Recipe", "animal mystery", [
        ("THE FESTIVAL DISASTER", "A squirrel baker opened her recipe box before the autumn festival and found the prize-winning pie instructions missing.", "door", "RECIPE GONE"),
        ("THE WRONG SUSPECT", "She followed floury footprints into the courtyard, but the tracks belonged to her apprentice carrying fresh bread.", "forest", "FALSE LEAD"),
        ("THE CELLAR CLUE", "A torn recipe corner clung to a flour sack beside the cellar stairs, where a draft had scattered loose papers.", "book", "PAPER TRAIL"),
        ("THE PIE RETURNS", "She recovered the recipe beneath the cellar shelf and baked the festival pie while her apprentice secured the box.", "door", "FESTIVAL SAVED"),
    ]),
    ("raccoon-orchestra-curtain", "The Raccoon and the Silent Orchestra", "animal comedy", [
        ("THE QUIET CONCERT", "A raccoon conductor raised his baton at the village concert, but the audience could barely hear a single instrument.", "door", "TOO QUIET"),
        ("LOUDER DIDN'T HELP", "He ordered the musicians to play harder, until a drumstick snapped and the exhausted players stopped altogether.", "forest", "PLAN FAILED"),
        ("THE HIDDEN CURTAIN", "From the balcony he noticed a thick rehearsal curtain hanging between the stage and audience, swallowing every note.", "book", "CURTAIN FOUND"),
        ("MUSIC AT LAST", "The stage crew lifted the curtain, and the orchestra played softly enough to hear every melody across the hall.", "door", "BRAVO"),
    ]),
    ("hedgehog-balloon", "The Hedgehog and the Runaway Balloon", "animal adventure", [
        ("THE PROBLEM", "The festival balloon broke loose while children waited for their first ride.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He grabbed its trailing cord, but a gust lifted him off the ground.", "door", "SETBACK"),
        ("THE DISCOVERY", "He wrapped the cord around a sturdy weather vane and called the ground crew.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The crew lowered the balloon safely, then secured every rope before reopening rides.", "forest", "RESOLVED"),
    ]),
    ("badger-compass", "The Badger and the Foggy Compass", "animal adventure", [
        ("THE PROBLEM", "A badger's compass disappeared just as fog swallowed the hiking trail.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He guessed the direction from the wind and led everyone toward a marsh.", "door", "SETBACK"),
        ("THE DISCOVERY", "He found north-facing moss and confirmed the path against an old trail marker.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The hikers reached the ranger station before the fog thickened again.", "forest", "RESOLVED"),
    ]),
    ("beaver-painting", "The Beaver and the Wet Painting", "animal adventure", [
        ("THE PROBLEM", "A new mural vanished from the school wall before the opening celebration.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The beaver accused the cleaners, but their brushes were still perfectly dry.", "door", "SETBACK"),
        ("THE DISCOVERY", "He followed colored drops to a moving cart and discovered the canvas rolled beneath it.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The painter restored the canvas and everyone helped hang it securely.", "forest", "RESOLVED"),
    ]),
    ("deer-bridge", "The Deer and the Paper Bridge", "animal adventure", [
        ("THE PROBLEM", "A deer found the footbridge broken while a school parade waited across the stream.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "She tried balancing planks on stones, but the first plank slid into the water.", "door", "SETBACK"),
        ("THE DISCOVERY", "She spotted the old footpath upstream and marked its shallow stepping stones.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The parade crossed with adult guides and reached the school without a fall.", "forest", "RESOLVED"),
    ]),
    ("duck-bell", "The Duck and the Midnight Bell", "animal adventure", [
        ("THE PROBLEM", "A bell began ringing at midnight although the clock tower was locked.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The duck climbed the stairs and found no one pulling the rope.", "door", "SETBACK"),
        ("THE DISCOVERY", "A loose shutter swung against the rope whenever the wind rose.", "book", "NEW CLUE"),
        ("THE PAYOFF", "She fastened the shutter and the town finally slept through the night.", "forest", "RESOLVED"),
    ]),
    ("ferret-garden", "The Ferret and the Midnight Garden", "animal adventure", [
        ("THE PROBLEM", "The community garden was flooded each morning despite clear overnight skies.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The ferret blamed rain clouds and built a roof that trapped the heat.", "door", "SETBACK"),
        ("THE DISCOVERY", "He traced bubbling soil to a cracked irrigation pipe beneath the vegetable beds.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The gardeners repaired the pipe and planted the rescued seedlings in fresh soil.", "forest", "RESOLVED"),
    ]),
    ("goat-lighthouse", "The Goat and the Lighthouse Shadow", "animal adventure", [
        ("THE PROBLEM", "Ships mistook a strange shadow for the harbor entrance during heavy fog.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The goat lit extra lamps, but their reflections confused the approaching captains.", "door", "SETBACK"),
        ("THE DISCOVERY", "He discovered a torn sail covering the lighthouse lens and removed it.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The clear beam guided the ships between the rocks and into harbor.", "forest", "RESOLVED"),
    ]),
    ("hare-recipe", "The Hare and the Pepper Pie", "animal adventure", [
        ("THE PROBLEM", "A hare mixed up two recipe cards before the town baking contest.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He added more sugar, but the pie only tasted stranger after baking.", "door", "SETBACK"),
        ("THE DISCOVERY", "A pepper stain revealed the savory card hidden beneath the sweet one.", "book", "NEW CLUE"),
        ("THE PAYOFF", "He started again with the right recipe and shared both pies afterward.", "forest", "RESOLVED"),
    ]),
    ("lynx-clock", "The Lynx and the Clock That Ran Backward", "animal adventure", [
        ("THE PROBLEM", "The station clock began running backward as the morning train approached.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The lynx pushed its hands ahead, but they spun backward again.", "door", "SETBACK"),
        ("THE DISCOVERY", "She found a maintenance lever set to reverse during an overnight repair.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The engineer restored the setting and the passengers caught their train.", "forest", "RESOLVED"),
    ]),
    ("otter-well", "The Otter and the Echoing Well", "animal adventure", [
        ("THE PROBLEM", "Strange knocks echoed from the village well whenever someone lowered a bucket.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The otter dropped pebbles to investigate, but the sounds only multiplied.", "door", "SETBACK"),
        ("THE DISCOVERY", "A loose wooden pulley struck the stone lining each time the rope moved.", "book", "NEW CLUE"),
        ("THE PAYOFF", "She replaced the pulley with the carpenter and the knocking stopped.", "forest", "RESOLVED"),
    ]),
    ("panda-tunnel", "The Panda and the Tunnel Lanterns", "animal adventure", [
        ("THE PROBLEM", "The mountain tunnel lights failed during the annual lantern procession.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The panda carried a single candle inside, but a draft extinguished it.", "door", "SETBACK"),
        ("THE DISCOVERY", "He located the outdoor switch box and found a fallen branch pressing the emergency cutoff.", "book", "NEW CLUE"),
        ("THE PAYOFF", "A technician cleared the branch and restored the lights before the procession.", "forest", "RESOLVED"),
    ]),
    ("raccoon-ferry", "The Raccoon and the Missing Ferry Rope", "animal adventure", [
        ("THE PROBLEM", "The ferry drifted away from its dock before the market passengers boarded.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The raccoon swam after it, but the current pushed the vessel farther downstream.", "door", "SETBACK"),
        ("THE DISCOVERY", "He reached a riverside winch and used its spare line to secure the ferry.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The captain inspected the mooring and brought everyone aboard safely.", "forest", "RESOLVED"),
    ]),
    ("wolf-fountain", "The Wolf and the Singing Fountain", "animal adventure", [
        ("THE PROBLEM", "The town fountain began whistling so loudly that nobody could hear the musicians.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The wolf covered the spout, but water sprayed across the market stalls.", "door", "SETBACK"),
        ("THE DISCOVERY", "He discovered a leaf wedged in the narrow nozzle and cleared it carefully.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The fountain returned to a gentle splash and the musicians finished their song.", "forest", "RESOLVED"),
    ]),
    ("squirrel-invitation", "The Squirrel and the Wrong Invitation", "animal adventure", [
        ("THE PROBLEM", "A squirrel delivered wedding invitations to the wrong houses before the ceremony.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "She retraced the route, but the wind scattered her address list.", "door", "SETBACK"),
        ("THE DISCOVERY", "A ribbon color on each envelope matched the decorations outside each guest's home.", "book", "NEW CLUE"),
        ("THE PAYOFF", "She corrected the deliveries and the guests arrived just before the vows.", "forest", "RESOLVED"),
    ]),
    ("owl-dam", "The Owl and the Moonlit Dam", "animal adventure", [
        ("THE PROBLEM", "An owl noticed the pond dropping each night despite a freshly repaired dam.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He searched for cracks in daylight and found the wall apparently sound.", "door", "SETBACK"),
        ("THE DISCOVERY", "At moonrise he spotted water slipping beneath a fallen log beside the bank.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The beavers moved the log and sealed the channel before the pond emptied.", "forest", "RESOLVED"),
    ]),
    ("fox-telescope", "The Fox and the Missing Star", "animal adventure", [
        ("THE PROBLEM", "The fox astronomer promised children a view of a bright comet after sunset.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He searched every corner of the sky but the telescope showed only darkness.", "door", "SETBACK"),
        ("THE DISCOVERY", "He discovered its protective lens cap had never been removed after cleaning.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The children watched the comet through the uncovered lens with careful guidance.", "forest", "RESOLVED"),
    ]),
    ("badger-orchestra", "The Badger and the Broken Drum", "animal adventure", [
        ("THE PROBLEM", "The marching band's drum fell silent moments before the town parade began.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The badger tightened the straps until one snapped and the drummer nearly dropped it.", "door", "SETBACK"),
        ("THE DISCOVERY", "He found a loose drumhead ring and borrowed the repair kit from a nearby workshop.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The drummer tested the repaired instrument and led the parade down the square.", "forest", "RESOLVED"),
    ]),
    ("beaver-compass", "The Beaver and the River Compass", "animal adventure", [
        ("THE PROBLEM", "A beaver lost the map showing where to deliver supplies across the marsh.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He followed a straight bank and became trapped among reeds and deep channels.", "door", "SETBACK"),
        ("THE DISCOVERY", "He climbed a lookout tree and recognized the three bends marked on an old sign.", "book", "NEW CLUE"),
        ("THE PAYOFF", "He followed the safer waterways and delivered the supplies before dusk.", "forest", "RESOLVED"),
    ]),
    ("deer-lantern", "The Deer and the Glass Lantern", "animal adventure", [
        ("THE PROBLEM", "A deer carried a lantern to the hilltop festival when its glass cracked.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "She shielded the flame with leaves, but sparks threatened the dry grass.", "door", "SETBACK"),
        ("THE DISCOVERY", "A potter offered a spare ceramic lantern with openings protected from the wind.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The deer carried the safer light uphill and joined the festival at sunset.", "forest", "RESOLVED"),
    ]),
    ("duck-clock", "The Duck and the Fast Clock", "animal adventure", [
        ("THE PROBLEM", "The bakery clock ran ten minutes fast and everyone arrived before the bread was ready.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The duck reset the hands, but the clock gained time again within an hour.", "door", "SETBACK"),
        ("THE DISCOVERY", "She noticed the pendulum weight had slipped after the baker moved the shelf.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The clockmaker adjusted the weight and the morning customers finally arrived on time.", "forest", "RESOLVED"),
    ]),
    ("ferret-bridge", "The Ferret and the Rope Crossing", "animal adventure", [
        ("THE PROBLEM", "A ferret needed to cross a creek to return a lost puppy before sunset.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He tested a rotten rope bridge and one of its boards cracked beneath him.", "door", "SETBACK"),
        ("THE DISCOVERY", "He spotted a fallen tree farther upstream and checked it with the forest ranger.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The ranger guided them across the stable trunk and reunited the puppy with its family.", "forest", "RESOLVED"),
    ]),
    ("goat-painting", "The Goat and the Rainy Portrait", "animal adventure", [
        ("THE PROBLEM", "A goat's portrait began to run when rain entered the gallery roof.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He moved the painting beneath a cloth, but the damp fabric touched the wet colors.", "door", "SETBACK"),
        ("THE DISCOVERY", "He found a dry storeroom and carried the framed work there without touching the surface.", "book", "NEW CLUE"),
        ("THE PAYOFF", "A conservator stabilized the painting while workers repaired the leaking roof.", "forest", "RESOLVED"),
    ]),
    ("hare-ferry", "The Hare and the Floating Basket", "animal adventure", [
        ("THE PROBLEM", "A hare's basket of festival flowers drifted away aboard an unattended ferry.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He jumped toward the ferry, but it floated beyond the edge of the dock.", "door", "SETBACK"),
        ("THE DISCOVERY", "He rang the harbor bell and directed the captain toward the drifting boat.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The captain recovered the basket and the hare decorated the festival stage.", "forest", "RESOLVED"),
    ]),
    ("lynx-garden", "The Lynx and the Garden Thief", "animal adventure", [
        ("THE PROBLEM", "A lynx found rows of carrots missing from the school garden each morning.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "She watched for thieves all night but saw only shadows moving near the fence.", "door", "SETBACK"),
        ("THE DISCOVERY", "At sunrise she discovered rabbits entering through a gap behind the compost heap.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The students built a rabbit-safe barrier and planted a separate patch for wildlife.", "forest", "RESOLVED"),
    ]),
    ("otter-bell", "The Otter and the Underwater Bell", "animal adventure", [
        ("THE PROBLEM", "A ceremonial bell fell from the pier into shallow water before the harbor festival.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The otter pulled its rope, but the knot slipped off the slippery metal handle.", "door", "SETBACK"),
        ("THE DISCOVERY", "She tied a lifting sling around the bell and asked the dock crew for a winch.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The bell rose safely onto the pier and rang as the festival boats arrived.", "forest", "RESOLVED"),
    ]),
    ("panda-recipe", "The Panda and the Missing Ingredient", "animal adventure", [
        ("THE PROBLEM", "A panda promised mooncakes for the village feast but discovered the pantry had no honey.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He tried replacing it with plain water and the first batch crumbled apart.", "door", "SETBACK"),
        ("THE DISCOVERY", "A neighbor showed him ripe dates that could be cooked into a thick sweet paste.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The new batch held together beautifully and the panda shared the recipe.", "forest", "RESOLVED"),
    ]),
    ("raccoon-tunnel", "The Raccoon and the Tunnel Echo", "animal adventure", [
        ("THE PROBLEM", "An eerie voice frightened travelers away from the old railway tunnel.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The raccoon shouted into the darkness, and the echo answered from three directions.", "door", "SETBACK"),
        ("THE DISCOVERY", "He traced the sound to wind passing through a broken ventilation grate.", "book", "NEW CLUE"),
        ("THE PAYOFF", "Workers repaired the grate and the travelers used the tunnel again.", "forest", "RESOLVED"),
    ]),
    ("wolf-windmill", "The Wolf and the Windmill Kite", "animal adventure", [
        ("THE PROBLEM", "A wolf's kite tangled in the windmill just before the blades began turning.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He tugged the string from below, pulling it tighter around a wooden sail.", "door", "SETBACK"),
        ("THE DISCOVERY", "He asked the miller to lock the blades and climbed the safe maintenance ladder.", "book", "NEW CLUE"),
        ("THE PAYOFF", "They freed the kite without damage and flew it in the open meadow.", "forest", "RESOLVED"),
    ]),
    ("squirrel-well", "The Squirrel and the Well Bucket", "animal adventure", [
        ("THE PROBLEM", "The well bucket disappeared and the village could not collect water for breakfast.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The squirrel tied a basket to the rope, but its wide gaps spilled every drop.", "door", "SETBACK"),
        ("THE DISCOVERY", "She found the missing bucket lodged beneath a low stone ledge inside the well.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The mason lifted it with a hook and replaced the worn rope.", "forest", "RESOLVED"),
    ]),
    ("owl-lighthouse", "The Owl and the False Beacon", "animal adventure", [
        ("THE PROBLEM", "A bright light on the cliffs confused ships approaching the real lighthouse.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The owl chased the beam across the rocks but could not find its source.", "door", "SETBACK"),
        ("THE DISCOVERY", "From above he spotted sunlight reflecting off a large mirror left by campers.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The campers moved the mirror and the harbor beacon stood out clearly.", "forest", "RESOLVED"),
    ]),
    ("fox-dam", "The Fox and the Buried Gate", "animal adventure", [
        ("THE PROBLEM", "The reservoir rose too high after a storm and the outlet gate would not open.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The fox pushed the gate wheel until its wooden handle splintered.", "door", "SETBACK"),
        ("THE DISCOVERY", "He found mud packed inside the drainage grate and called the maintenance team.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The crew cleared the grate and opened the gate gradually to lower the water.", "forest", "RESOLVED"),
    ]),
    ("badger-ferry", "The Badger and the Last Ferry", "animal adventure", [
        ("THE PROBLEM", "A badger missed the final ferry while carrying medicine to an island clinic.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He tried waving from the dock, but the boat was already rounding the bend.", "door", "SETBACK"),
        ("THE DISCOVERY", "He used the harbor signal lamp to send the agreed emergency return pattern.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The captain returned after confirming the signal and delivered the medicine.", "forest", "RESOLVED"),
    ]),
    ("beaver-lantern", "The Beaver and the Paper Lantern", "animal adventure", [
        ("THE PROBLEM", "The village's giant paper lantern tore just before the night procession.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The beaver patched it with wet glue, but the paper sagged under its own weight.", "door", "SETBACK"),
        ("THE DISCOVERY", "He built a light bamboo frame and attached dry paper panels around a safe LED lamp.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The lantern glowed above the parade without tearing again.", "forest", "RESOLVED"),
    ]),
    ("deer-orchestra", "The Deer and the Missing Violin", "animal adventure", [
        ("THE PROBLEM", "A deer violinist lost her instrument before the woodland concert.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "She borrowed a larger cello but could not play the rehearsed melody.", "door", "SETBACK"),
        ("THE DISCOVERY", "She heard a familiar string vibrate inside the empty rehearsal wagon.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The violin had slid beneath a blanket and she performed the opening solo.", "forest", "RESOLVED"),
    ]),
    ("duck-invitation", "The Duck and the Rain-Soaked Letters", "animal adventure", [
        ("THE PROBLEM", "A duck courier dropped the festival invitations into a puddle before delivery.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He dried the pages beside a fire but the handwritten addresses became unreadable.", "door", "SETBACK"),
        ("THE DISCOVERY", "He matched each envelope's wax seal to the guest list kept at the town hall.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The invitations reached their owners and the festival began with a full crowd.", "forest", "RESOLVED"),
    ]),
    ("ferret-telescope", "The Ferret and the Blurry Moon", "animal adventure", [
        ("THE PROBLEM", "A ferret's telescope showed two moons during the astronomy club meeting.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He adjusted the tripod repeatedly but the duplicate image stayed in place.", "door", "SETBACK"),
        ("THE DISCOVERY", "He noticed a loose eyepiece lens shifting whenever he touched the tube.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The club leader secured the eyepiece and everyone saw one sharp moon.", "forest", "RESOLVED"),
    ]),
    ("goat-clock", "The Goat and the Clockwork Parade", "animal adventure", [
        ("THE PROBLEM", "A clockwork parade float stopped moving halfway through the town square.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "The goat wound its spring harder, but the wheels refused to turn.", "door", "SETBACK"),
        ("THE DISCOVERY", "He found a ribbon caught between the rear gears and switched off the mechanism.", "book", "NEW CLUE"),
        ("THE PAYOFF", "After removing the ribbon safely, the float rolled through the cheering crowd.", "forest", "RESOLVED"),
    ]),
    ("hare-dam", "The Hare and the River Warning", "animal adventure", [
        ("THE PROBLEM", "A hare spotted water rising behind the dam during a village picnic.", "forest", "THE PROBLEM"),
        ("THE SETBACK", "He shouted from the bank, but the music drowned out his warning.", "door", "SETBACK"),
        ("THE DISCOVERY", "He rang the emergency bell and led families along the marked higher path.", "book", "NEW CLUE"),
        ("THE PAYOFF", "The engineers opened the spillway while everyone waited safely above the river.", "forest", "RESOLVED"),
    ]),
]

# Fresh authored plots for quality-gated replenishment; never bypass QA.
NEW_AUTHORED_PLOTS = [
    ("raccoon-midnight-bakery", "The Raccoon and the Midnight Bakery", "animal comedy", [
        ("A BELL IN THE NIGHT", "At midnight, a raccoon baker heard his shop bell ring although the door was locked and the street was empty.", "door", "WHO RANG"),
        ("FLOUR ON THE FLOOR", "He followed a trail of flour toward the oven, but the tiny footprints stopped beneath a tall stack of trays.", "door", "MYSTERY STEPS"),
        ("A HIDDEN CUSTOMER", "Behind the trays, he found a hungry hedgehog sheltering from the rain beside the bell's loose pull cord.", "forest", "FOUND YOU"),
        ("BREAKFAST BEFORE DAWN", "The raccoon baked a warm bun for his guest, fixed the bell cord, and opened the bakery to a line of smiling neighbors.", "door", "BAKERY OPEN"),
    ]),
    ("penguin-stage-fright", "The Penguin and the Silent Trumpet", "animal comedy", [
        ("THE CONCERT BEGAN", "A young penguin lifted his trumpet for the winter concert, but not a single note came out before the waiting crowd.", "signal", "NO SOUND"),
        ("A PANICKED SEARCH", "He blew harder and checked every valve while his bandmates tried to keep the audience entertained with clapping.", "robot", "WHERE IS MUSIC"),
        ("THE RED MITTEN", "His friend spotted the penguin's red mitten tucked inside the trumpet bell where he had hidden it for safekeeping.", "signal", "THE MISSING NOTE"),
        ("ONE LOUD FINISH", "He pulled out the mitten, played the opening melody, and turned his embarrassing mistake into the band's funniest encore.", "signal", "ENCORE"),
    ]),
    ("beaver-floating-garden", "The Beaver and the Floating Garden", "animal adventure", [
        ("THE GARDEN DRIFTED", "A beaver woke to find the village's floating vegetable garden drifting away after a night of heavy river rain.", "ship", "GARDEN ADRIFT"),
        ("THE ROPE SNAPPED", "She paddled after the garden and caught its loose rope, but the current snapped it against a submerged branch.", "ship", "HOLD ON"),
        ("THE QUIET INLET", "She noticed a calm inlet beyond the reeds and used her paddle to steer the garden toward its sheltered water.", "forest", "SAFE WATER"),
        ("HARVEST AT HOME", "The villagers helped secure new mooring lines, and everyone celebrated with vegetables picked from the rescued garden.", "forest", "HARVEST SAVED"),
    ]),

    ("mole-lantern-path", "The Mole and the Lantern Path", "animal adventure", [
        ("THE PATH WENT DARK", "A young mole found that the lanterns marking the woodland footpath had gone dark after a storm.", "forest", "LOST LIGHT"),
        ("THE FIRST FIX FAILED", "He replaced the first lantern's bulb, but the next lantern still flickered and went out.", "signal", "STILL DARK"),
        ("THE HIDDEN WIRE", "Following the loose cable, he discovered a fallen branch had pulled the power connector apart.", "forest", "FOUND THE BREAK"),
        ("THE LIGHTS RETURNED", "With the park keeper's help, he reconnected the safe low voltage line and guided the walkers home.", "signal", "WAY HOME"),
    ]),
    ("otter-paper-boat", "The Otter and the Paper Boat Race", "animal comedy", [
        ("THE BOAT SANK", "An otter folded a paper boat for the river race, but the first splash soaked its hull.", "ship", "SOGGY START"),
        ("A HEAVIER BOAT", "She tried wrapping the boat in thick cloth, only to watch it sink before the starting bell.", "ship", "TOO HEAVY"),
        ("A LIGHTER DESIGN", "She shaped a fresh paper hull and protected its bottom with a thin coat of natural wax.", "book", "NEW DESIGN"),
        ("THE FINISH LINE", "Her little boat floated across the pond, and she cheered for the other racers beside her.", "ship", "FINISH"),
    ]),
    ("badger-missing-notes", "The Badger and the Vanishing Music", "animal mystery", [
        ("THE MUSIC VANISHED", "A badger conductor opened the orchestra's folder and found every sheet of music missing.", "book", "EMPTY FOLDER"),
        ("THE WIND'S TRICK", "He searched the rehearsal hall while a draft kept rattling the window beside the stage.", "door", "FOLLOW THE WIND"),
        ("NOTES IN THE RAFTERS", "Looking upward, he saw the pages caught in a net beneath the ceiling vent.", "book", "THERE THEY ARE"),
        ("THE CONCERT BEGAN", "The stage crew recovered the pages safely, and the orchestra played its opening song on time.", "signal", "MUSIC RETURNS"),
    ]),
    ("fox-festival-lights", "The Fox and the Festival of Shadows", "animal adventure", [
        ("THE LIGHTS WENT OUT", "A fox arrived at the lantern festival just as the village square lost its electricity.", "door", "DARK FESTIVAL"),
        ("A BRIGHT IDEA FAILED", "She placed one lantern on the stage, but its tiny glow could not reach the crowd.", "signal", "NOT ENOUGH"),
        ("THE MIRROR CIRCLE", "She arranged the festival's polished mirrors around several battery lanterns to spread their light.", "robot", "REFLECT THE GLOW"),
        ("SHADOWS STARTED DANCING", "The villagers used the gentle reflections to perform shadow puppets until the power returned.", "forest", "SHOWTIME"),
    ]),
]

NEW_AUTHORED_PLOTS.extend([
    ("otter-tide-clock", "The Otter and the Tide Clock", "animal mystery", [
        ("THE CLOCK RAN BACKWARD", "An otter noticed the harbor clock ticking backward just before the fishing boats were due to return.", "clock", "WRONG WAY"),
        ("THE KEEPER WAS MISSING", "She searched the empty clock tower while the rising tide covered the steps to the dock.", "door", "TIME RUNNING OUT"),
        ("A ROPE ON THE GEAR", "She found a wet mooring rope wrapped around the clock's exposed drive wheel and called the keeper for help.", "robot", "HIDDEN SNAG"),
        ("THE HARBOR BELLS RANG", "The keeper freed the rope and restored the clock, while the otter guided the returning boats with the harbor bell.", "signal", "SAFE RETURN"),
    ]),
    ("lynx-glass-orchestra", "The Lynx and the Glass Orchestra", "animal comedy", [
        ("THE MUSIC WAS MISSING", "A young lynx arrived at the village concert and discovered the instruments had been packed onto the wrong wagon.", "signal", "NO INSTRUMENTS"),
        ("EVERY IDEA SOUNDED WRONG", "She tried drumming on crates and whistling through leaves, but neither could carry a melody across the square.", "forest", "TRY AGAIN"),
        ("THE RAIN MADE MUSIC", "She heard raindrops ringing against different glass jars and arranged them under the eaves by their pitch.", "door", "A NEW SOUND"),
        ("AN UNEXPECTED ENCORE", "The villagers joined with wooden spoons and gentle taps, turning the rainy evening into a sparkling glass orchestra.", "signal", "BRAVO"),
    ]),
    ("panda-bridge-paint", "The Panda and the Invisible Bridge", "animal adventure", [
        ("THE BRIDGE DISAPPEARED", "A panda carrying festival lanterns reached the stream and found the narrow footbridge hidden beneath thick morning fog.", "forest", "WHERE IS IT"),
        ("THE FIRST STEP SLIPPED", "He tried following the sound of the water, but his foot slipped on a wet stone near the bank.", "ship", "TOO DANGEROUS"),
        ("BELLS MARKED THE WAY", "He spotted the bridge's safety rope and tied tiny bells along it so the other walkers could follow its safe route.", "signal", "FOLLOW THE BELLS"),
        ("LIGHTS ACROSS THE STREAM", "The walkers crossed one at a time holding the rope, and the panda hung the lanterns on the far side for the festival.", "forest", "WE MADE IT"),
    ]),
    ("seal-snow-postoffice", "The Seal and the Snow Post Office", "animal mystery", [
        ("LETTERS IN THE SNOW", "A seal found the seaside post office buried beneath fresh snow just before the winter holiday deliveries.", "door", "MAIL TRAPPED"),
        ("THE SLED LOST ITS LOAD", "She packed the letters onto a small sled, but a gust scattered the envelopes across the frozen harbor.", "ship", "OH NO"),
        ("A MAP OF FOOTPRINTS", "She noticed each envelope had landed beside a different animal's fresh footprints and sorted the letters by the nearby tracks.", "book", "FOLLOW THE TRACKS"),
        ("EVERY LETTER ARRIVED", "With help from the neighbors, she delivered the rescued mail and found a thank you card waiting at her own door.", "door", "SPECIAL DELIVERY"),
    ]),
    ("heron-moon-mirror", "The Heron and the Missing Moon", "animal fantasy", [
        ("THE MOON VANISHED", "A heron looked into the village pond and saw that the bright full moon had disappeared from the water.", "planet", "WHERE IS THE MOON"),
        ("THE WATER TURNED CLOUDY", "She searched behind the reeds and splashed toward the center, only making the muddy pond harder to see through.", "forest", "NO REFLECTION"),
        ("THE MILL GATE OPENED", "She discovered a blocked stream had stirred the pond with silt and asked the miller to reopen the gentle water channel.", "ship", "CLEAR WATER"),
        ("TWO MOONS SHONE", "As the water settled, the moon returned to the pond beside its twin in the sky, and the heron laughed at the mystery.", "planet", "MYSTERY SOLVED"),
    ]),
    ("ferret-bakery-lift", "The Ferret and the Rising Bread", "animal comedy", [
        ("THE DOUGH ESCAPED", "A ferret baker returned from the market to find a giant bowl of dough swelling over the kitchen counter.", "door", "TOO MUCH DOUGH"),
        ("THE LID FLEW OFF", "He pushed a heavy lid onto the bowl, but the dough rose again and tipped the lid onto the flour sacks.", "robot", "IT KEEPS GROWING"),
        ("SMALLER LOAVES", "He divided the dough into little trays and gave each loaf enough space to rise without spilling.", "book", "SMART FIX"),
        ("A VILLAGE FEAST", "The bakery filled with warm rolls, and the ferret shared the unexpected extra bread with the whole village.", "door", "FRESH BREAD"),
    ]),
])


# Curated cross-genre narratives: distinct settings, stakes, reversals, and resolutions.
NEW_AUTHORED_PLOTS.extend([
    ("robot-last-sunrise", "The Robot Who Borrowed Tomorrow", "science fiction", [
        ("THE SUN DID NOT RISE", "A maintenance robot woke to find its city's artificial sunrise projector dark and every morning train stopped.", "robot", "NO SUNRISE"),
        ("THE BACKUP WAS EMPTY", "It raced through silent tunnels to the backup battery, only to discover the stored power had already drained away.", "signal", "POWER GONE"),
        ("THE STARS HELD ENERGY", "A forgotten observatory had solar cells charged by yesterday's light, and the robot rerouted their reserve through the old grid.", "planet", "ONE LAST CHARGE"),
        ("A CITY WOKE TOGETHER", "The projector painted dawn across the skyline as the trains restarted, while the robot saved the remaining energy for tomorrow.", "signal", "DAWN RETURNS"),
    ]),
    ("detective-vanishing-score", "The Detective and the Vanishing Score", "detective mystery", [
        ("THE FINAL PAGE VANISHED", "Minutes before a grand concert, a young detective discovered the orchestra's handwritten finale missing from its locked glass case.", "book", "LOCKED ROOM"),
        ("EVERY CLUE POINTED UP", "A feather and a trail of glitter led toward the ceiling, but the skylight had been locked since midnight.", "door", "IMPOSSIBLE EXIT"),
        ("THE MIRROR HELD THE NOTES", "She spotted the music reflected backward in a polished trophy and realized the score had been pressed onto the glass by condensation.", "book", "HIDDEN IN PLAIN SIGHT"),
        ("THE CONCERT FINISHED LOUD", "The conductor copied the recovered notes, and the final chord revealed the culprit was a harmless paper-loving magpie.", "signal", "CASE CLOSED"),
    ]),
    ("astronaut-silent-moon", "The Astronaut and the Silent Moon", "space adventure", [
        ("THE MOON STOPPED ANSWERING", "An astronaut approached a remote lunar greenhouse after its weekly radio signal vanished during a meteor shower.", "planet", "RADIO SILENCE"),
        ("THE AIRLOCK WOULD NOT OPEN", "Dust clogged the outer door while the greenhouse's oxygen alarm flashed behind the frosted window.", "robot", "TIME RUNNING OUT"),
        ("A SHADOW SHOWED THE PATH", "She noticed the rotating shadow of a broken antenna pointing to an emergency maintenance hatch beneath the solar panels.", "signal", "HIDDEN HATCH"),
        ("THE GARDEN SENT A MESSAGE", "She restored the antenna and heard the botanist's relieved voice as the greenhouse lights bloomed across the crater.", "planet", "SIGNAL RESTORED"),
    ]),
    ("chef-midnight-train", "The Chef and the Midnight Train", "culinary comedy", [
        ("DINNER LEFT WITHOUT HIM", "A chef watched the midnight dining train depart while his famous festival dessert sat unfinished on the station platform.", "ship", "TRAIN GONE"),
        ("THE CART LOST A WHEEL", "He pushed a food cart along the parallel market road until one wheel broke and his ingredients scattered into the rain.", "door", "TOTAL DISASTER"),
        ("THE MARKET BECAME A KITCHEN", "Street vendors lent him hot pans and fresh fruit, and he transformed the ruined dessert into tiny caramelized fruit cups.", "forest", "NEW RECIPE"),
        ("THE TRAIN CAME BACK HUNGRY", "A signal delay returned the passengers to the station, where they discovered the best meal of their journey waiting outside.", "signal", "SURPRISE FEAST"),
    ]),
    ("witch-rain-contract", "The Witch and the Borrowed Rain", "cozy fantasy", [
        ("A TOWN RAN OUT OF CLOUDS", "An apprentice witch promised rain for the harvest festival, but her cloud jar produced only one tiny silver droplet.", "planet", "EMPTY SKY"),
        ("THE DROPLET STOLE COLORS", "Every place the droplet landed turned gray, and the apprentice feared she had traded the village's colors for rain.", "forest", "WRONG SPELL"),
        ("THE COLORS WERE HIDING", "She followed the gray footprints to a sleeping rainbow moth whose wings had folded around the missing colors.", "forest", "SECRET REVEALED"),
        ("A RAINBOW WATERED FIELDS", "The witch woke the moth gently, and its bright wings scattered gentle rain over the crops without washing away a single color.", "planet", "HARVEST SAVED"),
    ]),
    ("runner-bridge-relay", "The Runner and the Broken Relay", "sports drama", [
        ("THE BATON SNAPPED", "A rookie runner's relay baton cracked moments before the championship race, and her team had no spare equipment.", "signal", "RACE IN DANGER"),
        ("THE FIRST HANDOFF FAILED", "She practiced with a rolled cloth substitute, but it slipped from her teammate's hand on every fast exchange.", "forest", "TRY AGAIN"),
        ("A QUIET COACH SAW THE ANSWER", "Their coach noticed the cloth needed a rigid center and built a legal replacement from an approved spare training baton.", "robot", "ONE MORE CHANCE"),
        ("THE LAST HANDOFF WORKED", "They completed a clean race and finished second, celebrating teamwork instead of the victory they had imagined.", "signal", "FINISH TOGETHER"),
    ]),
    ("museum-clock-heist", "The Museum and the Clockwork Thief", "heist mystery", [
        ("THE DIAMOND CASE WAS EMPTY", "A museum guard found an antique compass missing while the alarms stayed silent and every gallery door remained sealed.", "clock", "IMPOSSIBLE THEFT"),
        ("THE CLOCK STRUCK THIRTEEN", "A peculiar thirteenth chime led her to a clockwork display where fresh scratches marked the wooden floor.", "clock", "STRANGE CHIME"),
        ("THE THIEF WAS A MACHINE", "Inside the display, a misprogrammed cleaning automaton had mistaken the compass for a loose metal part and stored it in its toolbox.", "robot", "NOT A CRIMINAL"),
        ("THE EXHIBIT GOT A NEW GUARD", "The compass returned to its case, and the museum gave the little automaton a proper route that avoided priceless objects.", "door", "TREASURE SAFE"),
    ]),
    ("ghost-hotel-key", "The Ghost and the Hotel Key", "gentle supernatural", [
        ("ROOM NINE KEPT RINGING", "A night clerk heard the service bell ring from a hotel room that had been empty for fifty years.", "door", "WHO IS THERE"),
        ("THE HALLWAY TURNED COLD", "She followed a trail of old keys to the locked room, where a shadow appeared whenever the grandfather clock chimed.", "clock", "MIDNIGHT SHADOW"),
        ("THE SHADOW WAS A MESSAGE", "A hidden projector behind the clock played an old recording of the hotel's founder asking someone to reopen the ballroom.", "robot", "A LAST WISH"),
        ("THE BALLROOM FILLED AGAIN", "The clerk restored the dusty ballroom and hosted a dance, while the mysterious bell rang once more in celebration.", "signal", "ONE LAST DANCE"),
    ]),
    ("submarine-glass-reef", "The Submarine and the Glass Reef", "underwater thriller", [
        ("THE SONAR SAW A WALL", "A research submarine found an enormous shimmering barrier across its route home as its navigation lights began to fail.", "ship", "TRAPPED BELOW"),
        ("THE CURRENT PUSHED HARDER", "The captain tried reversing, but a powerful current dragged the vessel toward sharp rocks beneath the glowing wall.", "ship", "DANGER AHEAD"),
        ("THE WALL WAS ALIVE", "The scientist recognized a harmless bloom of luminous plankton and used its movement to locate a calm channel between the rocks.", "planet", "FOLLOW THE LIGHT"),
        ("THE SUBMARINE ROSE AT DAWN", "They escaped through the channel and surfaced beside the research ship with footage of the rare underwater spectacle.", "ship", "BACK TO SUNLIGHT"),
    ]),
    ("historian-secret-stair", "The Historian and the Hidden Staircase", "historical adventure", [
        ("THE MAP LOST A STREET", "A young historian found a century-old town map showing a street that had vanished beneath the modern market square.", "book", "MISSING STREET"),
        ("THE STONE STEPS ENDED", "She opened a forgotten cellar door and descended a staircase that ended abruptly against a newly built brick wall.", "door", "DEAD END"),
        ("THE OLD BELL MARKED NORTH", "An inscription on the market bell revealed the staircase had been mirrored on the map to hide a wartime shelter.", "signal", "READ IT BACKWARD"),
        ("A SHELTER BECAME A MUSEUM", "She found the preserved shelter and helped the town open it as a place to remember the families who once hid there.", "book", "HISTORY FOUND"),
    ]),
    ("lovers-star-post", "The Two Letters Under the Stars", "romantic adventure", [
        ("TWO LETTERS CROSSED", "Two childhood friends sent invitations to meet at the old observatory, but a storm scattered both envelopes.", "planet", "MISSED CONNECTION"),
        ("THE TRAIN WENT THE WRONG WAY", "Each boarded a different train believing the other had moved away, and the observatory was due to close at sunset.", "ship", "LAST CHANCE"),
        ("THE CONSTELLATION WAS A CLUE", "A shared sketch of their favorite constellation revealed the same rooftop meeting place written on the back of both letters.", "planet", "SAME DESTINATION"),
        ("THEY MET ABOVE THE CITY", "They reached the observatory from opposite staircases and watched the first stars appear, laughing about their crossed journeys.", "planet", "TOGETHER AGAIN"),
    ]),
    ("inventor-pocket-storm", "The Inventor and the Pocket Storm", "steampunk fantasy", [
        ("THUNDER FIT IN A BOX", "A young inventor accidentally trapped a tiny thunderstorm inside a brass music box during the village science fair.", "robot", "POCKET THUNDER"),
        ("THE BOX BEGAN TO FLOAT", "Every time the music played, the storm grew stronger and lifted the inventor's workshop off its foundations.", "signal", "UP IN THE AIR"),
        ("THE WIND FOLLOWED MUSIC", "She realized the storm changed direction with each note and composed a low melody that guided it toward an open window.", "book", "CHANGE THE TUNE"),
        ("RAIN FELL ON THE GARDEN", "The little storm escaped into the sky and watered the dry community garden while the workshop settled safely back to earth.", "forest", "PERFECT WEATHER"),
    ]),
])

AUTHORED_KEYS = {row[0] for row in PILLOW_DUO_PLOTS + PLOTS + REWRITTEN_PLOTS + NEW_AUTHORED_PLOTS + EDITORIAL_OCT2026_PLOTS + CROSSGENRE_DIRECTED_24 + AUTHORED_REPLENISHMENT_OCT2026 + AUTHORED_BATCH_341 + AUTHORED_BATCH_364 + AUTHORED_BATCH_407 + AUTHORED_BATCH_420 + AUTHORED_BATCH_421}

def catalog(excluded_ids=None, excluded_titles=None, limit=256, excluded_plot_hashes=None, history=None, include_drafts=False, include_expansion=False):
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
    # The 2,000 new combinations are visible to editorial review ONLY.
    # Default production supply remains authored; no bulk publishing of drafts.
    if include_expansion:
        from astra_v2.story_expansion_2000 import candidate_records
        expanded = candidate_records()
    else:
        expanded = []
    for key, title, genre, beats in (AUTHORED_BATCH_422 + AUTHORED_BATCH_421 + AUTHORED_BATCH_420 + AUTHORED_BATCH_407 + AUTHORED_BATCH_364 + AUTHORED_BATCH_341 + AUTHORED_REPLENISHMENT_OCT2026 + PILLOW_DUO_PLOTS + PLOTS + REWRITTEN_PLOTS + NEW_AUTHORED_PLOTS + EDITORIAL_OCT2026_PLOTS + CROSSGENRE_DIRECTED_24 + (draft_catalog() if include_drafts else []) + expanded):
        # Reject malformed or weak authored arcs before any expensive render.
        if len(beats) != 4 or any(not isinstance(b, (tuple, list)) or len(b) != 4 for b in beats):
            continue
        if any(not all(isinstance(field, str) and field.strip() for field in b) for b in beats):
            continue
        if len({b[1].casefold().strip() for b in beats}) != 4:
            continue
        if any(len(b[1].split()) < 9 for b in beats):
            continue
        cid = "rayvan-forge-" + hashlib.sha256(key.encode()).hexdigest()[:16]
        fingerprint = plot_fingerprint(beats)
        if cid in excluded or title.casefold() in titles or fingerprint in seen_plots:
            continue
        seen_plots.add(fingerprint)
        result.append({
            "genre": "fiction", "kind": ("authored_causal_story" if key in AUTHORED_KEYS else "unreviewed_causal_draft"),
            "production_ready": key in AUTHORED_KEYS, "content_id": cid,
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


def propose_episode_from_story(story, series_id, episode_number, state=None, ledger_path=None):
    """Create a non-publishable episode draft while retaining source identity.

    The production story fingerprint is distinct from the causal-outline hash.
    Neither a draft nor this adapter grants publication approval.
    """
    from astra_v2.episode_planner import plan_episode, plan_episode_with_ledger

    if not isinstance(story, dict):
        raise ValueError("episode_story_invalid")
    beats = story.get("story_beats") or []
    if not isinstance(beats, list) or len(beats) < 3:
        raise ValueError("episode_requires_three_or_more_beats")
    scenes = []
    for beat in beats:
        speech = beat.get("speech") if isinstance(beat, dict) else None
        if not isinstance(speech, str) or not speech.strip():
            raise ValueError("episode_beat_missing_speech")
        scenes.append({
            "cause": speech.strip(),
            "action": str(beat.get("headline") or "Story progresses").strip(),
            "consequence": str(beat.get("label") or "Next scene").strip(),
        })
    source_fingerprint = story.get("plot_fingerprint")
    if not source_fingerprint:
        raise ValueError("episode_source_fingerprint_required")
    # The original source identity must agree with its own beat narration.
    # Otherwise a caller could substitute an unrelated, unused fingerprint.
    if source_fingerprint != plot_fingerprint([
        (str(beat.get("headline") or ""), beat["speech"],
         str(beat.get("background") or ""), str(beat.get("label") or ""))
        for beat in beats
    ]):
        raise ValueError("episode_source_fingerprint_mismatch")
    if ledger_path is None:
        proposal = plan_episode(series_id, episode_number, scenes, state=state,
                                source_plot_fingerprint=source_fingerprint)
    else:
        proposal = plan_episode_with_ledger(series_id, episode_number, scenes,
                                            ledger_path, state=state,
                                            source_plot_fingerprint=source_fingerprint)
    proposal["source_content_id"] = str(story.get("content_id") or "")
    return proposal
