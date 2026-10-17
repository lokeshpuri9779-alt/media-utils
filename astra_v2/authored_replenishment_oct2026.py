"""Small, human-authored four-beat replenishment batch for exhausted Shorts supply.

These are candidates, never guaranteed publishable; existing gates remain active.
"""
PLOTS = [
    ("moth-map-ink", "The Moth and the Invisible Map", "woodland mystery", [
        ("A MAP WITHOUT ROADS", "A young moth discovered a blank map in the village archive just before the lantern festival.", "book", "EMPTY MAP"),
        ("THE INK NEEDED WARMTH", "She held the paper near a lantern and watched hidden paths appear in violet ink.", "book", "SECRET PATH"),
        ("THE OLD TUNNEL", "Following the lines she found an underground passage blocked by fallen branches and cleared it with her friends.", "forest", "PASSAGE OPEN"),
        ("THE FESTIVAL RETURNED", "The passage led everyone safely around the flooded bridge and the lantern festival began on time.", "forest", "LIGHTS ON"),
    ]),
    ("badger-windmill-song", "The Badger and the Windmill Song", "village comedy", [
        ("THE WINDMILL WENT QUIET", "A badger heard the village windmill stop grinding flour on the morning of the bread contest.", "forest", "NO FLOUR"),
        ("A STRANGE WHISTLE", "He climbed the wooden stairs and heard a whistle whenever the wind struck a loose shutter.", "door", "WHISTLING"),
        ("THE SHUTTER BECAME A SAIL", "He fastened the shutter to catch the breeze and guide it back toward the stalled windmill blades.", "forest", "WIND RETURNS"),
        ("BREAD FOR EVERYONE", "The blades turned again and the baker shared warm loaves with every helper at the contest.", "door", "FRESH BREAD"),
    ]),
    ("seal-buoy-code", "The Seal and the Singing Buoy", "ocean mystery", [
        ("A BUOY SANG AT DAWN", "A seal noticed the harbor buoy making three musical notes instead of its usual warning bell.", "ship", "THREE NOTES"),
        ("THE FISHERS MISREAD IT", "The boats followed the familiar channel but found floating driftwood blocking the entrance.", "ship", "BLOCKED"),
        ("THE NOTES MARKED DEPTH", "The seal matched each note to a water depth and guided the boats through a safer passage.", "signal", "NEW ROUTE"),
        ("A SAFER HARBOR", "The harbor keeper painted the new route on the pier and thanked the seal for listening closely.", "ship", "SAFE RETURN"),
    ]),
    ("rabbit-paper-telescope", "The Rabbit and the Paper Telescope", "science fantasy", [
        ("THE STARS WERE MISSING", "A rabbit arrived at the observatory and found thick clouds hiding the annual meteor shower.", "planet", "CLOUDY SKY"),
        ("A PAPER LENS", "She built a cardboard telescope but discovered it could only magnify raindrops on the window.", "book", "RAIN DROPS"),
        ("A REFLECTION IN THE POND", "She noticed the clouds opening above the distant hill and used the pond reflection to locate a clear viewpoint.", "forest", "CLEAR PATCH"),
        ("THE METEORS APPEARED", "She led her friends uphill and they counted bright meteors together before the clouds returned.", "planet", "SHOOTING STARS"),
    ]),
    ("otter-museum-wheel", "The Otter and the Museum Wheel", "museum adventure", [
        ("THE EXHIBIT STOPPED", "An otter found the museum's model railway frozen moments before a school visit began.", "robot", "STUCK TRAIN"),
        ("THE TRACK WAS CLEAN", "She polished every rail but the little engine still could not pull its heavy carriage.", "robot", "STILL STUCK"),
        ("ONE WHEEL WAS BACKWARD", "She spotted a wheel mounted in reverse and carefully turned it to match the other axles.", "robot", "WHEEL FIX"),
        ("THE MODEL RAN AGAIN", "The train circled the museum as the children cheered and the otter explained how wheels share motion.", "robot", "ALL ABOARD"),
    ]),
    ("fox-sundial-garden", "The Fox and the Sundial Garden", "garden mystery", [
        ("THE FLOWERS CLOSED EARLY", "A fox noticed the garden flowers closing before sunset on the day of the village picnic.", "forest", "TOO EARLY"),
        ("THE SUNDIAL LIED", "He checked the stone sundial and found its shadow pointing toward evening despite the bright morning sun.", "clock", "WRONG SHADOW"),
        ("THE STATUE HAD MOVED", "He discovered a tall statue had been shifted beside the sundial and was shading the flowers.", "forest", "HIDDEN CAUSE"),
        ("SUNSHINE RETURNED", "He moved the statue back with the gardeners and the flowers opened for the afternoon picnic.", "forest", "GARDEN OPEN"),
    ]),
    ("owl-radio-ribbon", "The Owl and the Radio Ribbon", "signal adventure", [
        ("THE RADIO LOST ITS VOICE", "An owl heard the hilltop radio fall silent while a mountain rescue team waited for directions.", "signal", "NO MESSAGE"),
        ("THE ANTENNA WAS INTACT", "She inspected the antenna but found its cable twisted around a metal weather vane.", "signal", "TANGLED"),
        ("A RIBBON SHOWED THE WIND", "She tied a ribbon to the vane and watched it reveal which gusts pulled the cable too tight.", "forest", "WIND CLUE"),
        ("THE RESCUE TEAM HEARD", "She secured the cable away from the vane and the rescue team received its route before nightfall.", "signal", "CONNECTED"),
    ]),
    ("panda-ferry-bell", "The Panda and the Ferry Bell", "river comedy", [
        ("THE FERRY MISSED ITS STOP", "A panda waited at the riverside station while the ferry drifted past without hearing the landing bell.", "ship", "MISSED STOP"),
        ("THE BELL WAS MUFFLED", "He rang the bell harder but a fallen wool scarf wrapped around it absorbed every sound.", "door", "SILENT BELL"),
        ("THE SCARF BECAME A FLAG", "He removed the scarf and waved it above the dock while the bell rang clearly again.", "ship", "TWO SIGNALS"),
        ("THE FERRY TURNED BACK", "The captain saw the flag and heard the bell, then helped the panda install a permanent signal flag.", "ship", "WELCOME ABOARD"),
    ]),
    ("hedgehog-frozen-clock", "The Hedgehog and the Clock of Frost", "winter mystery", [
        ("THE CLOCK STOPPED", "A hedgehog found the town clock frozen at noon just as the winter market opened.", "clock", "FROZEN TIME"),
        ("A WARM GEAR", "He noticed that the brass hands moved whenever sunlight reached the clock tower window.", "clock", "SUNLIT GEAR"),
        ("THE MIRROR PATH", "He arranged old mirrors along the stairwell to direct morning light onto the iced mechanism.", "signal", "LIGHT RETURNS"),
        ("THE BELLS RANG", "The ice melted without breaking the gears and the market bells rang for everyone waiting below.", "clock", "MARKET OPENS"),
    ]),
    ("crab-lighthouse-prism", "The Crab and the Split Lighthouse Beam", "coastal rescue", [
        ("TWO LIGHTS AT SEA", "A crab saw two lighthouse beams sweeping different directions during a foggy harbor night.", "signal", "DOUBLE BEAM"),
        ("THE GLASS HAD SLIPPED", "She climbed the tower and found a loose prism dividing the single warning light.", "book", "LOOSE PRISM"),
        ("ONE STEADY SIGNAL", "She held the prism in place while the keeper secured its bracket against the shaking wind.", "signal", "BEAM REPAIRED"),
        ("THE FERRY RETURNED", "The restored beam guided the last ferry around the reef and safely into the harbor.", "ship", "SAFE HARBOR"),
    ]),
    ("squirrel-bridge-seeds", "The Squirrel and the Seed Bridge", "forest adventure", [
        ("THE BRIDGE WASHED AWAY", "A squirrel discovered that spring rain had swept away the narrow bridge to the community orchard.", "forest", "RIVER RISING"),
        ("THE VINES WERE TOO SHORT", "She gathered vines for a crossing but each one snapped before reaching the far bank.", "forest", "SHORT VINES"),
        ("A FLOATING NURSERY", "She tied hollow seed pods into a floating line and used it to carry a stronger rope across.", "ship", "ROPE CROSSES"),
        ("THE ORCHARD WAS SAVED", "The neighbors built a safe footbridge from the rope and harvested fruit before the next storm.", "forest", "HARVEST SAFE"),
    ]),
    ("penguin-aurora-compass", "The Penguin and the Aurora Compass", "polar exploration", [
        ("THE COMPASS SPUN", "A penguin watched the research compass spin wildly beneath an unusually bright polar sky.", "planet", "LOST NORTH"),
        ("THE RADIO STILL WORKED", "She noticed the old radio antenna pointed toward camp whenever its signal grew strongest.", "signal", "FAINT SIGNAL"),
        ("FOLLOW THE SIGNAL", "She marked each stronger radio pulse with a flag and traced a route around the crevasses.", "signal", "FLAG TRAIL"),
        ("HOME BEFORE DARK", "The team followed her flags back to the station and repaired the compass indoors.", "forest", "CAMP FOUND"),
    ]),
    ("beaver-library-pipes", "The Beaver and the Whispering Library", "library mystery", [
        ("BOOKS WERE HUMMING", "A beaver heard a low hum inside the library shelves while rain poured outside.", "book", "HUMMING SHELVES"),
        ("A HIDDEN WATER PIPE", "He traced the sound to a pipe vibrating behind the oldest collection of picture books.", "door", "PIPE FOUND"),
        ("THE VALVE WAS STUCK", "He freed a jammed valve and guided the leaking water into an empty storage barrel.", "robot", "VALVE OPEN"),
        ("THE BOOKS STAYED DRY", "The librarian moved the books to safety and thanked him before the afternoon reading began.", "book", "BOOKS SAVED"),
    ]),
    ("koala-moon-garden", "The Koala and the Moon Garden", "garden mystery", [
        ("FLOWERS GLOWED BLUE", "A koala noticed blue light spreading through the garden every night after the new fountain opened.", "forest", "BLUE GLOW"),
        ("THE LAMPS WERE OFF", "She checked every garden lamp and discovered none had been switched on after sunset.", "clock", "NO LAMPS"),
        ("THE TILES REFLECTED", "She found that blue mosaic tiles beneath the fountain reflected moonlight onto the pale petals.", "forest", "MOON MIRROR"),
        ("A NIGHT WALK BEGAN", "The gardeners kept the tiles clean and invited visitors to see the harmless moonlit colors.", "forest", "MOON GARDEN"),
    ]),
    ("turtle-bell-train", "The Turtle and the Silent Railway Bell", "railway adventure", [
        ("NO BELL AT THE CROSSING", "A turtle heard a train approaching while the village crossing bell remained silent.", "robot", "SILENT BELL"),
        ("THE WIRE WAS LOOSE", "He inspected the warning box and discovered a loose wire shaking with each passing train.", "signal", "BROKEN CONTACT"),
        ("THE FLAG CAME FIRST", "He waved a bright flag to stop travelers while the station engineer secured the connection.", "signal", "CROSSING CLOSED"),
        ("THE WARNING RETURNED", "The bell rang again and the engineer tested the crossing before allowing anyone through.", "robot", "BELL WORKS"),
    ]),
    ("deer-cloud-kites", "The Deer and the Weather Kites", "hilltop adventure", [
        ("THE WIND CHANGED", "A deer saw festival kites falling toward the valley just before the mountain race began.", "forest", "FALLING KITES"),
        ("THE RIBBONS POINTED EAST", "She noticed that every loose ribbon pointed toward a narrow gap between the hills.", "signal", "WIND CLUE"),
        ("A SAFER ROUTE", "She placed colored ribbons along the sheltered trail and guided runners away from the gusts.", "forest", "TRAIL MARKED"),
        ("THE RACE CONTINUED", "The runners reached the finish safely and used the ribbons to plan next year's course.", "forest", "SAFE FINISH"),
    ]),
    ("raccoon-museum-shadows", "The Raccoon and the Vanishing Dinosaur", "museum comedy", [
        ("THE DINOSAUR DISAPPEARED", "A raccoon entered the museum and found the dinosaur silhouette missing from its famous wall.", "robot", "EMPTY WALL"),
        ("THE MODEL WAS STILL THERE", "He checked the giant skeleton and saw every bone standing exactly where it belonged.", "robot", "BONES IN PLACE"),
        ("A CURTAIN BLOCKED LIGHT", "He discovered a new curtain covering the spotlight and opened it with the caretaker.", "door", "LIGHT RESTORED"),
        ("THE SHADOW RETURNED", "The dinosaur shadow filled the wall again and visitors laughed at the simple mystery.", "robot", "SHADOW BACK"),
    ]),
    ("dolphin-tidal-gate", "The Dolphin and the Harbor Gate", "ocean rescue", [
        ("THE HARBOR GATE JAMMED", "A dolphin noticed the harbor gate stuck halfway open while fishing boats waited outside.", "ship", "GATE STUCK"),
        ("SAND HID THE HINGE", "She followed a stream of bubbles and found sand piled around the lower hinge.", "ship", "SAND FOUND"),
        ("A CURRENT CLEARED IT", "She guided the boats to create a gentle current that washed loose sand away from the hinge.", "ship", "HINGE FREED"),
        ("THE BOATS CAME HOME", "The gate swung open and the harbor crew scheduled a cleaning before the next tide.", "ship", "HARBOR OPEN"),
    ]),
    ("mouse-theater-stars", "The Mouse and the Missing Constellation", "theater mystery", [
        ("A STAR VANISHED", "A mouse discovered that one star was missing from the theater's painted night sky.", "planet", "MISSING STAR"),
        ("THE PAINT WAS UNTOUCHED", "She checked the backdrop and found the star still painted beneath a strip of black fabric.", "book", "PAINT INTACT"),
        ("THE CURTAIN WAS MISALIGNED", "She helped the stage crew realign the curtain so the whole constellation became visible.", "door", "CURTAIN FIX"),
        ("THE SHOW BEGAN", "The audience watched the stars shine together as the opening music finally played.", "planet", "STARS RETURN"),
    ]),
    ("lynx-mountain-mirror", "The Lynx and the Mountain Mirror", "mountain rescue", [
        ("A SIGNAL VANISHED", "A lynx saw the mountain rescue station's mirror signal disappear during a clear afternoon.", "signal", "NO FLASH"),
        ("THE MIRROR HAD TURNED", "He climbed to the lookout and discovered the mounting pin had slipped in the wind.", "signal", "LOOSE MOUNT"),
        ("A STEADY REFLECTION", "He braced the mirror while the ranger replaced the pin and aligned it with the valley station.", "signal", "SIGNAL FIXED"),
        ("THE TEAM ANSWERED", "The valley station flashed a reply and the rescue teams restored their daily communication check.", "signal", "REPLY RECEIVED"),
    ]),
]
