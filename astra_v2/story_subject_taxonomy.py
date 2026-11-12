"""Pure subject-label taxonomy shared by writing validation and visual rendering.

Keep this module free of renderer/image dependencies so story validation can run
in lightweight proposal workers without Pillow or video packages.
"""

SUBJECTS = (
    ("fox", r"\bfox\b|\bfoxes\b"),
    ("owl", r"\bowl\b|\bowls\b"),
    ("duck", r"\bduck\b|\bgoose\b|\bgeese\b"),
    ("squirrel", r"\bsquirrel\b|\bchipmunk\b"),
    ("mouse", r"\bmouse\b|\bmice\b"),
    ("mole", r"\bmoles?\b"),
    ("otter", r"\botter\b"),
    ("beaver", r"\bbeavers?\b"),
    ("penguin", r"\bpenguins?\b"),
    ("heron", r"\bherons?\b"),
    ("crab", r"\bcrab\b"),
    ("firefly", r"\bfirefl\w*\b"),
    ("cat", r"\bcat\b|\bfeline\b|\bkitten\b"),
    ("dog", r"\bdog\b|\bpuppy\b|\bhound\b"),
    ("monkey", r"\bmonkey\b|\bape\b|\bbaboon\b"),
    ("bird", r"\bbird\b|\bparrot\b|\bsparrow\b|\bcrow\b|\bpigeon\b"),
    ("rabbit", r"\brabbit\b|\bbunny\b|\bhare\b"),
    ("book", r"\bbook\b|\blibrar\w*|\bpages\b|\bnewspaper\b"),
    ("ocean", r"\bocean\b|\bunderwater\b|\bfish\b|\bjellyfish\b|\bcoral\b"),
    ("clock", r"\bclock\b|\btimepiece\b|\bclocktower\b"),
    ("museum", r"\bmuseum\b|\bexhibit\b|\bartifact\b"),
    ("whale", r"\bwhale\b"),
    ("tree", r"\bforest\b|\btree\b|\bseed\b"),
    ("train", r"\btrain\b|\brailway\b"),
    ("moon", r"\bmoon\b|\blunar\b"),
    ("robot", r"\brobot\b|\bmachine\b"),
)
