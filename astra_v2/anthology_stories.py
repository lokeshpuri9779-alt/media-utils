"""Original standalone story anthology. No external API, copied plots or paid services."""
import hashlib

PLOTS = [
 ("the-library-of-unwritten-books","The Library of Unwritten Books","fantasy","A librarian finds a shelf of books that write themselves.",[
 ("THE EMPTY BOOK","Every night, a blank book appeared on the library desk.","door","THE DISCOVERY","reveal"),
 ("WORDS APPEARED","The pages described a stranger who would arrive before dawn.","signal","THE WARNING","build"),
 ("THE STRANGER ARRIVED","The stranger carried a book with the librarian's name on its cover.","robot","THE TWIST","twist"),
 ("SHE WROTE THE ENDING","Instead of following the prediction, she wrote her own final page.","door","THE CHOICE","payoff")]),
 ("the-robot-who-collected-laughter","The Robot Who Collected Laughter","comedy","A lonely repair robot learns why people laugh.",[
 ("A ROBOT TOLD A JOKE","Its first joke was so bad that the whole workshop went silent.","robot","THE JOKE","reveal"),
 ("IT TRIED AGAIN","The robot practiced funny faces in every mirror it could find.","robot","THE PRACTICE","build"),
 ("THE ACCIDENT","It slipped on a paintbrush and landed inside a bucket of glitter.","robot","THE SURPRISE","twist"),
 ("EVERYONE LAUGHED","The robot finally understood that joy did not require perfection.","robot","THE PAYOFF","payoff")]),
 ("the-ocean-above-the-city","The Ocean Above the City","surreal fantasy","An ocean appears in the sky and a child discovers its secret.",[
 ("FISH SWAM ABOVE","One morning, fish were swimming across the sky like clouds.","planet","IMPOSSIBLE SKY","reveal"),
 ("A CHILD FOLLOWED","A child watched a glowing jellyfish drift toward an old lighthouse.","signal","FOLLOW IT","build"),
 ("THE LIGHTHOUSE SPOKE","Its lamp had been projecting memories of a vanished ocean.","door","THE SECRET","twist"),
 ("THE WATER RETURNED","The child restored the lamp and the town remembered how to protect its shore.","forest","NEW TIDE","payoff")]),
 ("the-museum-of-tomorrows","The Museum of Tomorrows","mystery","A night guard finds tomorrow's artifacts in a locked museum.",[
 ("TOMORROW ON DISPLAY","A museum guard found a newspaper dated one day ahead.","door","FUTURE NEWS","reveal"),
 ("A BROKEN BRIDGE","The front page showed a bridge collapsing at noon.","signal","COUNTDOWN","build"),
 ("A HIDDEN EXHIBIT","Behind the wall, a machine was collecting warnings from possible futures.","robot","THE MACHINE","twist"),
 ("A DIFFERENT HEADLINE","The guard warned the city, and the next newspaper showed an empty bridge.","door","FUTURE CHANGED","payoff")]),
 ("the-garden-on-the-moon","The Garden on the Moon","hopeful science fiction","A gardener grows the first flower in a forgotten lunar greenhouse.",[
 ("ONE GREEN LEAF","A gardener found a living leaf inside an abandoned lunar dome.","forest","FIRST LEAF","reveal"),
 ("NO WATER LEFT","The greenhouse pumps were broken and the last water tank was empty.","planet","THE PROBLEM","build"),
 ("ICE UNDER THE FLOOR","She discovered frozen water beneath the greenhouse foundation.","planet","HIDDEN WATER","twist"),
 ("THE FIRST FLOWER","She melted the ice and watched a blue flower open beneath the stars.","forest","NEW BEGINNING","payoff")]),
 ("the-shadow-that-was-late","The Shadow That Was Late","absurd mystery","A boy notices his shadow arriving five seconds late.",[
 ("THE SHADOW WAITED","His shadow kept moving five seconds after he stopped.","door","FIVE SECONDS","reveal"),
 ("A SECRET MESSAGE","It pointed toward a locked door beneath the stairs.","signal","FOLLOW ME","build"),
 ("AN OLD PROJECTOR","Behind the door, a forgotten projector was replaying his grandfather's films.","robot","THE REVEAL","twist"),
 ("ONE LAST DANCE","He played the final reel and danced with the shadow on the wall.","door","THE MEMORY","payoff")]),
 ("the-train-to-nowhere","The Train to Nowhere","adventure","A lost traveler boards a train that stops at forgotten places.",[
 ("NO STATION NAME","The midnight train arrived without a destination on its sign.","ship","ALL ABOARD","reveal"),
 ("EMPTY PLATFORMS","Each stop revealed a place erased from every map.","door","LOST PLACES","build"),
 ("THE LAST TICKET","A conductor showed her a ticket printed with her childhood home.","signal","THE TICKET","twist"),
 ("A PLACE REMEMBERED","She stepped off and found the garden she thought was gone forever.","forest","HOME AGAIN","payoff")]),
 ("the-last-firefly","The Last Firefly","nature fantasy","A child follows the last firefly to revive a dark forest.",[
 ("ONE LIGHT LEFT","The forest went dark except for a single firefly.","forest","LAST LIGHT","reveal"),
 ("A HIDDEN PATH","The insect led a child through trees that had stopped blooming.","forest","FOLLOW THE GLOW","build"),
 ("THE SILENT SPRING","A blocked stream had dried the roots of the oldest tree.","planet","THE CAUSE","twist"),
 ("LIGHTS RETURNED","The child cleared the stream and thousands of fireflies lit the night.","forest","THE FOREST GLOWS","payoff")]),
 ("the-baker-and-the-sunrise","The Baker Who Borrowed Sunrise","whimsical comedy","A baker finds a way to bring morning to a sleepy town.",[
 ("THE SUN DID NOT RISE","A baker opened his shop and discovered the town was still dark.","planet","NO MORNING","reveal"),
 ("AN ODD DELIVERY","A small robot delivered a glowing jar labeled sunrise.","robot","SPECIAL DELIVERY","build"),
 ("THE JAR OPENED","Golden light spilled into the streets and every clock began ringing.","signal","LIGHT RETURNS","twist"),
 ("BREAKFAST FOR EVERYONE","The baker shared warm bread as the town welcomed its first bright morning.","forest","GOOD MORNING","payoff")]),
 ("the-cat-and-the-clocktower","The Cat in the Clocktower","animal adventure","A curious cat discovers why the town's clock has stopped.",[
 ("MIDNIGHT FOREVER","A cat noticed that every clock in town showed midnight.","door","TIME FROZEN","reveal"),
 ("UP THE TOWER","It climbed a staircase filled with gears and old feathers.","robot","THE CLIMB","build"),
 ("A BIRD WAS TRAPPED","A little bird had become stuck between the clock's giant gears.","robot","THE SECRET","twist"),
 ("TIME MOVED AGAIN","The cat freed the bird and the bells rang across the waking town.","signal","DING DONG","payoff")]),
 ("the-fox-and-the-stolen-sunrise","The Fox Who Borrowed Sunrise","animal fantasy","A fox tries to return a missing sunrise to a sleepy valley.",[
 ("THE SKY STAYED DARK","A small fox woke to discover that the sun had not risen over the valley.","forest","MISSING MORNING","reveal"),
 ("A LIGHT IN THE HILLS","Following a golden glow, the fox found a frightened firefly carrying a tiny spark.","signal","FOLLOW THE GLOW","build"),
 ("THE SPARK WAS A KEY","The spark opened an ancient lantern on the hilltop, releasing the morning light.","door","THE SECRET","twist"),
 ("MORNING CAME BACK","The valley brightened, and the fox curled up beside the lantern as birds began to sing.","forest","SUNRISE RETURNS","payoff")]),
 ("the-little-robot-and-the-kite","The Little Robot and the Kite","cartoon adventure","A repair robot builds a kite that teaches it to fly.",[
 ("THE KITE FLEW AWAY","A little robot watched its handmade kite escape over the workshop roof.","robot","KITE ESCAPES","reveal"),
 ("CHASE THROUGH THE TOWN","It followed the kite across rooftops and under the town's old clocktower.","door","ROOFTOP CHASE","build"),
 ("THE WIND WAS HELPING","At the tower, the robot discovered the kite was guiding it toward a broken weather vane.","signal","HIDDEN MESSAGE","twist"),
 ("THE SKY WAS FULL OF KITES","The robot repaired the vane and the townspeople filled the bright sky with colorful kites.","planet","FLY TOGETHER","payoff")]),
 ("the-bear-who-fixed-the-moon","The Bear Who Fixed the Moon","whimsical comedy","A bear mistakes the moon's reflection for a broken moon.",[
 ("THE MOON WAS IN PIECES","A bear saw the moon shattered across the ripples of a mountain lake.","planet","BROKEN MOON","reveal"),
 ("HE FETCHED HIS TOOLS","He carried a toolbox to the shore and tried to collect every shining fragment.","robot","REPAIR TIME","build"),
 ("A FROG SHOWED HIM","A frog jumped into the lake and the pieces danced again, revealing the trick of the water.","forest","THE REVEAL","twist"),
 ("THE BEAR LAUGHED","When the lake became still, the moon looked whole again and the bear packed away his tools.","planet","MOON RESTORED","payoff")]),,

 ("the-penguin-who-delivered-snow","The Penguin Who Delivered Snow","animal comedy","A penguin tries to deliver winter to a town that has never seen snow.",[
 ("A PACKAGE OF SNOW","A penguin arrived at the desert post office carrying a box of snow.","forest","SPECIAL DELIVERY","reveal"),
 ("THE BOX WAS MELTING","The postmaster raced to find shade before the snow disappeared.","door","HURRY UP","build"),
 ("THE CLOUD MACHINE","Inside the box was a tiny machine that could make one snow cloud.","robot","THE SECRET","twist"),
 ("A SNOWY SURPRISE","The penguin switched it on and the whole town celebrated its first snowfall.","planet","WINTER ARRIVES","payoff")]),
 ("the-monkey-and-the-missing-banana","The Monkey and the Missing Banana","animal comedy","A monkey detective discovers who keeps stealing the bananas.",[
 ("BANANAS VANISHED","Every morning, one banana disappeared from the monkey's kitchen.","forest","THE MYSTERY","reveal"),
 ("TINY FOOTPRINTS","The monkey followed little footprints past the market and into a garden.","door","FOLLOW CLUES","build"),
 ("A HUNGRY ROBOT","Behind a wall, a tiny robot was using banana peels to fuel its toy car.","robot","THE CULPRIT","twist"),
 ("THE GREAT BANANA RACE","The monkey traded a basket of peels for a ride and they raced home laughing.","ship","CASE CLOSED","payoff")]),
 ("the-dog-who-guarded-the-stars","The Dog Who Guarded the Stars","animal fantasy","A brave puppy returns fallen stars to the night sky.",[
 ("STARS FELL DOWN","A puppy woke to find three bright stars glowing in the backyard.","planet","FALLEN STARS","reveal"),
 ("THE SKY WENT DARK","As more stars fell, the puppy carried them toward the tallest hill.","forest","THE CLIMB","build"),
 ("A KITE BECAME A LADDER","A lost kite caught a strong wind and lifted the glowing stars above the clouds.","ship","THE PLAN","twist"),
 ("THE SKY SPARKLED AGAIN","The puppy released the stars and watched the night sky light up once more.","planet","MISSION COMPLETE","payoff")]),
 ("the-turtle-and-the-speedy-clock","The Turtle and the Speedy Clock","animal comedy","A turtle learns that slowing down can save a runaway town clock.",[
 ("TIME RAN TOO FAST","A turtle noticed that the town clock was spinning faster than everyone could walk.","signal","TOO FAST","reveal"),
 ("EVERYONE RUSHED","The rabbit tried to stop the gears but kept slipping on the tower stairs.","door","HURRY","build"),
 ("A SMALL STONE","The turtle found a loose stone beneath the clock and carefully fixed the wobbly gear.","robot","SLOW AND STEADY","twist"),
 ("TIME FELT RIGHT","The bells rang at the correct hour and the town finally enjoyed a peaceful afternoon.","forest","ALL FIXED","payoff")]),
 ("the-cloud-that-wanted-a-hat","The Cloud That Wanted a Hat","whimsical comedy","A tiny cloud searches for the perfect hat before a windy parade.",[
 ("A CLOUD WANTED A HAT","A little cloud floated into town wearing a paper hat that immediately blew away.","planet","HAT TROUBLE","reveal"),
 ("EVERY HAT FLEW OFF","It tried a giant helmet, a flowerpot and even a bright umbrella.","door","TRY AGAIN","build"),
 ("THE RAINBOW RIBBON","A child tied a colorful ribbon to a kite and offered it to the cloud.","ship","A BETTER IDEA","twist"),
 ("THE PARADE BEGAN","The cloud wore its rainbow kite proudly and shaded everyone at the parade.","forest","PERFECT FIT","payoff")]),
 ("the-raccoon-and-the-midnight-bakery","The Raccoon and the Midnight Bakery","animal mystery","A raccoon investigates the mysterious smell of bread at midnight.",[
 ("BREAD AT MIDNIGHT","A raccoon smelled fresh bread coming from a bakery that had been closed for years.","door","WHO IS BAKING","reveal"),
 ("FLOUR ON THE FLOOR","Tiny flour footprints led through the dark kitchen to a locked cupboard.","signal","FOLLOW THE TRAIL","build"),
 ("THE SECRET BAKER","Inside, a little robot had been baking bread for the neighborhood's stray animals.","robot","THE REVEAL","twist"),
 ("A FEAST FOR ALL","The raccoon opened the doors and every hungry animal joined the midnight feast.","forest","SHARE THE BREAD","payoff")]),
]

def catalog():
    stories = []
    for key, title, genre_label, answer, beats in PLOTS:
        cid = "rayvan-anthology-" + hashlib.sha256(key.encode()).hexdigest()[:16]
        stories.append({
            "genre": "fiction", "kind": "original_anthology", "production_ready": True,
            "content_id": cid, "title": title, "hook": beats[0][0],
            "question": beats[0][1], "answer": answer, "source": "",
            "keywords": ["original fiction", genre_label],
            "story_beats": [
                {"headline": h, "speech": speech, "visual": visual,
                 "label": label, "story_beat": role, "sub": "AN ORIGINAL RAYVAN STORY",
                 "duration": 2.1}
                for h, speech, visual, label, role in beats
            ],
        })
    return stories
