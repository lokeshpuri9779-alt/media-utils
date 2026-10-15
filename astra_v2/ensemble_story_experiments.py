"""Experimental ensemble fiction for isolated Studio preview, NOT publication.

These pilots have individually written causal developments, differing cast
sizes, conflicts, false explanations, sacrifices and reversals. They are not
2,000 actor-swapped templates. Keep experimental until human visual/story QA.
"""
import hashlib

PILOTS = [
    {
        "key":"missing-tomorrow",
        "title":"The Trial of Tomorrow",
        "genre_name":"time mystery",
        "cast":("owl","fox","rabbit","cat","mouse"),
        "logline":"A fox is accused of stealing tomorrow; the evidence is an alarm that hasn't rung yet.",
        "beats":[
            ("TOMORROW WAS STOLEN","The owl put the fox on trial. The town clock showed tomorrow, and the rabbit swore it had rung early.","confrontation",{"owl":"point","fox":"hide","rabbit":"wave","cat":"look","mouse":"look"}),
            ("A WITNESS LIED","The cat exposed a fresh screwdriver mark behind the clock. Suddenly the rabbit stopped speaking.","clue",{"cat":"repair","rabbit":"hide","owl":"look","mouse":"point"}),
            ("THE CLOCK WAS A WARNING","The mouse opened a hidden book: tomorrow's alarm was designed to warn of a dam breaking tonight.","reveal",{"mouse":"open","fox":"point","owl":"look","cat":"look"}),
            ("THE ACCUSED TOOK CONTROL","The fox pushed the heavy bell while the others pulled its rope. The warning rang across the flooded valley.","action",{"fox":"push","rabbit":"pull","owl":"wave","cat":"run","mouse":"point"}),
            ("THE VERDICT CHANGED","The owl cleared the fox. The rabbit confessed she had shifted the clock to force everyone to listen before it was too late.","reaction",{"owl":"clap","rabbit":"look","fox":"look","mouse":"wave","cat":"clap"}),
        ],
    },
    {
        "key":"memory-library",
        "title":"The Library That Loaned Memories",
        "genre_name":"emotional fantasy",
        "cast":("owl","fox","rabbit","otter","squirrel","mouse"),
        "logline":"Six friends recover a lost hour, but restoring it means one must surrender their fondest memory.",
        "beats":[
            ("NOBODY REMEMBERED NOON","At the library, six friends found a book recording a missing hour. Each remembered a different ending to the same day.","crowd",{"owl":"look","fox":"point","rabbit":"look","otter":"open","squirrel":"wave","mouse":"hide"}),
            ("A PAGE WAS STILL WARM","The squirrel opened a page bearing the mouse's handwriting. It described a fire that nobody remembered escaping.","clue",{"squirrel":"open","mouse":"hide","owl":"look"}),
            ("THE MOUSE HAD SAVED THEM","The mouse confessed: he traded his happiest memory to rewind the hour before the fire. Now even his sister's face looked unfamiliar.","confrontation",{"mouse":"look","rabbit":"hug","otter":"point","fox":"hide"}),
            ("THE BOOK DEMANDED ANOTHER","The book offered everyone their memories back if someone surrendered a new one. The fox reached forward, but the owl stopped him.","reaction",{"fox":"pick","owl":"point","rabbit":"wave","mouse":"look"}),
            ("THEY CHOSE AN UNWRITTEN PAGE","Instead of paying again, each friend described a memory aloud. The mouse couldn't recover yesterday, but they could make a new story together.","resolution",{"owl":"open","fox":"hug","rabbit":"clap","otter":"clap","squirrel":"wave","mouse":"look"}),
        ],
    },
    {
        "key":"last-shadow-auction",
        "title":"The Auction of the Last Shadow",
        "genre_name":"comic mystery",
        "cast":("cat","fox","owl","dog"),
        "logline":"A town auctions shadows to keep its streetlights on, until the auctioneer's shadow exposes the trick.",
        "beats":[
            ("SOLD TO THE HIGHEST BID","The cat raised a hand to buy back the dog's shadow. Nobody at the auction questioned why shadows came in boxes.","crowd",{"cat":"wave","dog":"hide","fox":"look","owl":"point"}),
            ("THE SHADOW DIDN'T FIT","The fox opened the box. Its shadow moved the wrong way, even though the afternoon sun had not changed.","clue",{"fox":"open","cat":"look","owl":"point","dog":"hide"}),
            ("THE AUCTIONEER CAST TWO","The owl pointed toward the auctioneer's feet. One shadow belonged to him; the other was the town's missing clock tower.","reaction",{"owl":"point","fox":"look","dog":"jump"}),
            ("THE LIGHTS WERE THE PRIZE","The cat turned off the lamps. Every stolen shadow returned at once, revealing the clock tower's hidden doorway.","action",{"cat":"push","fox":"run","dog":"point","owl":"wave"}),
            ("THE WINNING BID WAS SILENCE","The dog refused to buy a thing. Without shadows to sell, the auctioneer finally admitted the lamps were powered by a stolen mirror.","resolution",{"dog":"clap","cat":"look","fox":"wave","owl":"clap"}),
        ],
    },
    {
        "key":"silent-orchestra",
        "title":"The Orchestra That Played a Warning",
        "genre_name":"suspense adventure",
        "cast":("fox","rabbit","cat","dog","owl","mouse","otter"),
        "logline":"Seven musicians receive a score with missing notes and discover the pauses mark a collapsing bridge.",
        "beats":[
            ("THE MUSIC HAD HOLES","Seven musicians rehearsed beside the river. The mouse noticed the conductor's new score had identical gaps in every page.","crowd",{"fox":"dance","rabbit":"look","cat":"clap","dog":"look","owl":"point","mouse":"open","otter":"wave"}),
            ("EVERY SILENCE HAD A NUMBER","The owl counted the missing beats. The numbers matched the iron bolts on the bridge outside the hall.","clue",{"owl":"point","mouse":"look","fox":"hide","cat":"point"}),
            ("THE CONDUCTOR HID A CRACK","The dog found a broken bolt beneath the bridge. The conductor hadn't written music; she was trying to send a warning unseen.","confrontation",{"dog":"point","rabbit":"wave","otter":"look","owl":"look"}),
            ("THEY STOPPED PLAYING","The fox cut the concert short. In the sudden silence, the audience heard the bridge snapping and hurried away.","action",{"fox":"point","cat":"run","rabbit":"run","dog":"wave","owl":"wave","mouse":"hide","otter":"run"}),
            ("THE FINAL NOTE WAS SAFE","The bridge fell into the empty riverbank. The musicians rebuilt the stage farther inland and performed the missing notes at last.","resolution",{"fox":"dance","rabbit":"clap","cat":"clap","dog":"clap","owl":"wave","mouse":"dance","otter":"dance"}),
        ],
    },
    {
        "key":"bridge-that-lied",
        "title":"The Bridge That Wouldn't Collapse",
        "genre_name":"high-stakes ensemble",
        "cast":("fox","rabbit","cat","dog","owl","mouse","otter","squirrel"),
        "logline":"Eight rescuers face a bridge that defies gravity; dismantling it might destroy the only safe evacuation route.",
        "beats":[
            ("THE BRIDGE HUNG IN MID-AIR","Eight rescuers stared at a bridge with its center supports missing. The squirrel insisted it was safer than it looked.","crowd",{"fox":"look","rabbit":"wave","cat":"point","dog":"hide","owl":"look","mouse":"look","otter":"point","squirrel":"wave"}),
            ("THE ROPE LED UNDERGROUND","The mouse followed a taut rope into an old tunnel. Beneath the bridge, a hidden counterweight was holding everyone above the river.","clue",{"mouse":"run","owl":"point","otter":"look","dog":"look"}),
            ("THE COUNTERWEIGHT WAS MOVING","The otter spotted the water rising against the tunnel door. When it opened, the counterweight would fall and take the bridge with it.","confrontation",{"otter":"point","squirrel":"hide","fox":"wave","rabbit":"look"}),
            ("THEY CHOSE TO BREAK IT FIRST","The fox and dog pulled the evacuation bell. The cat and rabbit cleared the road while the others cut the empty bridge free.","action",{"fox":"pull","dog":"pull","cat":"run","rabbit":"run","owl":"wave","mouse":"point","otter":"push","squirrel":"hide"}),
            ("THE RIVER TOOK THE BRIDGE","The bridge fell without a passenger on it. A moment later, the counterweight tore through the tunnel as they had feared.","reveal",{"fox":"look","otter":"look","owl":"point","mouse":"hide"}),
            ("THE SAFEST CROSSING WAS A DETOUR","The squirrel led the eight rescuers through a dry hillside path nobody had used in years. They saved the village by abandoning the obvious road.","resolution",{"squirrel":"point","fox":"clap","rabbit":"wave","cat":"wave","dog":"clap","owl":"look","mouse":"clap","otter":"wave"}),
        ],
    },
    {
        "key":"impossible-photo",
        "title":"The Photograph of a Crime That Never Happened",
        "genre_name":"three-person thriller",
        "cast":("cat","owl","mouse"),
        "logline":"A photograph predicts a theft; preventing it turns the would-be thief into the only witness who can prove a rescue.",
        "beats":[
            ("THE PHOTO SHOWED TOMORROW","The cat discovered a photograph of herself stealing the museum's clock. The date printed below it was tomorrow.","clue",{"cat":"look","owl":"point","mouse":"hide"}),
            ("SHE REFUSED TO GO","The owl locked the museum door and hid the key. By evening, a storm left the mouse trapped inside.","confrontation",{"owl":"hide","cat":"point","mouse":"wave"}),
            ("THE CLOCK HELD THE EXIT","The cat broke the clock's glass to reach the emergency switch and free the mouse before the floodwater arrived.","action",{"cat":"repair","mouse":"run","owl":"point"}),
            ("THE PICTURE WAS A WARNING","The owl unfolded the photograph's corner. The supposed stolen clock was still mounted on the wall; the cat was reaching for the rescue switch.","reveal",{"owl":"open","cat":"look","mouse":"point"}),
            ("THEY KEPT THE BROKEN CLOCK","The museum displayed the damaged clock beside the photograph, with a new label: evidence of a rescue, not a crime.","resolution",{"cat":"clap","owl":"clap","mouse":"wave"}),
        ],
    },
]

