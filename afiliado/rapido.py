"""Edición "rápida" para videos de ~30 s: cortes cada ~1.5 s alternando encuadres (jump cuts),
audio continuo de cada clip, whoosh entre clips, gancho en pantalla y etiqueta de IA.

Cada tramo es (inicio, fin, zoom, ancla_x, ancla_y): zoom 1.0 = completo; 1.3 = acercamiento.
ancla 0..1 = qué parte de la imagen se conserva al hacer zoom (0.5,0.35 = centro-arriba, cara).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .editor import FPS, H, W, _drawtext, _fuente, _run, duracion


def tramos_auto(dur: float, paso: float = 1.55, zooms=(1.0, 1.28), fin_recorte: float = 0.35,
                forzar: list[tuple[float, float, float, float, float]] | None = None):
    """Parte un clip en tramos de `paso` s alternando zoom. `forzar` reemplaza los tramos que se cruzan."""
    out, t, i = [], 0.0, 0
    fin = dur - fin_recorte
    while t < fin - 0.3:
        b = min(t + paso, fin)
        if fin - b < 0.6:
            b = fin
        out.append((t, b, zooms[i % len(zooms)], 0.5, 0.35))
        t, i = b, i + 1
    for f in forzar or []:
        nuevos = []
        for s in out:
            if s[1] <= f[0] or s[0] >= f[1]:
                nuevos.append(s)
            else:
                if s[0] < f[0]:
                    nuevos.append((s[0], f[0], *s[2:]))
                if s[1] > f[1]:
                    nuevos.append((f[1], s[1], *s[2:]))
        out = sorted(nuevos + [f])
    return out


def armar(clips: list[tuple[str, list]], salida: str | Path, gancho: str = "", etiqueta_ia: bool = True,
          whoosh: bool = True) -> Path:
    salida = Path(salida)
    fuente = _fuente()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        partes, marcas, t_total = [], [], 0.0
        for ci, (clip, tramos) in enumerate(clips):
            for si, (a, b, z, ax, ay) in enumerate(tramos):
                out = tmp / f"c{ci}_{si}.mp4"
                cw, ch = f"iw/{z}", f"ih/{z}"
                vf = (f"crop={cw}:{ch}:(iw-{cw})*{ax}:(ih-{ch})*{ay},"
                      f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1")
                _run(["ffmpeg", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", clip, "-vf", vf,
                      "-af", "aresample=44100,aformat=channel_layouts=stereo",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-c:a", "aac", "-ar", "44100", str(out)])
                partes.append(out)
                d = duracion(out)
                if si == 0 and ci > 0:
                    marcas.append(t_total)
                t_total += d
        lista = tmp / "l.txt"
        lista.write_text("".join(f"file '{p.as_posix()}'\n" for p in partes), encoding="utf-8")
        base = tmp / "base.mp4"
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c:v", "libx264", "-preset",
              "veryfast", "-crf", "19", "-c:a", "aac", str(base)])

        filtros = []
        if gancho:
            import textwrap
            for i, ln in enumerate(textwrap.wrap(gancho, 16)[:3]):
                tf = tmp / f"g{i}.txt"
                tf.write_text(ln, encoding="utf-8")
                filtros.append(_drawtext(fuente, tf, 92, f"h*0.62+{i * 118}", 0, 2.4))
        if etiqueta_ia:
            tf = tmp / "ia.txt"
            tf.write_text("Contenido generado con IA", encoding="utf-8")
            filtros.append(_drawtext(fuente, tf, 30, "h*0.045", box=True))
        vf = ",".join(filtros) or "null"

        entradas, mix = ["-i", str(base)], ""
        if whoosh and marcas:
            w = tmp / "w.wav"
            _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=d=0.4:c=pink:a=0.9", "-af",
                  "highpass=f=700,lowpass=f=5000,afade=t=in:d=0.2,afade=t=out:st=0.2:d=0.2,"
                  "aformat=channel_layouts=stereo:sample_rates=44100", str(w)])
            for i, m in enumerate(marcas):
                entradas += ["-i", str(w)]
                d = int(max(m - 0.2, 0) * 1000)
                mix += f"[{i + 1}:a]adelay={d}|{d},volume=0.45[w{i}];"
            mix += "[0:a]" + "".join(f"[w{i}]" for i in range(len(marcas))) + \
                   f"amix=inputs={len(marcas) + 1}:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]"
        else:
            mix = "[0:a]loudnorm=I=-14:TP=-1.5[a]"
        _run(["ffmpeg", "-y", *entradas, "-filter_complex", f"[0:v]{vf}[v];{mix}", "-map", "[v]", "-map", "[a]",
              "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
              "-b:a", "160k", "-movflags", "+faststart", str(salida)])
    return salida
