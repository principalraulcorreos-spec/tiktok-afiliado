"""Segmento de video con las FOTOS REALES del producto (gratis, sin créditos).

Cada foto: fondo desenfocado de la misma foto + foto centrada con zoom lento + texto.
Se usa para alargar un clip de IA (clip 8 s + fotos 6-8 s) o como video de respaldo.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .editor import FPS, H, W, _esc, _fuente, _run


def musica(salida: Path, dur: float) -> Path:
    """Base musical simple y libre de derechos (acordes suaves + pulso). Sustitúyela por un audio de la biblioteca de TikTok al publicar si quieres."""
    acordes = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7)]
    partes = []
    for i, (a, b, c) in enumerate(acordes):
        partes.append(f"(between(mod(t,4),{i},{i+1}))*(sin(2*PI*{a}*t)+sin(2*PI*{b}*t)+0.7*sin(2*PI*{c}*t))")
    expr = "0.07*(" + "+".join(partes) + ")*(0.6+0.4*exp(-6*mod(t,0.5)))"
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={dur:.2f}",
          "-af", "afade=t=in:d=0.3,afade=t=out:st={:.2f}:d=0.6,aformat=channel_layouts=stereo".format(max(dur - 0.6, 0)),
          "-c:a", "aac", str(salida)])
    return salida


def segmento(fotos: list[str], textos: list[str], salida: str | Path, seg_por_foto: float = 2.3,
             audio: bool = True) -> Path:
    """Arma un video 1080x1920 con las fotos. textos[i] va sobre la foto i ('' = sin texto)."""
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    fuente = _fuente()
    frames = int(seg_por_foto * FPS)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        partes = []
        for i, foto in enumerate(fotos):
            txt = textos[i] if i < len(textos) else ""
            tf = tmp / f"t{i}.txt"
            tf.write_text(txt, encoding="utf-8")
            zoom = "min(1+0.0015*on,1.12)" if i % 2 == 0 else "max(1.12-0.0015*on,1)"
            filtro = (
                f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:2,eq=brightness=-0.08[bg];"
                f"[0:v]scale=2000:-1,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1000x1000:fps={FPS}[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2-60:shortest=1,setsar=1"
            )
            if txt:
                filtro += (f",drawtext=fontfile='{_esc(fuente)}':textfile='{_esc(tf)}':fontsize=76:fontcolor=white:"
                           f"x=(w-text_w)/2:y=h*0.76:borderw=4:bordercolor=black@0.9:box=1:boxcolor=black@0.45:boxborderw=20")
            out = tmp / f"f{i}.mp4"
            _run(["ffmpeg", "-y", "-loop", "1", "-t", f"{seg_por_foto}", "-i", foto, "-filter_complex", filtro,
                  "-t", f"{seg_por_foto}", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                  "-pix_fmt", "yuv420p", str(out)])
            partes.append(out)
        lista = tmp / "l.txt"
        lista.write_text("".join(f"file '{p.as_posix()}'\n" for p in partes), encoding="utf-8")
        mudo = tmp / "mudo.mp4"
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(mudo)])
        dur = seg_por_foto * len(fotos)
        if audio:
            m = musica(tmp / "m.m4a", dur)
            _run(["ffmpeg", "-y", "-i", str(mudo), "-i", str(m), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                  "-c:a", "aac", "-shortest", str(salida)])
        else:
            _run(["ffmpeg", "-y", "-i", str(mudo), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v",
                  "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(salida)])
    return salida
