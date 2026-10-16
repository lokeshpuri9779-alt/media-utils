"""Original, non-repeating, hand-authored RAYVAN microfiction inventory.

Original narratives are unique stories, not randomized repackagings of a
single script. No news feeds, third-party video, copied media, or paid APIs.
Each storyboard uses Astra Studio's procedural imagery.
"""


def beats(*scenes):
    return [
        {
            "headline": title,
            "speech": speech,
            "visual": visual,
            "visual_intent": speech,
            "label": label,
            "sub": "AN ORIGINAL RAYVAN STORY",
            "story_beat": role,
            "duration": 2.1,
        }
        for title, speech, visual, label, role in scenes
    ]


def story(key, title, question, answer, shots):
    return {
        "genre": "fiction",
        "kind": "microfiction",
        "premium_story": False,  # procedural fiction; no external-source-media requirement
        "production_ready": True,
        "content_id": "rayvan-original-" + key + "-v1",
        "title": title,
        "hook": shots[0][0],
        "question": question,
        "answer": answer,
        "source": "",
        "keywords": ["original short fiction", "science fiction", "story"],
        "story_beats": beats(*shots),
    }


def catalog():
    return [
        story("skywhale", "The Whale Above the Clouds", "What sings above the clouds?", "A pilot follows a strange song and finds a creature living in the sky.", [("THE SKY SANG", "A pilot heard a song above the clouds.", "planet", "UNKNOWN SOUND", "reveal"), ("FOLLOW THE MUSIC", "She climbed toward the signal and saw a giant shadow.", "ship", "CLIMBING", "build"), ("THE SKY WHALE", "A luminous whale swam through the clouds carrying tiny stars.", "planet", "FIRST CONTACT", "twist"), ("A NEW CONSTELLATION", "The whale released its stars and the night sky began to shine.", "signal", "NEW STARS", "payoff")]),
        story("silentcomet", "The Comet That Stopped", "Why did a comet stop above Earth?", "A young astronomer discovers a beacon inside a motionless comet.", [("THE COMET STOPPED", "The comet stopped moving above the city.", "planet", "NO MOTION", "reveal"), ("A SIGNAL APPEARED", "An astronomer noticed a repeating pulse inside its ice.", "signal", "INCOMING", "build"), ("A MESSAGE ARRIVED", "The pulse was a map of a distant home.", "ship", "THE MAP", "twist"), ("THE JOURNEY BEGAN", "She transmitted a reply and watched the comet turn toward the stars.", "planet", "NEW HORIZON", "payoff")]),
        story("lightkeeper", "The Last Lightkeeper | Original Microfiction",
              "Who keeps the last lighthouse burning?",
              "A lone robot guards a lighthouse after the oceans vanish, waiting for one ship that never arrives.",
              [
                  ("THE SEA DISAPPEARED", "When the oceans vanished, the last lighthouse stayed on.", "planet", "THE LAST COAST", "reveal"),
                  ("ONE KEEPER REMAINED", "A little robot polished its lamp every night.", "robot", "YEAR 2089", "build"),
                  ("A SIGNAL ARRIVED", "After forty years, a ship finally answered the light.", "signal", "INCOMING", "twist"),
                  ("IT WAS THE RAIN", "The ship carried the first raincloud back to Earth.", "ship", "THE SEA RETURNS", "payoff"),
              ]),
        story("doorclock", "The Door That Opened Tomorrow | Original Microfiction",
              "What happens if a door only opens one day ahead?",
              "A door appears inside an empty station; every opening shows the next day, until there are no tomorrows left.",
              [
                  ("A DOOR TO TOMORROW", "At midnight, a new door appeared in the old station.", "door", "00:00", "reveal"),
                  ("ONE DAY AHEAD", "Through it, Lena saw the same room twenty-four hours later.", "door", "TOMORROW", "mechanism"),
                  ("THE CLOCK STOPPED", "On the seventh night, the room beyond was completely dark.", "signal", "NO SIGNAL", "twist"),
                  ("SHE LEFT IT OPEN", "So she held the door open. And the next morning finally arrived.", "door", "DAWN", "payoff"),
              ]),
        story("robotgarden", "The Robot Who Grew a Forest | Original Microfiction",
              "Can one robot bring a dead landscape back to life?",
              "A damaged gardener robot keeps a tiny promise until its single seed grows into a forest.",
              [
                  ("ONE SEED LEFT", "A forgotten robot found the last seed in a silent city.", "robot", "THE LAST SEED", "reveal"),
                  ("ONE DROP A DAY", "Every day, it carried one drop of water across the ruins.", "robot", "DAY AFTER DAY", "build"),
                  ("IT FINALLY GREW", "The seed became a tree. Then the tree made another seed.", "forest", "FIRST GREEN", "mechanism"),
                  ("THE CITY TURNED GREEN", "When the robot fell silent, its forest had just begun to sing.", "forest", "NEW BEGINNING", "payoff"),
              ]),
        story("spacesong", "The Song From the Empty Ship | Original Microfiction",
              "Why is an abandoned ship still singing?",
              "A distant rescue crew follows a melody through space and discovers an unexpected passenger.",
              [
                  ("A SHIP WAS SINGING", "An empty spaceship broadcast the same lullaby every night.", "ship", "UNKNOWN VESSEL", "reveal"),
                  ("NO ONE ABOARD", "The rescuers searched every room. Not one person was there.", "ship", "EMPTY", "build"),
                  ("A TINY HEARTBEAT", "Behind the engine, they found a sleeping child in a rescue pod.", "signal", "LIFE DETECTED", "twist"),
                  ("THE SHIP KEPT ITS PROMISE", "The lullaby had been a promise to keep the child safe.", "ship", "HOME FOUND", "payoff"),
              ]),
        story("marsfootprints", "The Footprints That Were Not There | Original Microfiction",
              "Who is walking beside the first explorer on Mars?",
              "A rover finds a second trail of footprints beside its own tracks, and a message from home.",
              [
                  ("TWO SETS OF TRACKS", "The rover was alone on Mars. Then its camera found footprints beside it.", "planet", "MARS / DAY 41", "reveal"),
                  ("NO ONE WAS THERE", "The next photo showed only red sand, and a tiny blinking light.", "robot", "NO CONTACT", "build"),
                  ("A MESSAGE FROM HOME", "The light was an old beacon sent years before the rover arrived.", "signal", "EARTH SIGNAL", "twist"),
                  ("NOT ALONE AFTER ALL", "It had waited all that time just to say, Welcome to Mars.", "planet", "WELCOME", "payoff"),
              ]),
        story("lasttree", "The Library Beneath the Last Tree | Original Microfiction",
              "What secret does the oldest tree protect?",
              "In a world of metal towers, a child finds an ancient living library grown beneath the last tree.",
              [
                  ("THE LAST TREE", "In a city of steel, one tree was older than every building.", "forest", "ONE LEFT", "reveal"),
                  ("A DOOR IN ITS ROOTS", "A child found a small door hidden under the roots.", "door", "DO NOT DISTURB", "build"),
                  ("THE BOOKS WERE ALIVE", "Inside, every book was made of living leaves.", "forest", "A LIVING LIBRARY", "twist"),
                  ("THE FOREST RETURNED", "When she read the first page aloud, seeds began to fall.", "forest", "CHAPTER ONE", "payoff"),
              ]),
        story("moonpost", "The Post Office on the Moon | Original Microfiction",
              "Who delivers letters to an empty moon?",
              "A lunar courier discovers that the letters she delivers are messages from future explorers.",
              [
                  ("MAIL FOR NOBODY", "Every morning, Mara carried letters to an abandoned lunar outpost.", "planet", "LUNAR MAIL", "reveal"),
                  ("A NEW ENVELOPE", "One envelope held a drawing of a garden that did not exist.", "door", "NO SENDER", "build"),
                  ("THE FIRST SEED", "Behind the outpost, she found a greenhouse with one tiny green shoot.", "forest", "FIRST LIFE", "twist"),
                  ("DELIVERY CONFIRMED", "Years later, the first settlers wrote back from a garden beneath the stars.", "signal", "REPLY RECEIVED", "payoff"),
              ]),
        story("rainmuseum", "The Museum of Lost Rain | Original Microfiction",
              "Can a museum return the world's missing rain?",
              "A child restores a forgotten weather machine by listening to a recording of the first storm.",
              [
                  ("THE LAST RAINDROP", "The museum kept the world's last raindrop inside a glass jar.", "planet", "NO RAIN", "reveal"),
                  ("AN OLD RECORDING", "Niko found a recording of thunder hidden beneath the display.", "signal", "ARCHIVE FOUND", "build"),
                  ("THE MACHINE AWOKE", "When he played it, the silent weather machine began to hum.", "robot", "SYSTEM ONLINE", "twist"),
                  ("RAIN ON THE ROOF", "Outside, the city heard real thunder for the first time in a century.", "forest", "FIRST STORM", "payoff"),
              ]),
        story("clockworkbridge", "The Bridge That Remembered | Original Microfiction",
              "Why does an abandoned bridge light up every night?",
              "A repair robot follows glowing footsteps across a bridge and reunites a town.",
              [
                  ("THE EMPTY BRIDGE", "Every night, lights crossed the broken bridge though nobody was there.", "signal", "MIDNIGHT", "reveal"),
                  ("FOLLOW THE LIGHTS", "A small repair robot traced the lights to a missing metal joint.", "robot", "FAULT FOUND", "build"),
                  ("THE OLD PROMISE", "Its memory revealed two villages had once built the bridge together.", "door", "ARCHIVE", "twist"),
                  ("TWO SIDES MEET", "At sunrise, the repaired bridge carried neighbors toward each other again.", "ship", "RECONNECTED", "payoff"),
              ]),
        story("starseed", "The Seed That Fell From Saturn | Original Microfiction",
              "What grows from a seed that falls through space?",
              "An astronaut plants a mysterious seed and discovers a beacon for lost travelers.",
              [
                  ("A SEED IN SPACE", "A silver seed drifted past the station near Saturn.", "planet", "UNKNOWN OBJECT", "reveal"),
                  ("A LITTLE GARDEN", "Iris planted it in the station's smallest pot.", "forest", "DAY ONE", "build"),
                  ("THE LEAVES GLOWED", "Each new leaf pointed toward a ship lost beyond the rings.", "signal", "SIGNAL FOUND", "twist"),
                  ("A WAY HOME", "Following the glowing leaves, the lost crew finally found their way home.", "ship", "RESCUE", "payoff"),
              ]),
    ]
