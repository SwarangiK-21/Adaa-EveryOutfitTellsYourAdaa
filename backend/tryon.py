"""Virtual try-on: show the user wearing an outfit, using their own try-on server.

The server is the Colab notebook in tryon/Adaa_TryOn_Colab.ipynb (CatVTON on a free GPU).
Adaa sends it the user's full-body photo and one garment photo at a time:
  - a dress / gown / saree           -> "overall"
  - otherwise the bottom first ("lower"), then the top ("upper") on top of that result.
Shoes can optionally go on last ("shoes", experimental: the model is trained on clothes).
Jewellery, bags and accessories can't be tried on by the model; they are listed as skipped.

Results are cached on disk, keyed by the exact photos used, so showing the same outfit
again (e.g. swapping back) is instant and doesn't use the GPU.
"""
import hashlib
import json
import threading
from pathlib import Path

import httpx

import config
import storage
from recommender import garments as g

STEPS = {"high": 50, "standard": 30}   # diffusion steps per garment: quality vs. speed on a free T4 GPU
TIMEOUT_SECONDS = 240      # one garment can take a while, especially the first one after loading
_gpu_lock = threading.Lock()  # one try-on at a time: the free GPU can't do several at once


class TryOnError(Exception):
    """Something the user can act on. `status` is the HTTP status to return."""

    def __init__(self, message: str, status: int = 503):
        super().__init__(message)
        self.status = status


# ---------- settings (the Colab link and token) ----------

def _settings_path() -> Path:
    return config.DATA_DIR / "tryon_settings.json"


DEFAULTS = {"url": "", "token": "", "quality": "standard", "shoes": False}


def load_settings() -> dict:
    try:
        data = json.loads(_settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    settings = {**DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS and v is not None}}
    if settings["quality"] not in STEPS:
        settings["quality"] = DEFAULTS["quality"]
    return settings


def save_settings(url: str, token: str, quality: str = "standard", shoes: bool = False) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _settings_path().write_text(json.dumps({
        "url": url.strip().rstrip("/"), "token": token.strip(),
        "quality": quality if quality in STEPS else DEFAULTS["quality"], "shoes": bool(shoes),
    }), encoding="utf-8")


def is_configured() -> bool:
    s = load_settings()
    return bool(s["url"] and s["token"])


# ---------- which garments go on the person ----------

def plan(items: list[dict], try_shoes: bool = False) -> tuple[list[tuple[dict, str]], list[dict]]:
    """Returns ([(item, cloth_type), ...] in the order to apply them, [items that can't be tried on])."""
    one_pieces, tops, bottoms, shoes, skipped = [], [], [], [], []
    for item in items:
        role, _ = g.classify(item)
        if role == g.ONE_PIECE:
            one_pieces.append(item)
        elif role in (g.TOP, g.BLOUSE):
            tops.append(item)
        elif role == g.BOTTOM:
            bottoms.append(item)
        elif role == g.FOOTWEAR and try_shoes:
            shoes.append(item)
        else:
            skipped.append(item)  # footwear, jewellery, bags, dupattas, layers, accessories
    shoe_pass = [(s, "shoes") for s in shoes[:1]]
    if one_pieces:
        # A dress/saree covers the whole body; anything else worn with it can't be added on top.
        return [(one_pieces[0], "overall")] + shoe_pass, skipped + one_pieces[1:] + tops + bottoms + shoes[1:]
    if not (tops or bottoms):
        return [], skipped + shoes  # shoes alone aren't worth a try-on
    passes = [(b, "lower") for b in bottoms[:1]] + [(t, "upper") for t in tops[:1]] + shoe_pass
    return passes, skipped + bottoms[1:] + tops[1:] + shoes[1:]


# ---------- cache ----------

def cache_dir() -> Path:
    d = config.DATA_DIR / "tryon"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_key(person_filename: str, passes: list[tuple[dict, str]], steps: int) -> str:
    recipe = "|".join([person_filename, str(steps)] + [f"{i['image_filename']}:{t}" for i, t in passes])
    return hashlib.sha1(recipe.encode()).hexdigest()


def cached_image(name: str) -> Path | None:
    if len(name) != 44 or not name.endswith(".png") or any(c not in "0123456789abcdef" for c in name[:40]):
        return None
    path = cache_dir() / name
    return path if path.is_file() else None


def clear_cache() -> None:
    for f in [*cache_dir().glob("*.png"), *cache_dir().glob("*.json")]:
        f.unlink(missing_ok=True)


# ---------- talking to the try-on server ----------

BLOCKED = ("The try-on model's safety filter blocked this picture. It sometimes does this by mistake "
           "with short skirts, crop tops or bare shoulders, so Adaa is showing the drawing instead.")