STAGE_SEQUENCES = {
    "missing-tomorrow":("courtroom","courtroom","clocktower","river","courtroom"),
    "memory-library":("library","library","attic","library","library"),
    "last-shadow-auction":("auction","auction","street","street","auction"),
    "silent-orchestra":("concert_hall","concert_hall","bridge","concert_hall","bridge"),
    "bridge-that-lied":("bridge","tunnel","tunnel","bridge","river","hills"),
    "impossible-photo":("museum","museum","gallery","museum","museum"),
}

def catalog():
    stories=[]
    for plot in PILOTS:
        beats=[]
        stage_sequence=STAGE_SEQUENCES[plot["key"]]
        assert len(stage_sequence)==len(plot["beats"])
        for i,(headline,speech,style,acting) in enumerate(plot["beats"]):
            beats.append({
                "headline":headline,
                "speech":speech,
                "visual":"story",
                "label":plot["genre_name"].upper(),
                "sub":"ASTRA EXPERIMENT — NOT FOR PUBLICATION",
                "duration":2.4,
                "story_beat":("reveal","build","twist","payoff")[min(3,i*4//len(plot["beats"]))],
                "scene_style":style,
                "story_environment":stage_sequence[i],
                "acting_notes":acting,
                "story_cast":plot["cast"],
                "experimental_ensemble":True,
            })
        stories.append({
            "genre":"fiction","kind":"experimental_ensemble_story",
            "production_ready":False,"experimental_ensemble":True,
            "content_id":"astra-ensemble-"+hashlib.sha256(plot["key"].encode()).hexdigest()[:16],
            "title":plot["title"],"story_cast":plot["cast"],
            "hook":beats[0]["headline"],
            "question":plot["logline"],"answer":beats[-1]["speech"],
            "source":"","keywords":["ensemble animated fiction",plot["genre_name"]],
            "story_beats":beats,
        })
    return stories
