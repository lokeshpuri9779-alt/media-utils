"""Reusable 2-bone kinematic rig for ASTRA's authored 2D Mara performances.

Mara and her double share exactly the same proportions. These are actual
per-frame shoulder/elbow/wrist and hip/knee/ankle joint solutions, rather
than the previous single bar joining a shoulder to a hand. This is 2D inverse
kinematics, not 3D animation, human motion capture or neural video generation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from astra_errors import CreativeReject

# All joints are pixel-relative to the same stable character anchor.
SHOULDER_L=(-58,-40)
SHOULDER_R=(54,-40)
HIP_L=(-37,195)
HIP_R=(38,195)
UPPER_ARM=105.0
FOREARM=105.0
# Physically proportioned near-straight standing legs. The previous
# 91/154 pair forced huge side-bent knees ("frog squat") even at rest:
# the body anchor-to-ankle distance is only ~145 px.
THIGH=81.0
CALF=86.0
FRAME_RATE=30


def _smooth(a):
    x=max(0.0,min(1.0,a))
    return x*x*(3.0-2.0*x)


def ik_joint(origin, target, first, second, bend):
    """Return joint with fixed segment lengths, clamping unreachable targets.

    Bend direction is fixed per limb, avoiding the elbow/knee popping to the
    opposite side when an animation crosses an IK singularity.
    """
    if bend not in (-1,1):
        raise CreativeReject("IK bend must be signed")
    if not all(math.isfinite(float(v)) for v in (*origin,*target,first,second)):
        raise CreativeReject("IK parameters must be finite")
    if first<=0 or second<=0:
        raise CreativeReject("IK bone lengths must be positive")
    dx=float(target[0]-origin[0])
    dy=float(target[1]-origin[1])
    distance=math.hypot(dx,dy)
    if distance<1e-6:
        dx,dy=0.0,1.0
        distance=1.0
    # Keep a tiny epsilon away from full straightening for stable elbow bends.
    clamped=max(abs(first-second)+1.0,min(distance,first+second-0.5))
    ux,uy=dx/distance,dy/distance
    base=(first*first-second*second+clamped*clamped)/(2*clamped)
    rise=math.sqrt(max(0.0,first*first-base*base))
    return (origin[0]+base*ux+bend*rise*(-uy),
            origin[1]+base*uy+bend*rise*ux)


@dataclass(frozen=True)
class RigPose:
    left_elbow: tuple[float,float]
    right_elbow: tuple[float,float]
    left_hand: tuple[float,float]
    right_hand: tuple[float,float]
    left_knee: tuple[float,float]
    right_knee: tuple[float,float]
    left_ankle: tuple[float,float]
    right_ankle: tuple[float,float]
    torso_offset: float
    stride: float


def solve_mara_pose(t, *, reaching=False, running=False, carrying=False,
                    gesture="consider", action_progress=None):
    """Per-frame named action rig; all coordinates are character-local.

    Walk/run cycles use opposing strides. In nonrunning stories, posture
    transfers weight and the arms still form jointed poses. Reaches interpolate
    through story time as selected by the caller. Every action is continuous
    at 30 FPS and deterministic for the same parameters.
    """
    if not math.isfinite(float(t)) or t<0:
        raise CreativeReject("Rig time must be finite and nonnegative")
    if gesture not in ("consider","protect","open"):
        raise CreativeReject("Unsupported gesture for rig")
    if action_progress is None:
        progress=_smooth(t/1.15)
    else:
        if not math.isfinite(float(action_progress)):
            raise CreativeReject("Invalid authored story-action progress")
        progress=_smooth(float(action_progress))
    foot_cycle=math.sin(t*9.2) if running else math.sin(t*1.6)
    stride=(58 if running else 7)*foot_cycle
    lift=(25 if running else 2)*max(0.0,math.sin(t*9.2))
    torso_offset=math.sin(t*1.35)*5.5 + (9*math.sin(t*9.2) if running else 0)
    lh={
        "protect":(-20,50+8*math.sin(t*1.4)),
        "open":(-157,40-11*math.sin(t*1.1)),
        "consider":(-40,-42+7*math.sin(t*.8)),
    }[gesture]
    rh=(113+7*math.sin(t*1.3),155)
    if reaching:
        rh=(113+32*progress,155-193*progress)
    elif carrying:
        rh=(144,10+4*math.sin(t*1.5))
    if running:
        lh=(-146,51-stride*.40)
        rh=(137,55+stride*.40)
    la=(-55-stride,340-lift)
    ra=(56+stride,340-(25 if running else 2)*max(0.0,-math.sin(t*9.2)))
    return RigPose(
        left_elbow=ik_joint(SHOULDER_L,lh,UPPER_ARM,FOREARM,-1),
        right_elbow=ik_joint(SHOULDER_R,rh,UPPER_ARM,FOREARM,1),
        left_hand=lh,right_hand=rh,
        left_knee=ik_joint(HIP_L,la,THIGH,CALF,1),
        right_knee=ik_joint(HIP_R,ra,THIGH,CALF,-1),
        left_ankle=la,right_ankle=ra,
        torso_offset=torso_offset,
        stride=stride,
    )


def is_pose_continuous(first,second,max_jump=8.0):
    """Detect visible animation pops in 30 FPS adjacent joint samples."""
    points=("left_elbow","right_elbow","left_hand","right_hand",
            "left_knee","right_knee","left_ankle","right_ankle")
    for point in points:
        a=getattr(first,point)
        b=getattr(second,point)
        if math.hypot(a[0]-b[0],a[1]-b[1])>max_jump:
            return False
    return True
