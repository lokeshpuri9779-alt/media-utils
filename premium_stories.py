from __future__ import annotations

"""Curated, source-backed stories for RAYVAN's premium lane.

These are not filler. Each story is written around one visual payoff that can be
supported by public-domain/CC0 media and a short, natural narration.
"""

def catalog():
    return [
        {
            "genre":"space","kind":"explainer","content_id":"moon-tidal-lock-v1",
            "premium_story":True,"production_ready":True,
            "hook":"THE MOON ROTATES",
            "question":"Why do we always see almost the same face of the Moon?",
            "answer":"The Moon spins once in the same time it takes to orbit Earth. That synchronous rotation keeps the same side facing us.",
            "title":"Why We Always See the Same Side of the Moon",
            "voice_speed":1.04,
            "source":"https://science.nasa.gov/moon/tidal-locking/",
            "keywords":["moon","tidal locking","space"],
            "story_beats":[
                {"headline":"THE MOON ROTATES","speech":"The Moon rotates. You just cannot see the spin from Earth.","visual":"media","label":"","sub":"","story_beat":"reveal","media_query":"Moon nearside LRO","media_file":"File:Moon nearside LRO 5000.jpg","media_fit":"contain","media_motion":"push"},
                {"headline":"WATCH THE MARKER","speech":"Watch the marker. One spin takes the same time as one orbit.","visual":"tidal_lock","label":"","sub":"","story_beat":"mechanism"},
                {"headline":"NEAR SIDE / FAR SIDE","speech":"That is why nearly the same side always faces us.","visual":"media","label":"","sub":"","story_beat":"evidence","media_query":"Near and far side Moon","media_file":"File:Near and far side of the Moon.jpg","media_fit":"wide","media_motion":"still"},
                {"headline":"THE SIDE EARTH CAN'T SEE","speech":"This is the far side. Spacecraft can see it. Earth cannot directly.","visual":"media","label":"","sub":"","story_beat":"payoff","media_query":"Moon farside LRO","media_file":"File:Moon farside LRO 5000.jpg","media_fit":"contain","media_motion":"push"},
            ],
        },
        {
            "genre":"space","kind":"explainer","content_id":"mercury-solar-day-v1",
            "premium_story":True,"production_ready":False,
            "hook":"A DAY LASTS TWO YEARS",
            "question":"How can one day on Mercury outlast two Mercury years?",
            "answer":"Mercury orbits the Sun every 88 Earth days, but one full sunrise-to-sunrise solar day lasts 176 Earth days.",
            "title":"On Mercury, One Day Lasts Two Years",
            "source":"https://science.nasa.gov/mercury/facts/",
            "keywords":["mercury","planet","space"],
            "story_beats":[
                {"headline":"ONE DAY = TWO YEARS","speech":"On Mercury, sunrise to sunrise takes one hundred seventy-six Earth days.","visual":"media","label":"176 DAYS","sub":"ONE SOLAR DAY","story_beat":"reveal","media_query":"Mercury MESSENGER NASA planet public domain"},
                {"headline":"BUT A YEAR IS ONLY 88","speech":"Mercury races around the Sun in just eighty-eight Earth days.","visual":"media","label":"88 DAYS","sub":"ONE ORBIT","story_beat":"contrast","media_query":"Mercury orbit Sun NASA diagram public domain"},
                {"headline":"THE WEIRD PART","speech":"Its slow spin and fast, stretched orbit make the Sun behave strangely in Mercury's sky.","visual":"media","label":"SLOW SPIN","sub":"FAST ORBIT","story_beat":"mechanism","media_query":"Mercury rotation orbit MESSENGER NASA public domain"},
                {"headline":"SO YES","speech":"One full Mercury day lasts a little more than two Mercury years.","visual":"media","label":"176 > 88 × 2","sub":"DAY / YEAR","story_beat":"payoff","media_query":"Mercury NASA MESSENGER full disk public domain"},
            ],
        },
        {
            "genre":"space","kind":"explainer","content_id":"iss-sixteen-sunrises-v1",
            "premium_story":True,"production_ready":True,
            "hook":"16 SUNRISES A DAY",
            "question":"How can astronauts see sixteen sunrises in one day?",
            "answer":"The International Space Station circles Earth about every 90 minutes, making about 16 orbits in 24 hours.",
            "title":"Why Astronauts See About 16 Sunrises a Day",
            "voice_speed":1.04,
            "source":"https://www.nasa.gov/international-space-station/space-station-facts-and-figures/",
            "keywords":["iss","space station","earth","space"],
            "story_beats":[
                {"headline":"16 SUNRISES A DAY","speech":"Astronauts can see about sixteen sunrises in one Earth day.","visual":"media","label":"","sub":"","story_beat":"reveal","media_query":"ISS sunrise from orbit","media_file":"File:ISS-43 Sunrise from orbit.jpg","media_fit":"wide","media_motion":"push"},
                {"headline":"ONE ORBIT: ABOUT 90 MINUTES","speech":"The station circles Earth roughly every ninety minutes.","visual":"iss_orbit","label":"","sub":"","story_beat":"mechanism"},
                {"headline":"DAYLIGHT COMES BACK FAST","speech":"That means day and night keep repeating around the crew.","visual":"media","label":"","sub":"","story_beat":"evidence","media_query":"ISS sunrise solar arrays","media_file":"File:ISS. Sunrise Through the Solar Arrays.jpg","media_fit":"wide","media_motion":"push"},
                {"headline":"AROUND EARTH. AGAIN.","speech":"Sixteen trips around Earth means roughly sixteen sunrises and sunsets.","visual":"media","label":"","sub":"","story_beat":"payoff","media_query":"ISS sunrise Earth horizon","media_file":"File:ISS-64 Sunrise through Earth's horizon.jpg","media_fit":"wide","media_motion":"push"},
            ],
        },
        {
            "genre":"space","kind":"explainer","content_id":"mars-blue-sunset-v1",
            "premium_story":True,"production_ready":True,
            "hook":"MARS HAS BLUE SUNSETS",
            "question":"Why can sunset near the Sun look blue on the Red Planet?",
            "answer":"Fine Martian dust lets blue light stay concentrated closer to the Sun while other colors spread more broadly through the sky.",
            "title":"Why Sunsets on Mars Can Look Blue",
            "source":"https://science.nasa.gov/solar-system/planets/mars/what-does-a-sunrise-sunset-look-like-on-mars/",
            "keywords":["mars","sunset","space"],
            "story_beats":[
                {"headline":"THE RED PLANET TURNS BLUE","speech":"Near sunset on Mars, the sky around the Sun can glow blue.","visual":"media","label":"BLUE","sub":"AT SUNSET","story_beat":"reveal","media_query":"Mars blue sunset Curiosity NASA public domain"},
                {"headline":"IT'S THE DUST","speech":"Fine dust in the Martian atmosphere scatters light differently from Earth's air.","visual":"media","label":"FINE DUST","sub":"CHANGES THE LIGHT","story_beat":"mechanism","media_query":"Mars atmosphere dust NASA rover public domain"},
                {"headline":"BLUE STAYS NEAR THE SUN","speech":"Blue light remains concentrated closer to the Sun while red and yellow spread across more of the sky.","visual":"media","label":"BLUE / RED","sub":"DIFFERENT SCATTERING","story_beat":"evidence","media_query":"Mars sunset Curiosity Gale Crater NASA public domain"},
                {"headline":"MARS FLIPS THE SCRIPT","speech":"Red landscape. Blue sunset. The atmosphere makes both possible.","visual":"media","label":"RED → BLUE","sub":"ONE PLANET","story_beat":"payoff","media_query":"Mars sunset Perseverance NASA public domain"},
            ],
        },
        {
            "genre":"space","kind":"explainer","content_id":"saturn-density-v1",
            "premium_story":True,"production_ready":False,
            "hook":"SATURN COULD FLOAT",
            "question":"Could Saturn really float in water?",
            "answer":"Saturn is the only planet with an average density lower than water. In an impossibly large enough ocean, that means it would float.",
            "title":"Saturn Is Less Dense Than Water",
            "source":"https://science.nasa.gov/saturn/facts/",
            "keywords":["saturn","density","space"],
            "story_beats":[
                {"headline":"SATURN COULD FLOAT","speech":"Saturn's average density is lower than water.","visual":"media","label":"LESS DENSE","sub":"THAN WATER","story_beat":"reveal","media_query":"Saturn Cassini NASA full planet public domain"},
                {"headline":"THAT'S UNIQUE","speech":"NASA says Saturn is the only planet in our solar system with an average density below water.","visual":"media","label":"SATURN < WATER","sub":"AVERAGE DENSITY","story_beat":"evidence","media_query":"Saturn rings Cassini NASA public domain"},
                {"headline":"BUT THERE'S A CATCH","speech":"You would need an absurdly enormous body of water. There is no planetary bathtub.","visual":"media","label":"HYPOTHETICAL","sub":"VERY, VERY LARGE","story_beat":"contrast","media_query":"Saturn Earth size comparison NASA public domain"},
                {"headline":"THE POINT IS DENSITY","speech":"The floating idea is a scale model for remembering how unusually low Saturn's average density is.","visual":"media","label":"MEMORABLE","sub":"BECAUSE IT'S TRUE","story_beat":"payoff","media_query":"Saturn Cassini rings NASA public domain"},
            ],
        },
    ]
