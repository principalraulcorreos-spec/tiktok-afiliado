"""Importa métricas.

1) API (automático): vistas, likes, comentarios, compartidos de tus videos (Display API).
2) CSV/Excel exportado de TikTok Studio (retención, tiempo visto) y del Centro de afiliados
   (clics al producto, pedidos, GMV, comisión). Los encabezados se reconocen en español o inglés.
3) Plantilla manual: data/plantilla_metricas.csv si prefieres capturarlo a mano una vez por semana.

Cada fila se asocia a un video por: id de TikTok > enlace del video > inicio de la descripción.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

from . import db

ALIAS = {
    "tiktok_video_id": ["video id", "id del video", "id de video", "item id", "video_id"],
    "link": ["video link", "enlace del video", "link", "url", "enlace"],
    "titulo": ["title", "titulo", "descripcion", "description", "video title", "titulo del video", "nombre del video"],
    "vistas": ["views", "video views", "vistas", "reproducciones", "visualizaciones", "vistas del video"],
    "likes": ["likes", "me gusta"],
    "comentarios": ["comments", "comentarios"],
    "compartidos": ["shares", "compartidos", "veces compartido"],
    "guardados": ["saves", "favorites", "guardados", "favoritos"],
    "tiempo_prom_seg": ["average watch time", "tiempo de reproduccion promedio", "tiempo promedio de visualizacion",
                        "avg watch time", "tiempo promedio visto"],
    "retencion_pct": ["watched full video", "vieron el video completo", "completion rate", "tasa de finalizacion",
                      "retencion"],
    "clics_producto": ["product clicks", "clics en el producto", "clics del producto", "clics", "clicks"],
    "pedidos": ["orders", "pedidos", "items sold", "articulos vendidos", "sku orders", "ventas"],
    "gmv": ["gmv", "ingresos", "revenue", "valor bruto"],
    "comision": ["commission", "est. commission", "comision", "comision estimada", "comisiones"],
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


def _num(x) -> float | None:
    if x is None:
        return None
    s = str(x).strip().replace("$", "").replace("MX", "").replace(",", "")
    if not s or s in {"-", "--"}:
        return None
    mult = 1
    if s.endswith("%"):
        s = s[:-1]
    if s[-1:].upper() == "K":
        mult, s = 1_000, s[:-1]
    elif s[-1:].upper() == "M":
        mult, s = 1_000_000, s[:-1]
    m = re.search(r"(\d+):(\d+)", s)  # 0:07
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    s = s.lower().replace("s", "")
    try:
        return float(s) * mult
    except ValueError:
        return None


def _mapear(encabezados: list[str]) -> dict[str, str]:
    mapa = {}
    norm = {h: _norm(h) for h in encabezados}
    for campo, alias in ALIAS.items():
        for h, n in norm.items():
            if any(n == _norm(a) for a in alias) and campo not in mapa:
                mapa[campo] = h
        if campo not in mapa:
            for h, n in norm.items():
                if any(_norm(a) in n for a in alias):
                    mapa[campo] = h
                    break
    return mapa


def _leer(ruta: Path) -> list[dict]:
    if ruta.suffix.lower() in {".xlsx", ".xls"}:
        import openpyxl  # pip install openpyxl
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
        filas = list(wb.active.iter_rows(values_only=True))
        enc = [str(c or "") for c in filas[0]]
        return [dict(zip(enc, f)) for f in filas[1:] if any(f)]
    with ruta.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _buscar_video(fila: dict, mapa: dict) -> int | None:
    interno = str(fila.get("video_id_interno", "") or "").strip()
    if interno.isdigit():
        tk = str(fila.get(mapa.get("tiktok_video_id", ""), "") or "").strip()
        if tk:
            db.actualizar("videos", int(interno), tiktok_video_id=tk)
        return int(interno)
    vid = str(fila.get(mapa.get("tiktok_video_id", ""), "") or "").strip()
    link = str(fila.get(mapa.get("link", ""), "") or "")
    if not vid and link:
        m = re.search(r"/video/(\d+)", link)
        vid = m.group(1) if m else ""
    if vid:
        r = db.query("SELECT id FROM videos WHERE tiktok_video_id=?", (vid,))
        if r:
            return r[0]["id"]
    titulo = _norm(str(fila.get(mapa.get("titulo", ""), "") or ""))[:40]
    if len(titulo) >= 12:
        for v in db.query("SELECT id, caption FROM videos WHERE caption IS NOT NULL"):
            if _norm(v["caption"])[:40].startswith(titulo[:25]):
                if vid:
                    db.actualizar("videos", v["id"], tiktok_video_id=vid)
                return v["id"]
    return None


def importar_archivo(ruta: str | Path, fuente: str = "csv", fecha: str | None = None) -> tuple[int, int]:
    ruta = Path(ruta)
    filas = _leer(ruta)
    if not filas:
        return 0, 0
    mapa = _mapear(list(filas[0].keys()))
    fecha = fecha or date.today().isoformat()
    ok = sin = 0
    with db.conectar() as con:
        for fila in filas:
            video_id = _buscar_video(fila, mapa)
            if not video_id:
                sin += 1
                continue
            vals = {c: _num(fila.get(h)) for c, h in mapa.items()
                    if c not in {"tiktok_video_id", "link", "titulo"}}
            if vals.get("retencion_pct") is not None and vals["retencion_pct"] <= 1:
                vals["retencion_pct"] *= 100
            cols = ["video_id", "fecha", "fuente", *vals.keys()]
            con.execute(
                f"INSERT INTO metricas ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)}) "
                f"ON CONFLICT(video_id, fecha, fuente) DO UPDATE SET "
                + ",".join(f"{k}=excluded.{k}" for k in vals) if vals else
                "INSERT OR IGNORE INTO metricas (video_id, fecha, fuente) VALUES (?,?,?)",
                (video_id, fecha, fuente, *vals.values()))
            ok += 1
    return ok, sin


def sincronizar_api() -> int:
    """Trae vistas/likes/comentarios/compartidos por la Display API y los asocia a tus videos."""
    from .publisher import listar_mis_videos
    hoy = date.today().isoformat()
    n = 0
    for it in listar_mis_videos(200):
        fila = {"id": it["id"], "titulo": it.get("title") or it.get("video_description", "")}
        video_id = _buscar_video(fila, {"tiktok_video_id": "id", "titulo": "titulo"})
        if not video_id:
            continue
        with db.conectar() as con:
            con.execute(
                "INSERT INTO metricas (video_id, fecha, fuente, vistas, likes, comentarios, compartidos) "
                "VALUES (?,?,?,?,?,?,?) ON CONFLICT(video_id, fecha, fuente) DO UPDATE SET "
                "vistas=excluded.vistas, likes=excluded.likes, comentarios=excluded.comentarios, "
                "compartidos=excluded.compartidos",
                (video_id, hoy, "api", it.get("view_count"), it.get("like_count"),
                 it.get("comment_count"), it.get("share_count")))
            con.execute("UPDATE videos SET tiktok_video_id=?, estado='publicado', "
                        "publicado=COALESCE(publicado, ?) WHERE id=?",
                        (it["id"], datetime.fromtimestamp(it.get("create_time", 0)).isoformat(), video_id))
        n += 1
    return n


def plantilla(ruta: str | Path) -> Path:
    ruta = Path(ruta)
    campos = ["video_id_interno", "Video ID", "Vistas", "Tiempo promedio visto", "Vieron el video completo",
              "Clics en el producto", "Pedidos", "GMV", "Comisión"]
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(campos)
        for v in db.query("SELECT id, tiktok_video_id FROM videos WHERE estado IN ('publicado','borrador')"):
            w.writerow([v["id"], v["tiktok_video_id"] or "", "", "", "", "", "", "", ""])
    return ruta
