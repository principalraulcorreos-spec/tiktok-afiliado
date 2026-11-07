"""QA objetivo de un video terminado (sin opiniones: solo números medidos con ffmpeg).

    python -m afiliado.qa Downloads/<Producto>/FINAL.mp4            → imprime JSON y guarda qa.json + qa_hoja.jpg
    python -m afiliado.qa FINAL.mp4 --registro guia/metricas.csv     → además agrega una fila al histórico

Métricas y umbral (✅/⚠️):
- duracion_s            13–28 s (rango de los videos ganadores analizados)
- lufs                  −15 a −13 (TikTok normaliza a ~−14)
- true_peak_db          ≤ −1.0
- cortes_por_s          ≥ 0.5 (un cambio de plano cada ≤ 2 s)
- congelado_pct         ≤ 10 % (tiempo con imagen quieta ≥ 0.5 s; la política castiga lo estático)
- negro_s               0
- verde_residual_pct    ≤ 0.5 % de píxeles color pantalla verde en la zona de la presentadora
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

W, H = 1080, 1920
ZONA_PRES = (591, 200, 453, 520)   # x, y, w, h de la presentadora arriba a la derecha (ancho 0.42)

UMBRALES = {
    "duracion_s": (13, 28), "lufs": (-15.0, -13.0), "true_peak_db": (None, -1.0), "cortes_por_s": (0.5, None),
    "congelado_pct": (None, 10.0), "negro_s": (None, 0.0), "verde_residual_pct": (None, 0.5),
}


def _ff(args: list[str]) -> str:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True).stderr


def medir(video: str | Path) -> dict:
    v = str(video)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v],
                               capture_output=True, text=True).stdout.strip())
    m = {"video": Path(v).name, "duracion_s": round(dur, 2)}

    e = _ff(["-i", v, "-af", "ebur128=peak=true", "-f", "null", "-"])
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", e)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)
    m["lufs"] = float(i[-1]) if i else None
    m["true_peak_db"] = float(p[-1]) if p else None

    s = _ff(["-i", v, "-vf", "select='gt(scene,0.30)',showinfo", "-f", "null", "-"])
    m["cortes_por_s"] = round(len(re.findall(r"pts_time:", s)) / dur, 2)

    f = _ff(["-i", v, "-vf", "freezedetect=n=0.003:d=0.5", "-an", "-f", "null", "-"])
    congelado = sum(float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", f))
    m["congelado_pct"] = round(100 * congelado / dur, 1)

    b = _ff(["-i", v, "-vf", "blackdetect=d=0.2:pix_th=0.08", "-an", "-f", "null", "-"])
    m["negro_s"] = round(sum(float(x) for x in re.findall(r"black_duration:([\d.]+)", b)), 2)

    # verde residual: píxeles muy verdes (G alto, R y B bajos) en la zona de la presentadora, 1 cuadro por segundo
    x, y, w, h = ZONA_PRES
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", f"fps=1,crop={w}:{h}:{x}:{y},scale=113:130",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    tot = verdes = 0
    for k in range(0, len(raw) - 2, 3):
        r_, g_, b_ = raw[k], raw[k + 1], raw[k + 2]
        tot += 1
        if g_ > 120 and g_ > r_ * 1.45 and g_ > b_ * 1.45:
            verdes += 1
    m["verde_residual_pct"] = round(100 * verdes / tot, 2) if tot else None

    m["mb"] = round(Path(v).stat().st_size / 1e6, 2)
    m["evaluacion"] = {k: _ok(k, m.get(k)) for k in UMBRALES}
    m["aprobado"] = all(x != "⚠️" for x in m["evaluacion"].values())
    return m


def _ok(k: str, val) -> str:
    if val is None:
        return "—"
    lo, hi = UMBRALES[k]
    return "✅" if (lo is None or val >= lo) and (hi is None or val <= hi) else "⚠️"


def hoja(video: str | Path, salida: str | Path, n: int = 8) -> Path:
    """Hoja de contacto de n cuadros repartidos en el video (para revisar a ojo en 1 imagen)."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(video)], capture_output=True, text=True).stdout.strip())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf",
                    f"fps={n / dur:.4f},scale=180:-1,tile={n}x1", "-frames:v", "1", str(salida)], check=True)
    return Path(salida)


def registrar(m: dict, csv_path: str | Path, producto: str = "", version: str = "") -> None:
    csv_path = Path(csv_path)
    campos = ["fecha", "producto", "version", "video", *UMBRALES.keys(), "mb", "aprobado"]
    nuevo = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        if nuevo:
            w.writeheader()
        w.writerow({"fecha": dt.date.today().isoformat(), "producto": producto, "version": version, **m})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    vid = Path(sys.argv[1])
    res = medir(vid)
    (vid.parent / "qa.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    hoja(vid, vid.parent / "qa_hoja.jpg")
    if "--registro" in sys.argv:
        registrar(res, sys.argv[sys.argv.index("--registro") + 1], vid.parent.name)
    print(json.dumps(res, ensure_ascii=False, indent=1))