UNREACHABLE = ("Can't reach your try-on server. Is the Colab notebook running? "
               "If you restarted it, paste the new link and token in Preferences.")


def check_server(url: str, token: str) -> str:
    """Returns a short description of the server, or raises TryOnError."""
    try:
        r = httpx.get(f"{url}/health", headers={"X-Adaa-Token": token}, timeout=15)
    except httpx.HTTPError:
        raise TryOnError(UNREACHABLE) from None
    if r.status_code == 401:
        raise TryOnError("The token was rejected. Copy the token shown in Colab.", 502)
    if r.status_code != 200:
        raise TryOnError(f"The link answered, but not like an Adaa try-on server (error {r.status_code}).", 502)
    info = r.json()
    return f"{info.get('model', 'Try-on')} on {info.get('gpu', 'GPU')}"


def call_server(url: str, token: str, person: bytes, cloth: bytes, cloth_type: str, steps: int = 50) -> bytes:
    """One garment onto one person photo. Returns PNG bytes."""
    try:
        r = httpx.post(
            f"{url}/tryon",
            headers={"X-Adaa-Token": token},
            files={"person": ("person.png", person), "cloth": ("cloth.png", cloth)},
            data={"cloth_type": cloth_type, "steps": str(steps)},
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException:
        raise TryOnError("Your try-on server took too long. It may still be warming up; try again in a minute.") from None
    except httpx.HTTPError:
        raise TryOnError(UNREACHABLE) from None
    if r.status_code == 401:
        raise TryOnError("The try-on token was rejected. Copy the current token from Colab into Preferences.", 502)
    if r.status_code == 451:
        raise TryOnError(BLOCKED, 422)
    if r.status_code == 422:
        raise TryOnError("The try-on model couldn't find you clearly in your photo. "
                         "Try a full-length, front-facing photo with good light.", 422)
    if r.status_code != 200:
        raise TryOnError(f"Your try-on server had a problem (error {r.status_code}). Check the Colab tab.", 502)
    if not r.content.startswith(b"\x89PNG"):
        raise TryOnError("Your try-on server sent back something that isn't an image.", 502)
    return r.content


def _read_photo(filename: str, what: str) -> bytes:
    path = storage.image_path(filename)
    if path is None:
        raise TryOnError(f"The photo for {what} is missing, so it can't be tried on.", 409)
    return path.read_bytes()


def _cached(path: Path, result: dict) -> dict:
    notes_file = path.with_suffix(".json")
    saved = json.loads(notes_file.read_text(encoding="utf-8")) if notes_file.exists() else {}
    return {**result, "garments": saved.get("garments", result["garments"]),
            "skipped": saved.get("skipped", result["skipped"]), "notes": saved.get("notes", [])}


def generate(person_filename: str, items: list[dict], cached_only: bool = False) -> dict:
    """Make (or reuse) an image of the user wearing these items.
    cached_only=True never uses the GPU: it returns a saved image or raises a 404 TryOnError."""
    settings = load_settings()
    steps = STEPS[settings["quality"]]
    passes, skipped = plan(items, try_shoes=settings["shoes"])
    if not passes:
        raise TryOnError("This look has no clothing that can be tried on (try-on works with tops, bottoms and dresses).", 400)
    key = cache_key(person_filename, passes, steps)
    path = cache_dir() / f"{key}.png"
    result = {
        "url": f"/api/tryon/images/{key}.png",
        "garments": [i["name"] for i, _ in passes],
        "skipped": [i["name"] for i in skipped],
        "notes": [],
        "cached": True,
    }
    if path.exists():
        return _cached(path, result)
    if cached_only:
        raise TryOnError("Not made yet.", 404)

    if not (settings["url"] and settings["token"]):
        raise TryOnError("Set up your try-on server in Preferences first.", 409)
    person = _read_photo(person_filename, "you")

    with _gpu_lock:
        if path.exists():  # another request made it while we waited
            return _cached(path, result)
        image, notes = person, []
        garments, extra_skipped = list(result["garments"]), []
        for item, cloth_type in passes:
            try:
                image = call_server(settings["url"], settings["token"], image,
                                    _read_photo(item["image_filename"], item["name"]), cloth_type, steps)
            except TryOnError as exc:
                if cloth_type != "shoes" or exc.status != 422:
                    raise
                # Experimental shoes didn't work: keep the clothes, and say so.
                notes.append(f"Your {item['name']} couldn't be added this time, so you're shown in the shoes from your photo.")
                garments.remove(item["name"])
                extra_skipped.append(item["name"])
        path.write_bytes(image)
        summary = {"garments": garments, "skipped": result["skipped"] + extra_skipped, "notes": notes}
        path.with_suffix(".json").write_text(json.dumps(summary), encoding="utf-8")
    return {**result, **summary, "cached": False}
