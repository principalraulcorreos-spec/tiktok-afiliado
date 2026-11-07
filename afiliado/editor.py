"""Edición automática con ffmpeg.

Entrada: 1 o más clips de IA (+ tu voz opcional).
Salida: MP4 1080x1920, 30 fps, con:
  - gancho en texto grande los primeros 2.5 s
  - aviso pequeño "Contenido generado con IA" todo el video
  - tu voz encima del audio ambiente (bajado al 15 %)
  - subtítulos automáticos de tu voz (si tienes faster-whisper instalado)
Si tu voz dura más que los clips, el video se repite hasta cubrirla.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

from . import db
from .config import FONT_PATH, OUTPUT_DIR

W, H, FPS = 1080, 1920, 30


def _fuente() -> str:
    candidatos = [FONT_PATH] if FONT_PATH else []
    if platform.system() == "Windows":
        candidatos += ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf"]
    elif platform.system() == "Darwin":
        candidatos += ["/System/Library/Fonts/Supplemental/Arial Bold.ttf"]
    candidatos += ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
    for c in candidatos:
        if c and Path(c).exists():
            return c
    raise SystemExit("No encontré una fuente .ttf. Define FONT_PATH en .env")


def _esc(path: str) -> str:
    """Escapa rutas para filtros de ffmpeg (incluye C:/ de Windows)."""
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def duracion(path: str | Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return float(json.loads(out.stdout)["format"]["duration"])


def _tiene_audio(path: str | Path) -> bool:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return bool(out.stdout.strip())


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falló:\n" + r.stderr[-2000:])


def _base(clips: list[str], recorte_inicio: float, tmp: Path, recorte_final: float = 0.0) -> Path:
    """Escala/recorta cada clip a 9:16 y los une en uno solo (con audio ambiente o silencio).

    recorte_final quita los últimos segundos de CADA clip: Veo tiende a "derivar" al final
    (aparece la cara, objetos nuevos). Regla R9 del estándar de prompts.
    """
    partes = []
    for i, c in enumerate(clips):
        out = tmp / f"p{i}.mp4"
        ini = recorte_inicio if (i == 0 and recorte_inicio > 0) else 0.0
        ss = ["-ss", str(ini)] if ini else []
        if recorte_final > 0:
            largo = duracion(c) - ini - recorte_final
            if largo > 1:
                ss += ["-t", f"{largo:.2f}"]
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1")
        if _tiene_audio(c):
            cmd = ["ffmpeg", "-y", *ss, "-i", c, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "20", "-c:a", "aac", "-ar", "44100", "-ac", "2", str(out)]
        else:
            cmd = ["ffmpeg", "-y", *ss, "-i", c, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                   "-vf", vf, "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                   "-c:a", "aac", str(out)]
        _run(cmd)
        partes.append(out)
    if len(partes) == 1:
        return partes[0]
    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file '{p.as_posix()}'\n" for p in partes), encoding="utf-8")
    base = tmp / "base.mp4"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(base)])
    return base


def _subtitulos(voz: str) -> list[tuple[float, float, str]]:
    """Transcribe tu voz con faster-whisper (opcional). Devuelve trozos de 3 palabras."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return []
    model = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="auto", compute_type="int8")
    segs, _ = model.transcribe(voz, language="es", word_timestamps=True)
    palabras = [w for s in segs for w in (s.words or [])]
    trozos = []
    for i in range(0, len(palabras), 3):
        grupo = palabras[i:i + 3]
        trozos.append((grupo[0].start, grupo[-1].end, "".join(w.word for w in grupo).strip().upper()))
    return trozos


def _drawtext(fuente: str, textfile: Path, size: int, y: str, inicio: float | None = None,
              fin: float | None = None, box: bool = True, color: str = "white") -> str:
    f = (f"drawtext=fontfile='{_esc(fuente)}':textfile='{_esc(textfile)}':fontsize={size}:"
         f"fontcolor={color}:x=(w-text_w)/2:y={y}:borderw=3:bordercolor=black@0.9")
    if box:
        f += ":box=1:boxcolor=black@0.45:boxborderw=18"
    if inicio is not None:
        f += f":enable='between(t,{inicio:.2f},{fin:.2f})'"
    return f


