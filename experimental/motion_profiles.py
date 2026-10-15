"""Compatibility exports for the optimized Pillow experiment.

The canonical motion implementation now belongs to the single ASTRA Studio
renderer and is shared by solo, duo, and ensemble story compositions.
"""
from astra_v2.story_motion import MotionState, smoothstep, evaluate

__all__ = ["MotionState", "smoothstep", "evaluate"]
