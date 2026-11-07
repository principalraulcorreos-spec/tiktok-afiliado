"""Publicación con la API oficial de TikTok (Content Posting API).

Lo que la API SÍ hace:  subir el video y la descripción; marcarlo como IA (is_aigc) en publicación directa.
Lo que la API NO hace:  vincular el producto del carrito naranja (no existe ese campo).
Por eso el modo por defecto es BORRADOR: el video llega a tu bandeja de TikTok y tú, en la app, tocas
"Agregar enlace → Productos", activas "Contenido generado por IA" y publicas (≈1 min por video).

Requisitos: app en developers.tiktok.com con Login Kit + Content Posting API (scope video.upload;
video.publish para directo). Sin auditoría, la publicación directa solo puede ser privada.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import secrets
import time
import urllib.parse
from pathlib import Path

import requests

from . import db
from .config import TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REDIRECT_URI, TIKTOK_TOKEN_PATH

API = "https://open.tiktokapis.com"
SCOPES = "user.info.basic,video.upload,video.publish,video.list"
CHUNK = 10 * 1024 * 1024  # 10 MB


# ---------- OAuth ----------
def url_autorizacion() -> str:
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(16)
    TIKTOK_TOKEN_PATH.with_suffix(".pkce").write_text(json.dumps({"verifier": verifier, "state": state}))
    q = {"client_key": TIKTOK_CLIENT_KEY, "scope": SCOPES, "response_type": "code",
         "redirect_uri": TIKTOK_REDIRECT_URI, "state": state,
         "code_challenge": challenge, "code_challenge_method": "S256"}
    return "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(q)


def canjear_codigo(url_o_codigo: str) -> dict:
    """Pega aquí la URL completa a la que te redirigió TikTok (o solo el code)."""
    code = url_o_codigo
    if "code=" in url_o_codigo:
        code = urllib.parse.parse_qs(urllib.parse.urlparse(url_o_codigo).query)["code"][0]
    pk = json.loads(TIKTOK_TOKEN_PATH.with_suffix(".pkce").read_text())
    r = requests.post(f"{API}/v2/oauth/token/", data={
        "client_key": TIKTOK_CLIENT_KEY, "client_secret": TIKTOK_CLIENT_SECRET, "code": code,
        "grant_type": "authorization_code", "redirect_uri": TIKTOK_REDIRECT_URI,
        "code_verifier": pk["verifier"]}, timeout=30)
    return _guardar_token(r)


def _guardar_token(r: requests.Response) -> dict:
    data = r.json()
    if "access_token" not in data:
        raise RuntimeError(f"Error de token: {data}")
    data["obtenido"] = time.time()
    TIKTOK_TOKEN_PATH.write_text(json.dumps(data, indent=2))
    return data


def token() -> str:
    if not TIKTOK_TOKEN_PATH.exists():
        raise SystemExit("Primero autoriza: python -m afiliado tiktok-login")
    t = json.loads(TIKTOK_TOKEN_PATH.read_text())
    if time.time() > t["obtenido"] + t.get("expires_in", 86400) - 300:
        r = requests.post(f"{API}/v2/oauth/token/", data={
            "client_key": TIKTOK_CLIENT_KEY, "client_secret": TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token", "refresh_token": t["refresh_token"]}, timeout=30)
        t = _guardar_token(r)
    return t["access_token"]


def _h(json_body: bool = True) -> dict:
    h = {"Authorization": f"Bearer {token()}"}
    if json_body:
        h["Content-Type"] = "application/json; charset=UTF-8"
    return h


def _check(r: requests.Response) -> dict:
    data = r.json()
    err = data.get("error", {})
    if err.get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok API: {err}")
    return data.get("data", {})


# ---------- Publicación ----------
def info_creador() -> dict:
    return _check(requests.post(f"{API}/v2/post/publish/creator_info/query/", headers=_h(), timeout=30))


def _subir(upload_url: str, ruta: Path) -> None:
    total = ruta.stat().st_size
    n = max(1, math.floor(total / CHUNK)) if total > CHUNK else 1
    size = total if n == 1 else CHUNK
    with ruta.open("rb") as f:
        for i in range(n):
            ini = i * size
            fin = total - 1 if i == n - 1 else ini + size - 1
            f.seek(ini)
            data = f.read(fin - ini + 1)
            r = requests.put(upload_url, data=data, timeout=300, headers={
                "Content-Type": "video/mp4", "Content-Length": str(len(data)),
                "Content-Range": f"bytes {ini}-{fin}/{total}"})
            if r.status_code not in (200, 201, 206):
                raise RuntimeError(f"Fallo subiendo chunk {i}: {r.status_code} {r.text[:300]}")


def _source_info(ruta: Path) -> dict:
    total = ruta.stat().st_size
    n = max(1, math.floor(total / CHUNK)) if total > CHUNK else 1
    return {"source": "FILE_UPLOAD", "video_size": total,
            "chunk_size": total if n == 1 else CHUNK, "total_chunk_count": n}


def subir_borrador(video_id: int) -> str:
    """Sube a la bandeja de TikTok (borrador). Tú terminas en la app: producto + etiqueta IA + publicar."""
    v = db.query("SELECT * FROM videos WHERE id=?", (video_id,))[0]
    ruta = Path(v["final_path"])
    data = _check(requests.post(f"{API}/v2/post/publish/inbox/video/init/", headers=_h(),
                                json={"source_info": _source_info(ruta)}, timeout=60))
    _subir(data["upload_url"], ruta)
    db.actualizar("videos", video_id, publish_id=data["publish_id"], estado="borrador")
    return data["publish_id"]


def publicar_directo(video_id: int, privacidad: str | None = None) -> str:
    """Publicación directa con etiqueta de IA. OJO: queda SIN producto vinculado; agrégalo después
    en Centro de creadores de TikTok Shop → Vincular productos (si tu cuenta lo tiene disponible)."""
    v = db.query("SELECT * FROM videos WHERE id=?", (video_id,))[0]
    ruta = Path(v["final_path"])
    info = info_creador()
    opciones = info.get("privacy_level_options", [])
    privacidad = privacidad or ("PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in opciones else "SELF_ONLY")
    body = {
        "post_info": {
            "title": f"{v['caption']}\n{v['hashtags']}"[:2200],
            "privacy_level": privacidad,
            "disable_duet": False, "disable_comment": False, "disable_stitch": False,
            "is_aigc": True,
            "brand_content_toggle": False,
            "brand_organic_toggle": False,
        },
        "source_info": _source_info(ruta),
    }
    data = _check(requests.post(f"{API}/v2/post/publish/video/init/", headers=_h(), json=body, timeout=60))
    _subir(data["upload_url"], ruta)
    db.actualizar("videos", video_id, publish_id=data["publish_id"], estado="publicado", publicado=db.now())
    return data["publish_id"]


def estado_publicacion(publish_id: str) -> dict:
    return _check(requests.post(f"{API}/v2/post/publish/status/fetch/", headers=_h(),
                                json={"publish_id": publish_id}, timeout=30))


# ---------- Métricas básicas (Display API) ----------
def listar_mis_videos(max_items: int = 100) -> list[dict]:
    campos = "id,title,video_description,create_time,view_count,like_count,comment_count,share_count,duration"
    salida, cursor = [], None
    while len(salida) < max_items:
        body = {"max_count": 20}
        if cursor:
            body["cursor"] = cursor
        data = _check(requests.post(f"{API}/v2/video/list/?fields={campos}", headers=_h(), json=body, timeout=30))
        salida += data.get("videos", [])
        if not data.get("has_more"):
            break
        cursor = data.get("cursor")
    return salida
