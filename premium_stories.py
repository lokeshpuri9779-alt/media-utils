from __future__ import annotations

"""Curated, source-backed stories for RAYVAN's premium lane.

These are not filler. Each story is written around one visual payoff that can be
supported by public-domain/CC0 media and a short, natural narration.
"""

def catalog():
    return [
        {
            "genre":"space","kind":"explainer","content_id":"moon-tidal-lock-v1",
            "premium_story":True,
            "hook":"THE MOON DOES ROTATE",
            "question":"Why do we always see almost the same face of the Moon?",
            "answer":"The Moon spins once in the same time it takes to orbit Earth. That synchronous rotation keeps the same side facing us.",
            "title":"The Moon Is Rotating — You Just Can't See It",
            "source":"https://science.nasa.gov/moon/tidal-locking/",
            "keywords":["moon","tidal locking","space"],
            "story_beats":[
                {"headline":"THE MOON DOES ROTATE","speech":"The Moon is rotating. It just hides the motion extremely well.","visual":"media","label":"ROTATING","sub":"NOT FROZEN","story_beat":"reveal","media_query":"Moon near side NASA LRO public domain"},
                {"headline":"ONE SPIN. ONE ORBIT.","speech":"It turns once in the same time it takes to orbit Earth.","visual":"media","label":"1 = 1","sub":"SPIN / ORBIT","story_beat":"mechanism","media_query":"Moon Earth orbit tidal locking NASA diagram public domain"},
                {"headline":"THAT LOCKS THE VIEW","speech":"So the same lunar hemisphere keeps facing Earth as the Moon travels around us.","visual":"media","label":"SAME FACE","sub":"SYNCHRONOUS ROTATION","story_beat":"evidence","media_query":"Moon near side far side NASA public domain"},
                {"headline":"THE FAR SIDE IS REAL","speech":"Spacecraft can see it. From Earth, tidal locking keeps it turned away.","visual":"media","label":"FAR SIDE","sub":"SEEN FROM SPACE","story_beat":"payoff","media_query":"Moon far side NASA LRO public domain"},
            ],
        },
        {
            "genre":"space","kind":"explainer","content_id":"mercury-solar-day-v1",
            "premium_story":True,
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
            "premium_story":True,
            "hook":"16 SUNRISES A DAY",
            "question":"How can astronauts see sixteen sunrises in one day?",
            "answer":"The International Space Station circles Earth about every 90 minutes, making about 16 orbits in 24 hours.",
            "title":"Astronauts Can See 16 Sunrises Every Day",
            "source":"https://www.nasa.gov/international-space-station/space-station-facts-and-figures/",
            "keywords":["iss","space station","earth","space"],
            "story_beats":[
                {"headline":"16 SUNRISES. EVERY DAY.","speech":"Astronauts on the space station can see about sixteen sunrises and sunsets in twenty-four hours.","visual":"media","label":"16×","sub":"SUNRISE / SUNSET","story_beat":"reveal","media_query":"International Space Station sunrise Earth NASA public domain"},
                {"headline":"HERE'S WHY","speech":"The station circles Earth roughly once every ninety minutes.","visual":"media","label":"~90 MIN","sub":"ONE ORBIT","story_beat":"mechanism","media_query":"International Space Station orbit Earth NASA public domain"},
                {"headline":"IT IS MOVING FAST","speech":"NASA says it travels about seventeen thousand five hundred miles per hour.","visual":"media","label":"17,500 MPH","sub":"AROUND EARTH","story_beat":"evidence","media_query":"International Space Station Earth NASA public domain"},
                {"headline":"DAY. NIGHT. REPEAT.","speech":"At that speed, a sunrise can return before a movie is over.","visual":"media","label":"16 ORBITS","sub":"IN 24 HOURS","story_beat":"payoff","media_query":"ISS cupola Earth sunrise NASA public domain"},
            ],
        },
        {
            "genre":"space","kind":"explainer","content_id":"mars-blue-sunset-v1",
            "premium_story":True,
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
            "premium_story":True,
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
