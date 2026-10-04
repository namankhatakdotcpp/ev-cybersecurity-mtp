import math
import os
from typing import Tuple

import numpy as np
import soundfile as sf
import sounddevice as sd


def load_mono(path: str) -> Tuple[np.ndarray, int]:
    """Load audio file and return mono float32 samples and sample rate."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    data, sr = sf.read(path, always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data.astype(np.float32), sr


def pan_to_stereo(mono: np.ndarray, pan: float) -> np.ndarray:
    """Constant-power pan from mono to stereo. pan in [-1.0..1.0]."""
    pan = max(-1.0, min(1.0, float(pan)))
    angle = (pan + 1.0) * (math.pi / 4.0)
    g_l = math.cos(angle)
    g_r = math.sin(angle)
    left = mono * g_l
    right = mono * g_r
    return np.vstack((left, right)).T


def position_to_stereo(mono: np.ndarray, front: float, right: float, ref_distance: float = 1.0) -> np.ndarray:
    """Convert a mono signal to stereo using a simple 2D position.

    - `front` is forward distance (positive in front)
    - `right` is rightward offset (positive to the listener's right)
    """
    angle = math.atan2(right, front)
    pan = math.sin(angle)

    pan = max(-1.0, min(1.0, float(pan)))
    angle_p = (pan + 1.0) * (math.pi / 4.0)
    g_l = math.cos(angle_p)
    g_r = math.sin(angle_p)

    dist = math.hypot(front, right)
    attenuation = ref_distance / (ref_distance + dist)

    left = mono * g_l * attenuation
    right_ch = mono * g_r * attenuation
    return np.vstack((left, right_ch)).T


def play_stereo(stereo: np.ndarray, sr: int, blocking: bool = True) -> None:
    sd.play(stereo, sr)
    if blocking:
        sd.wait()


def play_position_from_mono(mono: np.ndarray, sr: int, front: float, right: float, wait: bool = True, ref_distance: float = 1.0) -> None:
    stereo = position_to_stereo(mono, front, right, ref_distance=ref_distance)
    play_stereo(stereo, sr, blocking=wait)


def play_input(value: int, wait: bool = True, audio_dir: str = "audio") -> None:
    """Map input to left/right audio and play at a small offset.

    - `value == 0`: play `audio/right.ogg` at position (front=1, right=+0.5)
    - `value == 1`: play `audio/left.ogg` at position (front=1, right=-0.5)
    """
    if value == 0:
        fname = os.path.join(audio_dir, "right.ogg")
        front, right = 1.0, 0.5
    elif value == 1:
        fname = os.path.join(audio_dir, "left.ogg")
        front, right = 1.0, -0.5
    else:
        raise ValueError("value must be 0 (right) or 1 (left)")

    mono, sr = load_mono(fname)
    play_position_from_mono(mono, sr, front, right, wait)


if __name__ == "__main__":
    # simple CLI test: python c:\Users\06562\Desktop\EV\backend\audio_direction.py 0
    import sys

    if len(sys.argv) < 2:
        print("Usage: python backend/audio_direction.py <0|1>")
        raise SystemExit(1)
    val = int(sys.argv[1])
    play_input(val, wait=True)
