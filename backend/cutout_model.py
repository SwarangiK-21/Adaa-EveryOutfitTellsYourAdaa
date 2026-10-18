"""The AI models used (in the browser) to make clean garment pictures. Each is downloaded once.

- isnet:   IS-Net background removal (Apache 2.0), from the rembg project.        ~179 MB
- clothes: SegFormer-B2 clothes parser (ATR labels: top, skirt, pants, dress,
           shoes, bag, face, arms...), quantised ONNX by Xenova.                   ~29 MB
           Licence: NVIDIA SegFormer licence, NON-COMMERCIAL (research/evaluation) use only.
"""
from pathlib import Path

import httpx

import config

MODELS = {
    "isnet": (
        "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx",
        "isnet-general-use.onnx",
        178_648_008,
    ),
    "clothes": (
        "https://huggingface.co/Xenova/segformer_b2_clothes/resolve/main/onnx/model_quantized.onnx",
        "segformer_b2_clothes_quantized.onnx",
        28_837_959,
    ),
}


class ModelUnavailable(Exception):
    pass


def model_path(name: str) -> Path:
    return config.DATA_DIR / "models" / MODELS[name][1]


def ensure_model(name: str = "isnet") -> Path:
    if name not in MODELS:
        raise ModelUnavailable("Unknown model.")
    url, _, expected = MODELS[name]
    path = model_path(name)
    if path.exists() and path.stat().st_size == expected:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=600) as r:
            r.raise_for_status()
            with part.open("wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
    except httpx.HTTPError:
        part.unlink(missing_ok=True)
        raise ModelUnavailable(f"Couldn't download the {name} model (needs internet once).") from None
    if part.stat().st_size != expected:
        part.unlink(missing_ok=True)
        raise ModelUnavailable(f"The {name} model download was incomplete. Try again.")
    part.replace(path)
    return path
