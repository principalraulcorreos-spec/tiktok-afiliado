"""Auditoría automática del repo (la corre la tarea programada diaria y se puede correr a mano).

    python scripts/auditoria.py            → imprime un bloque Markdown con métricas medidas

Mide: pruebas (pasan / tiempo), avisos de pyflakes, líneas de código, último QA de videos
(guia/metricas_videos.csv) y rendimiento publicado (guia/metricas_rendimiento.csv si existe).
No inventa nada: si un dato no existe, lo reporta como "sin datos".
"""
from __future__ import annotations

import csv
import datetime as dt
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _sh(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


def pruebas() -> dict:
    t = time.time()
    code, out = _sh([sys.executable, "-m", "pytest", "-q", "tests"])
    m = re.search(r"(\d+) passed", out)
    f = re.search(r"(\d+) failed", out)
    return {"pasan": int(m.group(1)) if m else 0, "fallan": int(f.group(1)) if f else (0 if code == 0 else -1),
            "segundos": round(time.time() - t, 1)}


def lint() -> int:
    code, out = _sh([sys.executable, "-m", "pyflakes", "afiliado", "tests", "scripts"])
    return len([x for x in out.splitlines() if x.strip()])


def loc() -> int:
    return sum(len(p.read_text(encoding="utf-8", errors="ignore").splitlines()) for p in (RAIZ / "afiliado").glob("*.py"))


def ultimas_filas(nombre: str, n: int = 5) -> list[dict]:
    p = RAIZ / "guia" / nombre
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))[-n:]


if __name__ == "__main__":
    pr = pruebas()
    print(f"### Auditoría automática {dt.date.today().isoformat()}")
    print(f"- Pruebas: {pr['pasan']} pasan, {pr['fallan']} fallan ({pr['segundos']} s)")
    print(f"- Avisos de pyflakes: {lint()}")
    print(f"- Líneas de código en afiliado/: {loc()}")
    qa = ultimas_filas("metricas_videos.csv")
    if qa:
        print("- Últimos QA de videos:")
        for r in qa:
            print(f"  - {r['fecha']} {r['producto']} {r.get('version', '')}: {r['duracion_s']} s, {r['lufs']} LUFS, "
                  f"{r['cortes_por_s']} cortes/s, congelado {r['congelado_pct']} %, verde {r['verde_residual_pct']} %, "
                  f"aprobado={r['aprobado']}")
    else:
        print("- Últimos QA de videos: sin datos")
    rend = ultimas_filas("metricas_rendimiento.csv", 10)
    print("- Rendimiento publicado: " + (f"{len(rend)} filas recientes" if rend else
                                          "sin datos (falta sesión de TikTok Studio / Centro de afiliados)"))
