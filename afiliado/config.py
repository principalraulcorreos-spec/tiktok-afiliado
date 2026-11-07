"""Configuración central. Todo se lee de variables de entorno o del archivo .env."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(os.environ.get("AFILIADO_HOME", Path(__file__).resolve().parent.parent))


def _load_dotenv() -> None:
    env = BASE_DIR / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

DB_PATH = Path(os.environ.get("AFILIADO_DB", BASE_DIR / "data" / "afiliado.db"))
PRODUCTS_DIR = BASE_DIR / "data" / "productos"      # imágenes de cada producto
CLIPS_DIR = BASE_DIR / "data" / "clips"             # clips crudos de la IA
VOICES_DIR = BASE_DIR / "data" / "voces"            # tus voces grabadas
OUTPUT_DIR = BASE_DIR / "data" / "listos"           # videos finales listos para publicar
KITS_DIR = BASE_DIR / "data" / "kits"               # plan diario: prompts + captions
REPORTS_DIR = BASE_DIR / "data" / "reportes"
RULES_PATH = BASE_DIR / "data" / "reglas.json"      # reglas que genera la evaluación mensual
FONT_PATH = os.environ.get("FONT_PATH", "")          # .ttf para el texto del gancho (opcional)

# Gemini API (Veo)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
VEO_MODEL = os.environ.get("VEO_MODEL", "veo-3.1-generate-preview")  # usa `listar-modelos` para ver Lite/Fast

# TikTok for Developers (Content Posting API + Display API)
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.environ.get("TIKTOK_REDIRECT_URI", "https://localhost/callback")
TIKTOK_TOKEN_PATH = BASE_DIR / "data" / "tiktok_token.json"

# Operación
VIDEOS_POR_DIA = int(os.environ.get("VIDEOS_POR_DIA", "4"))
HORARIOS = os.environ.get("HORARIOS", "12:30,15:30,19:00,21:30").split(",")
VOZ_IA = os.environ.get("VOZ_IA", "1") == "1"  # 1 = la voz la dice Veo dentro del clip; 0 = la grabas tú
TIPO_CAMBIO = float(os.environ.get("TIPO_CAMBIO", "18.5"))  # MXN por USD, solo para estimar costos

for d in (PRODUCTS_DIR, CLIPS_DIR, VOICES_DIR, OUTPUT_DIR, KITS_DIR, REPORTS_DIR, DB_PATH.parent):
    d.mkdir(parents=True, exist_ok=True)