def editar(clips: list[str], salida: str | Path, gancho: str = "", voz: str | None = None,
           recorte_inicio: float = 0.0, subtitulos: bool = True, etiqueta_ia: bool = True,
           recorte_final: float = 0.0) -> Path:
    if not shutil.which("ffmpeg"):
        raise SystemExit("Instala ffmpeg y agrégalo al PATH")
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    fuente = _fuente()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        base = _base([str(c) for c in clips], recorte_inicio, tmp, recorte_final)
        dur_base = duracion(base)
        dur = max(dur_base, duracion(voz) + 0.4) if voz else dur_base

        filtros = []
        # Gancho: líneas centradas, cada una con su propio drawtext
        if gancho:
            lineas = textwrap.wrap(gancho, width=18)[:4]
            for i, linea in enumerate(lineas):
                tf = tmp / f"g{i}.txt"
                tf.write_text(linea, encoding="utf-8")
                filtros.append(_drawtext(fuente, tf, 78, f"h*0.20+{i * 105}", 0, 2.5))
        if etiqueta_ia:
            tf = tmp / "ia.txt"
            tf.write_text("Contenido generado con IA", encoding="utf-8")
            filtros.append(_drawtext(fuente, tf, 30, "h*0.045", box=True))
        if voz and subtitulos:
            for j, (a, b, txt) in enumerate(_subtitulos(voz)):
                if a < 2.5:      # no tapar el gancho
                    a = max(a, 2.5)
                    if b <= a:
                        continue
                tf = tmp / f"s{j}.txt"
                tf.write_text(txt, encoding="utf-8")
                filtros.append(_drawtext(fuente, tf, 64, "h*0.70", a, b, color="yellow"))
        vf = ",".join(filtros) if filtros else "null"

        cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(base)]
        if voz:
            cmd += ["-i", str(voz), "-filter_complex",
                    f"[0:v]{vf}[v];[0:a]volume=0.15[a0];[1:a]volume=1.0,aresample=44100[a1];"
                    f"[a0][a1]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5[a]",
                    "-map", "[v]", "-map", "[a]"]
        else:
            cmd += ["-vf", vf, "-map", "0:v", "-map", "0:a"]
        cmd += ["-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(salida)]
        _run(cmd)
    return salida


def editar_video(video_id: int, recorte_inicio: float = 0.0, extra_clips: list[str] | None = None,
                 recorte_final: float = 0.8) -> Path:
    v = db.query("SELECT * FROM videos WHERE id=?", (video_id,))
    if not v:
        raise SystemExit(f"No existe el video {video_id}")
    v = v[0]
    if not v["clip_path"]:
        raise SystemExit("Este video no tiene clip. Usa `clip` para registrar el que bajaste de Flow, o `generar`.")
    clips = [v["clip_path"], *(extra_clips or [])]
    salida = OUTPUT_DIR / v["fecha_plan"] / f"{v['horario'].replace(':', '')}_video{video_id}.mp4"
    editar(clips, salida, gancho=v["gancho"] or "", voz=v["voz_path"], recorte_inicio=recorte_inicio,
           recorte_final=recorte_final)
    db.actualizar("videos", video_id, final_path=str(salida), estado="editado")
    return salida


def energizar(video: str | Path, salida: str | Path, cortes: list[float] | None = None,
              fuerza: float = 0.14, vol_whoosh: float = 0.5, etiqueta_ia: bool = True) -> Path:
    """Modo dinámico: zoom de golpe (punch-in) + 'whoosh' en el segundo 0 y en cada corte.

    Interrupciones de patrón cada 2-4 s = más retención. `cortes` en segundos (además del 0).
    """
    salida = Path(salida)
    marcas = [0.0] + sorted(cortes or [])
    # zoom que decae en 0.35 s después de cada marca
    z = "+".join(f"{fuerza}*max(0,1-(t-{c:.2f})/0.35)*gte(t,{c:.2f})" for c in marcas)
    vf = (f"scale=w='trunc(iw*(1+{z})/2)*2':h='trunc(ih*(1+{z})/2)*2':eval=frame,"
          f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2,setsar=1")
    with tempfile.TemporaryDirectory() as td:
        if etiqueta_ia:  # la etiqueta va DESPUÉS del zoom para que nunca se corte
            tf = Path(td) / "ia.txt"
            tf.write_text("Contenido generado con IA", encoding="utf-8")
            vf += "," + _drawtext(_fuente(), tf, 30, "h*0.045", box=True)
        w = Path(td) / "whoosh.wav"
        _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=d=0.45:c=pink:a=0.9",
              "-af", "highpass=f=600,lowpass=f=5000,afade=t=in:d=0.25,afade=t=out:st=0.25:d=0.2,"
                     "aformat=channel_layouts=stereo:sample_rates=44100", str(w)])
        entradas = ["-i", str(video)]
        mix = []
        for i, c in enumerate(marcas):
            entradas += ["-i", str(w)]
            d = int(max(c - 0.15, 0) * 1000)
            mix.append(f"[{i + 1}:a]adelay={d}|{d},volume={vol_whoosh}[w{i}]")
        n = len(marcas)
        fc = (f"[0:v]{vf}[v];" + ";".join(mix) + ";" + "[0:a]" + "".join(f"[w{i}]" for i in range(n)) +
              f"amix=inputs={n + 1}:duration=first:normalize=0[a]")
        _run(["ffmpeg", "-y", *entradas, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
              "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(salida)])
    return salida


def montaje(segmentos: list[dict], salida: str | Path, musica_vol: tuple[float, float] = (0.10, 0.32),
            punch: bool = True) -> Path:
    """Video largo (~30 s) con varios ángulos. Cada segmento:
    {"src": ruta (mp4 o jpg), "ini": s, "dur": s, "voz": bool (usar audio original), "texto": str, "zoom": 1.0}
    - voz=False: se silencia el clip y suena la música más fuerte (B-roll).
    - zoom>1: recorte al centro = "otro ángulo" del mismo clip.
    """
    from .fotos import musica
    salida = Path(salida)
    fuente = _fuente()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        partes, t, tramos_voz, cortes = [], 0.0, [], []
        for i, s in enumerate(segmentos):
            z = s.get("zoom", 1.0)
            vf = (f"scale={int(W * z)}:{int(H * z)}:force_original_aspect_ratio=increase,"
                  f"crop={W}:{H},fps={FPS},setsar=1")
            txt = ""
            if s.get("texto"):
                tf = tmp / f"t{i}.txt"
                tf.write_text(s["texto"], encoding="utf-8")
                txt = "," + _drawtext(fuente, tf, 72, "h*0.72", 0.15, s["dur"])
            vf += txt
            out = tmp / f"s{i}.mp4"
            es_img = str(s["src"]).lower().endswith((".jpg", ".jpeg", ".png"))
            if es_img:
                vf = (f"scale=1400:-1,zoompan=z='min(1+0.002*on,1.15)':d={int(s['dur'] * FPS)}:s={W}x{W}:fps={FPS},"
                      f"pad={W}:{H}:0:(oh-ih)/2:color=white,setsar=1" + txt)
                cmd = ["ffmpeg", "-y", "-loop", "1", "-t", str(s["dur"]), "-i", s["src"],
                       "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-vf", vf, "-t", str(s["dur"]),
                       "-map", "0:v", "-map", "1:a"]
            elif s.get("voz"):
                cmd = ["ffmpeg", "-y", "-ss", str(s.get("ini", 0)), "-t", str(s["dur"]), "-i", s["src"],
                       "-vf", vf, "-af", "aresample=44100,aformat=channel_layouts=stereo"]
            else:
                cmd = ["ffmpeg", "-y", "-ss", str(s.get("ini", 0)), "-t", str(s["dur"]), "-i", s["src"],
                       "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-vf", vf, "-t", str(s["dur"]),
                       "-map", "0:v", "-map", "1:a"]
            _run(cmd + ["-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", str(out)])
            partes.append(out)
            if s.get("voz"):
                tramos_voz.append((t, t + s["dur"]))
            t += s["dur"]
            cortes.append(t)
        lista = tmp / "l.txt"
        lista.write_text("".join(f"file '{p.as_posix()}'\n" for p in partes), encoding="utf-8")
        base = tmp / "base.mp4"
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c:v", "copy", "-c:a", "aac", str(base)])
        m = musica(tmp / "m.m4a", t)
        cond = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in tramos_voz) or "0"
        vol = f"if({cond},{musica_vol[0]},{musica_vol[1]})"
        mezcla = tmp / "mezcla.mp4"
        _run(["ffmpeg", "-y", "-i", str(base), "-i", str(m), "-filter_complex",
              f"[1:a]volume='{vol}':eval=frame[mu];[0:a][mu]amix=inputs=2:duration=first:normalize=0,"
              f"loudnorm=I=-14:TP=-1.5[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", str(mezcla)])
        if punch:
            energizar(mezcla, salida, cortes[:-1], fuerza=0.08, vol_whoosh=0.35)
        else:
            shutil.copy(mezcla, salida)
    return salida
