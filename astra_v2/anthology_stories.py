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
