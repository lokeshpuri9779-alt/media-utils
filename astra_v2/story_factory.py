"""Bounded, resumable, review-only story factory. No publishing permissions."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from astra_v2.story_expansion_2000 import MECHANISMS as BASE_MECHANISMS, ANIMAL_PAIRS, SETTINGS
from astra_v2.story_factory_premises import NEW_MECHANISMS
MECHANISMS = BASE_MECHANISMS + NEW_MECHANISMS

TARGET = 196000
CONTEXTS = (
    ("before sunrise", "the first delivery of the day"),
    ("before the evening market", "the waiting traders"),
    ("as a storm approached", "the shelter volunteers"),
    ("before the school fair", "the arriving families"),
    ("during a power outage", "the community helpers"),
    ("before the final ferry", "the stranded travelers"),
    ("while the town prepared a parade", "the festival organizers"),
    ("after an unexpected downpour", "the neighborhood gardeners"),
    ("as the mountain mist thickened", "the rescue volunteers"),
    ("before the library opened", "the visiting readers"),
    ("during a sudden cold snap", "the local caretakers"),
    ("before the village meeting", "the assembled neighbors"),
    ("while a bridge was closed", "the waiting commuters"),
    ("after a strong windstorm", "the cleanup crew"),
    ("before the harvest celebration", "the farm workers"),
    ("while the clock tower was repaired", "the town engineers"),
    ("during the spring festival", "the performers"),
    ("before the last train arrived", "the station helpers"),
    ("after the river rose", "the river patrol"),
    ("before the museum tour", "the volunteer guides"),
    ("as the garden lights dimmed", "the evening visitors"),
    ("before the children's recital", "the music teachers"),
)
# Capacity is derived from authored source premises and variation dimensions.
# Candidate slots are not independently original plots.
CAPACITY = len(MECHANISMS)*len(ANIMAL_PAIRS)*len(SETTINGS)*len(CONTEXTS)*3
assert CAPACITY >= TARGET

def candidate_at(index):
    if not 0 <= index < TARGET:
        raise IndexError(index)
    n = index
    mechanism_index = n % len(MECHANISMS); n //= len(MECHANISMS)
    role = n % 3; n //= 3
    context = CONTEXTS[n % len(CONTEXTS)]; n //= len(CONTEXTS)
    setting = SETTINGS[n % len(SETTINGS)]; n //= len(SETTINGS)
    a,b = ANIMAL_PAIRS[n % len(ANIMAL_PAIRS)]; n //= len(ANIMAL_PAIRS)
    key,title,problem,setback,clue,resolution = MECHANISMS[mechanism_index]
    lead,partner = ((a,b),(b,a),(a,b))[role]
    place = "the " + setting
    deadline,audience = context
    beats = [
      f"At {place}, {lead} and {partner} discovered {problem} {deadline}, leaving {audience} waiting.",
      f"{lead.capitalize()} attempted an immediate fix, but {setback}; {partner} stopped the attempt before the situation worsened.",
      f"{partner.capitalize()} examined the evidence and realized {clue}; together they revised their plan rather than repeating the mistake.",
      f"With {audience} watching, they {resolution}, then explained the clue so their neighbors could prevent the problem next time."
    ]
    if role == 2:
        beats[1] = f"{partner.capitalize()} tried to isolate the problem first, but {setback}; {lead} stopped the attempt before further damage."
        beats[2] = f"{lead.capitalize()} compared the failed attempt with the evidence and realized {clue}; they planned a safer joint response."
    identity=f"factory-v1:{index}:{key}:{a}:{b}:{setting}:{context[0]}:{role}"
    plot_signature = hashlib.sha256(key.encode()).hexdigest()[:16]
    return {"plot_signature":plot_signature,"candidate_id":hashlib.sha256(identity.encode()).hexdigest()[:24],
            "slot":index,"premise_key":key,"title":title,
            "setting":setting,"context":context[0],"characters":[a,b],
            "story_beats":beats,"kind":"unreviewed_causal_draft",
            "production_ready":False,"editorial_review_required":True,
            "generation_method":"deterministic_composition",
            "independent_plot_claim":False}

def screen_candidate(candidate, previously_seen=()):
    """Conservative review; never authorizes publication."""
    reasons = []
    beats = candidate["story_beats"]
    if len(beats) != 4 or any(len(beat.split()) < 12 for beat in beats):
        reasons.append("weak_causal_structure")
    if candidate["premise_key"] in previously_seen:
        reasons.append("repeated_underlying_plot_mechanism")
    return {"candidate_id": candidate["candidate_id"],
            "premise_key": candidate["premise_key"],
            "status": "needs_new_plot" if reasons else "awaiting_editorial_review",
            "issues": reasons, "production_ready": False}

def generate(state_path, output_path, batch_size=500):
    if not 1 <= batch_size <= 5000:
        raise ValueError("batch_size must be between 1 and 5000")
    state_file=Path(state_path)
    state=json.loads(state_file.read_text()) if state_file.exists() else {}
    cursor=int(state.get("next_slot",0))
    if not 0 <= cursor <= TARGET: raise ValueError("invalid cursor")
    end=min(cursor+batch_size,TARGET)
    rows=[candidate_at(i) for i in range(cursor,end)]
    seen=set(state.get("seen_premise_keys", []))
    # Prioritize newly authored mechanisms without resetting the persistent cursor.
    # Preserve the slot and derive a new identity to avoid recycling early IDs.
    unseen=[i for i, mechanism in enumerate(MECHANISMS)
            if mechanism[0] not in seen]
    for position, mechanism_index in enumerate(unseen[:len(rows)]):
        original=rows[position]
        replacement=candidate_at(mechanism_index)
        replacement["slot"]=original["slot"]
        replacement["candidate_id"]=hashlib.sha256(
            ("factory-priority-v1:" + str(original["slot"]) + ":" +
             replacement["premise_key"]).encode()).hexdigest()[:24]
        rows[position]=replacement
    review=[]
    accepted_plot_signatures=set(state.get("seen_plot_signatures", []))
    for row in rows:
        review.append(screen_candidate(row, seen))
        seen.add(row["premise_key"])
        accepted_plot_signatures.add(row["plot_signature"])
    out=Path(output_path); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w") as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False)+"\n")
    review_path=out.with_name("story_factory_review.jsonl")
    with review_path.open("w") as f:
        for row in review: f.write(json.dumps(row,ensure_ascii=False)+"\n")
    state_file.parent.mkdir(parents=True,exist_ok=True)
    state_file.write_text(json.dumps({"version":1,"next_slot":end,
        "target":TARGET,"last_batch":len(rows),"complete":end==TARGET,
        "seen_premise_keys":sorted(seen),
        "seen_plot_signatures":sorted(accepted_plot_signatures),
        "last_awaiting_review":sum(x["status"]=="awaiting_editorial_review" for x in review)},indent=2)+"\n")
    return len(rows)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--state",default="story_factory_state.json")
    parser.add_argument("--output",default="story_factory_candidates.jsonl")
    parser.add_argument("--batch-size",type=int,default=500)
    args=parser.parse_args()
    print("Generated review-only candidates:",generate(args.state,args.output,args.batch_size))
