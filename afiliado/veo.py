"""Generación automática con Veo vía Gemini API (de pago). Para el MVP usa Flow a mano.

Siempre genera desde la FOTO REAL del producto (image-to-video) para no tergiversarlo.
pip install google-genai
"""
from __future__ import annotations

import time
from pathlib import Path

from . import db
from .config import BASE_DIR, CLIPS_DIR, GEMINI_API_KEY, VEO_MODEL

# Precio aproximado por segundo (USD) en Gemini API, oct 2026. Ajusta si cambia.
PRECIO_SEG = {"lite": 0.05, "fast": 0.10, "default": 0.40}


def _cliente():
    if not GEMINI_API_KEY:
        raise SystemExit("Falta GEMINI_API_KEY en .env")
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def listar_modelos() -> list[str]:
    cli = _cliente()
    return [m.name for m in cli.models.list() if "veo" in m.name.lower()]


def _precio(modelo: str) -> float:
    m = modelo.lower()
    return PRECIO_SEG["lite"] if "lite" in m else PRECIO_SEG["fast"] if "fast" in m else PRECIO_SEG["default"]


def generar(video_id: int, modelo: str | None = None, duracion: int = 8, resolucion: str = "720p") -> Path:
    from google.genai import types

    modelo = modelo or VEO_MODEL
    v = db.query("SELECT v.*, p.imagenes FROM videos v JOIN productos p ON p.id=v.producto_id WHERE v.id=?",
                 (video_id,))
    if not v:
        raise SystemExit(f"No existe el video {video_id}")
    v = v[0]
    imagen = (v["imagenes"] or "").split("|")[0]
    if imagen and not Path(imagen).is_absolute():
        imagen = str(BASE_DIR / imagen)
    if not imagen or not Path(imagen).exists():
        raise SystemExit(f"El producto no tiene imagen local válida: {imagen!r}. Es obligatoria (image-to-video).")

    cli = _cliente()
    img = types.Image.from_file(location=imagen)
    op = cli.models.generate_videos(
        model=modelo,
        prompt=v["prompt"],
        image=img,
        config=types.GenerateVideosConfig(
            aspect_ratio="9:16",
            resolution=resolucion,
            duration_seconds=duracion,
            person_generation="allow_adult",
            number_of_videos=1,
        ),
    )
    t0 = time.time()
    while not op.done:
        if time.time() - t0 > 600:
            raise TimeoutError("Veo tardó más de 10 min")
        time.sleep(10)
        op = cli.operations.get(op)
    if not op.response or not op.response.generated_videos:
        raise RuntimeError(f"Veo no devolvió video (posible filtro de seguridad): {op}")

    destino = CLIPS_DIR / f"video_{video_id}_{int(time.time())}.mp4"
    gen = op.response.generated_videos[0]
    cli.files.download(file=gen.video)
    gen.video.save(str(destino))

    costo = duracion * _precio(modelo)
    db.actualizar("videos", video_id, clip_path=str(destino), motor="veo_api",
                  costo_usd=(v["costo_usd"] or 0) + costo, estado="clip_ok")
    return destino
