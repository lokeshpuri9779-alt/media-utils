"""Offline Studio hot-path benchmark; measurements only, never a release shortcut."""
from __future__ import annotations
import json
import statistics
import time
from pathlib import Path
from PIL import Image
from astra_v2.pillow_duo_scene import draw_duo, _cached_actor_mentions, _cached_prop, _cached_mood
from astra_v2.pillow_scene_direction import _cached_scene_setting
from studio_renderer import background, font, _starfield_points

def benchmark():
    text="The fox and rabbit carry a gift box by the river."
    trials=1200
    uncached=time.perf_counter()
    for _ in range(trials):
        _cached_actor_mentions.cache_clear()
        _cached_actor_mentions(text.lower())
    cold_ms=(time.perf_counter()-uncached)*1000
    _cached_actor_mentions.cache_clear()
    _cached_actor_mentions(text.lower())
    warm=time.perf_counter()
    for _ in range(trials):
        _cached_actor_mentions(text.lower())
    warm_ms=(time.perf_counter()-warm)*1000

    # Real sequential frame rendering: includes background, actors and props.
    shot={"speech":text,"story_cast":("fox","rabbit"),
          "story_action":"carry","story_visual_seed":"optim-perf-episode"}
    samples=[]
    for i in range(20):
        frame=background("fiction",i%3)
        t0=time.perf_counter()
        draw_duo(frame,shot,i/30)
        samples.append((time.perf_counter()-t0)*1000)
    return {
        "measurements_not_a_publishing_quality_gate":True,
        "animal_text_scans":trials,
        "uncached_animal_lookup_ms":round(cold_ms,3),
        "cached_animal_lookup_ms":round(warm_ms,3),
        "observed_lookup_speedup":round(cold_ms/max(warm_ms,.00001),2),
        "pillow_duo_frame_ms_median":round(statistics.median(samples),3),
        "pillow_duo_frame_ms_max":round(max(samples),3),
        "font_cache":dict(hits=font.cache_info().hits,misses=font.cache_info().misses),
        "stars_cached":_starfield_points.cache_info().currsize,
        "scene_setting_cache":dict(hits=_cached_scene_setting.cache_info().hits,
                                   misses=_cached_scene_setting.cache_info().misses),
        "prop_cache":dict(hits=_cached_prop.cache_info().hits,
                          misses=_cached_prop.cache_info().misses),
        "mood_cache":dict(hits=_cached_mood.cache_info().hits,
                          misses=_cached_mood.cache_info().misses),
    }

if __name__=="__main__":
    data=benchmark()
    Path("preview").mkdir(exist_ok=True)
    Path("preview/studio-perf-report.json").write_text(json.dumps(data,indent=2))
    print("ASTRA_STUDIO_PERF="+json.dumps(data,sort_keys=True))
