"""Reviewed causal story candidates; all existing publication gates remain active."""
PLOTS = [
    ("stoat-shadow-clock", "The Stoat and the Shadow Clock", "desert navigation", [
        ("THE SIGNAL FLAG FELL", "A stoat delivering medicine across the desert found the caravan signal pole broken at noon.", "signal", "NO SIGNAL"),
        ("THE SAND HID THE TRACKS", "A sudden gust buried the wheel marks and left the stoat searching for a safe route.", "forest", "TRACKS LOST"),
        ("THE SHADOW POINTED HOME", "She planted her walking stick beside an old sundial and matched its shadow with the caravan trail.", "clock", "SHADOW CLUE"),
        ("THE MEDICINE ARRIVED", "She reached the caravan before sunset and helped the travelers build a stronger signal pole.", "signal", "DELIVERY MADE"),
    ]),
    ("tapir-mangrove-bell", "The Tapir and the Mangrove Bell", "coastal rescue", [
        ("THE TIDE CUT THE PATH", "A tapir found the island school cut off when a high tide flooded the mangrove walkway.", "ship", "PATH UNDERWATER"),
        ("THE BOAT COULD NOT PASS", "He guided a skiff toward the school but a fallen branch blocked the usual channel.", "forest", "CHANNEL BLOCKED"),
        ("THE BELL MARKED DEEP WATER", "He heard the harbor bell through an open tidal passage and marked the channel with floating coconuts.", "signal", "SOUND THE WAY"),
        ("THE CHILDREN CROSSED", "The school boat followed his coconut markers safely and the villagers later cleared the blocked channel.", "ship", "SAFE CROSSING"),
    ]),
    ("alpaca-museum-whisper", "The Alpaca and the Whispering Museum", "mechanical mystery", [
        ("THE PAINTINGS HUMMED", "An alpaca night guard heard a strange humming behind the museum portraits after the lights went out.", "book", "STRANGE HUM"),
        ("THE WALL WAS SOLID", "She searched the gallery but found no doorway or hidden visitor behind any of the frames.", "door", "NO FOOTPRINTS"),
        ("THE VENT CARRIED MUSIC", "She held a paper ribbon near the wall and saw it flutter beside an old ventilation grille.", "robot", "AIRFLOW CLUE"),
        ("THE RECITAL WAS SAVED", "She traced the humming to a forgotten rehearsal radio and restored the gallery quiet before opening.", "door", "MYSTERY SOLVED"),
    ]),
    ("pangolin-river-lanterns", "The Pangolin and the River Lanterns", "nighttime engineering", [
        ("THE BRIDGE LIGHTS WENT DARK", "A pangolin discovered the river bridge lanterns had gone out before the night market opened.", "signal", "DARK BRIDGE"),
        ("THE WICKS WOULD NOT STAY LIT", "He replaced every lantern wick but river spray extinguished the little flames again and again.", "ship", "SPRAY TROUBLE"),
        ("THE SHELLS SHIELDED FLAMES", "He noticed empty river shells shielding a fisherman's stove and fitted protective covers around the lanterns.", "forest", "SHELL SHIELDS"),
        ("THE MARKET FOUND ITS WAY", "The protected lanterns illuminated the crossing and the traders opened the evening market safely.", "door", "LIGHTS RETURN"),
    ]),
]
