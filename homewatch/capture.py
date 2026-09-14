"""Capture with rpicam-still, adapted from Intellens/src/capture/capture.py."""
import io
import subprocess

from PIL import Image


def take_photo(settle_ms=1000):
    # Intellens uses auto focus and a JPEG capture. stdout avoids SD card writes.
    command = [
        "rpicam-still",
        "-o", "-",
        "--timeout", str(settle_ms),
        "--autofocus-mode", "auto",
        "--width", "1280",
        "--height", "960",
        "--nopreview",
        "--encoding", "jpg",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True,
                                timeout=settle_ms / 1000 + 10)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Camera capture timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("rpicam-still failed; check the camera connection and settings") from exc
    with Image.open(io.BytesIO(result.stdout)) as image:
        return image.convert("RGB")
