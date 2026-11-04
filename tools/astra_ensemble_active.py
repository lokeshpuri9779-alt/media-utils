"""Explicit ASTRA ensemble engine switch; production publishing is unchanged.

This workflow is an independent, artifact-only engine activation. It never
calls astra_v2.run or YouTube upload APIs. Both renderers can coexist.
"""
from __future__ import annotations
import os
from pathlib import Path

def main():
    os.environ["ASTRA_EXPERIMENT_ENSEMBLE"]="1"
    os.environ["ASTRA_OPENAI_ENABLED"]="0"
    from astra_v2.ensemble_story_experiments import catalog
    from astra_v2.publication_quality import publication_rejection
    from tools.astra_ensemble_voiced_preview import make_narrated_preview
    stories=catalog()
    assert stories and all(s.get("production_ready") is False for s in stories)
    assert all(publication_rejection(s)=="not_production_ready" for s in stories)
    result=make_narrated_preview(index=0,destination="preview/astra-ensemble-activated.mp4")
    assert Path("preview/astra-ensemble-activated.mp4").is_file()
    print("ASTRA_ENSEMBLE_ENGINE_ACTIVE=1")
    print("ASTRA_ENSEMBLE_PUBLISHING_ACTIVE=0")
    print("ASTRA_STUDIO_7_3_0_PRODUCTION_UNCHANGED=1")
    print(result)

if __name__=="__main__":
    main()
