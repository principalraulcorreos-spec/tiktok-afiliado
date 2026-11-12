"""Modo "REAL + REACCIÓN" (nov-2026): el producto sale SOLO en material real (videos y fotos de la ficha)
y una presentadora IA con fondo verde reacciona en una esquina. La IA nunca dibuja el producto.

Uso:
    python -m afiliado.secuencia timeline.json
    # o desde Python: armar(timeline_dict)

timeline.json (rutas relativas a la carpeta del timeline):
{
  "salida": "FINAL.mp4",
  "escenas": [                                   # fondo a pantalla completa, en orden
    {"tipo": "video", "src": "videos/demo.mp4", "ini": 2.0, "dur": 1.6, "vel": 1.0, "punch": true,
     "franja": [0.82, 0.95]},                    # franja: difumina subtítulos quemados del vendedor
    {"tipo": "foto",  "src": "fotos/1.jpg", "dur": 1.0, "mov": "in"},          # mov: in | out | izq | der
    {"tipo": "recorte", "src": "recortes/1.png", "dur": 1.2, "fondo": "fotos/1.jpg"}  # producto sin fondo que entra con rebote
  ],
  "presentadora": {                              # opcional
    "pos": "arriba_derecha",                     # arriba_derecha | arriba_izquierda | abajo_centro
    "ancho": 0.42,                               # fracción del ancho del video
    "verde": "0x00FF00", "similitud": 0.16, "suavizado": 0.08,
    "recorte_y": [0.0, 0.62],                    # parte del clip que se usa (0=arriba, 1=abajo): busto
    "desvanecer": 0.12,                          # fracción inferior del busto que se desvanece (0 = corte recto)
    "clips": [{"src": "presentadora/r1.mp4", "ini": 0.0, "dur": 3.0, "en": 0.0, "audio": true}]
  },
  "voz": "voz.wav",                              # narración (Gemini TTS de AI Studio). Con voz, la presentadora va muda
  "narracion": "texto exacto de la voz",         # → captions sincronizados automáticos
  "voz_en": 0.0, "ajustar_a_voz": true,          # las escenas se estiran/encogen para durar lo que la voz
  "textos": [{"t": "¿TE DESPIERTA EL SOL?", "ini": 0.0, "fin": 1.8, "estilo": "gancho"},
             {"t": "triple capa", "ini": 5.0, "fin": 6.4, "estilo": "caption"}],
  "frases": [{"t": "Mira lo que encontré para tu recámara", "ini": 0.3, "fin": 2.6}],  # → captions automáticos
  "sfx_cortes": true,                            # whoosh/pop en cada corte (generados o de la carpeta sfx)
  "sfx_dir": "",                                 # carpeta con whoosh*.wav, pop.wav, braams.wav (opcional)
  "musica": "", "musica_vol": 0.12
}

Reglas (de la investigación de videos ganadores, ver guia/MODO_REAL_REACCION.md):
- Lo más impactante del producto en el cuadro 0 (resultado primero).
- Cortes cada 1.0-1.6 s; ninguna foto quieta: todas con movimiento.
- >= 50 % del video con movimiento real (videos de la ficha + presentadora).
- Captions chicos sincronizados a la voz; textos grandes solo en el gancho y el CTA.
"""
from __future__ import annotations

import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

W, H, FPS = 1080, 1920, 30
AQUI = Path(__file__).resolve().parent
FUENTE_LOCAL = AQUI / "assets" / "Poppins-Bold.ttf"


# --------------------------------------------------------------------------- utilidades
def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falló:\n" + " ".join(map(str, cmd))[:600] + "\n" + r.stderr[-2500:])


def _dur(p) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def _tiene_audio(p) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def _medir_lufs(wav: str | Path, cadenas: list[str]) -> list[float] | None:
    """Sonoridad integrada (LUFS, ebur128 = la misma medida del QA) de `wav` pasado por cada una de `cadenas`,
    en UNA sola llamada a ffmpeg (asplit). None si falla o si es silencio total."""
    n = len(cadenas)
    ramas = [f"[0:a]asplit={n}" + "".join(f"[r{k}]" for k in range(n))] if n > 1 else []
    ramas += [f"[{'r%d' % k if n > 1 else '0:a'}]{c},ebur128=framelog=quiet[m{k}]" for k, c in enumerate(cadenas)]
    salidas = [x for k in range(n) for x in ("-map", f"[m{k}]", "-f", "null", "-")]
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-v", "info", "-i", str(wav),
                        "-filter_complex", ";".join(ramas), *salidas], capture_output=True, text=True)
    res = re.findall(r"Parsed_ebur128_(\d+) @[^\]]*\] Summary:\s*\n(?:.*\n)*?\s*I:\s+(-?[\d.]+) LUFS", r.stderr)
    if r.returncode != 0 or len(res) != n:
        return None
    i = [float(v) for _, v in sorted(res, key=lambda x: int(x[0]))]   # ffmpeg imprime los resúmenes al revés
    return i if min(i) > -70 else None


def _render_mezcla(entradas: list[str], mezcla: list[str], etiqueta: str, wav: Path) -> float | None:
    """Renderiza la mezcla de audio `etiqueta` a `wav` (solo audio, sin demuxar el video) y de paso mide su
    sonoridad original con ebur128 (pasada 1, sin costo extra). Devuelve los LUFS o None."""
    solo_audio = [x for a in entradas for x in (("-vn", a) if a == "-i" else (a,))]
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-nostats", "-v", "info", *solo_audio, "-filter_complex",
                        ";".join([*mezcla, f"{etiqueta}ebur128=framelog=quiet[wavm]"]), "-map", "[wavm]",
                        "-c:a", "pcm_f32le", str(wav)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falló al mezclar el audio:\n" + r.stderr[-2500:])
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(i[-1]) if i and float(i[-1]) > -70 else None


def _loudnorm_2p(wav: str | Path, objetivo: float = -14.0, tp: float = -1.5, i0: float | None = None) -> str:
    """Normalización en 2 pasadas sobre la mezcla ya renderizada `wav`: devuelve ganancia fija + limitador.
    En 1 pasada (loudnorm dinámico) los videos con mucho silencio y efectos quedaban en −16.6 LUFS: los efectos
    son casi puro pico y el modo lineal de loudnorm no sube la ganancia si un pico rebasa el true peak.
    Pasada 1: sonoridad original (`i0`, o se mide). Pasada 2: prueba 3 ganancias con el limitador a la vez
    (el limitador se come parte de la ganancia) e interpola la que da el objetivo. Si falla, regresa el loudnorm de antes."""
    base = f"loudnorm=I={objetivo}:TP={tp}"
    lim = 10 ** ((tp - 0.5) / 20)              # 0.5 dB de margen: alimiter mide pico de muestra, no true peak

    def cadena(g):
        return f"volume={g:.2f}dB,alimiter=limit={lim:.4f}:attack=2:release=50:level=0,aresample=44100"
    if i0 is None:
        m = _medir_lufs(wav, ["anull"])
        if m is None:
            return base
        i0 = m[0]
    gs = [objetivo - i0 + extra for extra in (0, 3, 6)]
    ii = _medir_lufs(wav, [cadena(g) for g in gs])
    if ii is None:
        return base
    g = gs[-1]                                 # si ni con +6 dB llega, se queda con la más alta
    for (ga, ia), (gb, ib) in zip(zip(gs, ii), zip(gs[1:], ii[1:])):
        if ia >= objetivo:
            g = ga
            break
        if ia < objetivo <= ib:
            g = ga + (gb - ga) * (objetivo - ia) / (ib - ia)
            break
    return cadena(g)


def _esc(p) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def _fuente() -> str:
    cands = [FUENTE_LOCAL]
    if platform.system() == "Windows":
        cands += [Path("C:/Windows/Fonts/arialbd.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf")]
    cands += [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")]
    for c in cands:
        if c.exists():
            return str(c)
    raise SystemExit("No encontré fuente .ttf")


ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS)]

# fondo desenfocado + primer plano ajustado (para material que no es 9:16)
_FIT = (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:2,"
        f"eq=brightness=-0.06[bg];[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2")


def _es_vertical(p) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try:
        w, h = map(int, r.stdout.strip().split(",")[:2])
        return h / w > 1.7   # 9:16 real: llena la pantalla sin perder casi nada
    except Exception:
        return False


# --------------------------------------------------------------------------- escenas (fondo)
def _escena_video(e: dict, out: Path) -> None:
    """Tramo de video real. Nunca recorta los lados: si no es 9:16 va completo sobre fondo desenfocado.
    `franja`: [y0, y1] (fracción de alto) que se difumina para tapar subtítulos quemados del vendedor."""
    vel = float(e.get("vel", 1.0))
    dur = float(e["dur"])
    base = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" if _es_vertical(e["src"])
            else _FIT)
    punch = ""
    if e.get("punch"):  # zoom de golpe que se relaja en 0.35 s (el cuadro completo, sin perder bordes al final)
        punch = (",scale=w='trunc(iw*(1+0.10*max(0\\,1-t/0.35))/2)*2':h='trunc(ih*(1+0.10*max(0\\,1-t/0.35))/2)*2'"
                 f":eval=frame,crop={W}:{H}")
    franja = ""
    if e.get("franja"):
        y0, y1 = e["franja"]
        hh = int(H * (y1 - y0)) // 2 * 2
        franja = (f",split[m][f];[f]crop={W}:{hh}:0:{int(H * y0)},boxblur=22:4[fb];"
                  f"[m][fb]overlay=0:{int(H * y0)}")
    vf = (f"[0:v]setpts=(PTS-STARTPTS)/{vel},{base}{franja}{punch},fps={FPS},setsar=1,format=yuv420p[v]")
    _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{e.get('ini', 0)}", "-t", f"{dur * vel:.3f}", "-i", str(e["src"]),
          "-filter_complex", vf, "-map", "[v]", "-an", "-t", f"{dur:.3f}", *ENC, str(out)])


def _escena_foto(e: dict, out: Path) -> None:
    """Foto de la ficha COMPLETA (nunca se recorta: suelen traer texto en los bordes), centrada sobre un
    fondo muy desenfocado y oscuro, con zoom suave de la foto entera (mov: in | out) o deslizamiento (izq | der)."""
    dur = float(e["dur"])
    n = max(int(dur * FPS), 1)
    mov = e.get("mov", "in")
    k = {"in": f"(0.94+0.08*t/{dur})", "out": f"(1.02-0.08*t/{dur})"}.get(mov, "0.98")
    dx = {"izq": f"+40-80*t/{dur}", "der": f"-40+80*t/{dur}"}.get(mov, "")
    # con presentadora arriba, la foto baja a la zona libre (y >= 720) para que ella no tape su texto
    y = f"max((H-h)/2-60\\,{int(e['debajo'])})" if e.get("debajo") else "(H-h)/2-60"
    ancho = int(e.get("ancho_foto", W))
    fc = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=60:4,"
          f"eq=brightness=-0.28:saturation=0.8,loop=-1:1,trim=end_frame={n},setpts=N/{FPS}/TB[bg];"
          f"[b]scale={ancho}:-2,loop=-1:1,trim=end_frame={n},setpts=N/{FPS}/TB,"
          f"scale=w='trunc({ancho}*{k}/2)*2':h=-2:eval=frame[fg];"
          f"[bg][fg]overlay=x='(W-w)/2{dx}':y='{y}':shortest=1,setsar=1,fps={FPS},format=yuv420p[v]")
    _run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", f"{dur + 0.5}", "-i", str(e["src"]),
          "-filter_complex", fc, "-map", "[v]", "-frames:v", str(n), *ENC, str(out)])


def _escena_recorte(e: dict, out: Path) -> None:
    """PNG sin fondo (rembg) que entra desde abajo con rebote y queda flotando suave."""
    dur = float(e["dur"])
    fondo = e.get("fondo") or e["src"]
    yexp = ("(H-h)/2-60+ if(lt(t,0.45), (H)*pow(1-t/0.45,2)*cos(t*14), 18*sin(t*3))")
    fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:3,"
          f"eq=brightness=-0.15:saturation=1.2,loop=-1:1,trim=duration={dur},setpts=PTS-STARTPTS,fps={FPS}[bg];"
          f"[1:v]scale=900:-1[p];[bg][p]overlay=x=(W-w)/2:y='{yexp}':shortest=1,setsar=1,format=yuv420p[v]")
    _run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", f"{dur}", "-i", str(fondo),
          "-loop", "1", "-t", f"{dur}", "-i", str(e["src"]), "-filter_complex", fc, "-map", "[v]",
          "-t", f"{dur}", *ENC, str(out)])


def recortar_fondo(fotos: list[str | Path], carpeta: str | Path) -> list[Path]:
    """Quita el fondo con rembg (pip install rembg onnxruntime). Devuelve los PNG."""
    from rembg import remove
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    outs = []
    for f in fotos:
        o = carpeta / (Path(f).stem + ".png")
        if not o.exists():
            o.write_bytes(remove(Path(f).read_bytes()))
        outs.append(o)
    return outs


# --------------------------------------------------------------------------- sonido
def _sfx_generados(tmp: Path) -> dict[str, Path]:
    s = {}
    s["whoosh"] = tmp / "whoosh.wav"
    _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anoisesrc=d=0.4:c=pink:a=0.9", "-af",
          "highpass=f=700,lowpass=f=6000,afade=t=in:d=0.18,afade=t=out:st=0.18:d=0.22,"
          "aformat=channel_layouts=stereo:sample_rates=44100", str(s["whoosh"])])
    s["pop"] = tmp / "pop.wav"
    _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
          "aevalsrc='0.8*sin(2*PI*(900-700*t/0.09)*t)*exp(-t*38)':s=44100:d=0.12", "-af",
          "aformat=channel_layouts=stereo:sample_rates=44100", str(s["pop"])])
    s["boom"] = tmp / "boom.wav"
    _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
          "aevalsrc='0.9*sin(2*PI*(110-60*t)*t)*exp(-t*3.5)':s=44100:d=1.2", "-af",
          "lowpass=f=400,aformat=channel_layouts=stereo:sample_rates=44100", str(s["boom"])])
    return s


def _sfx_carpeta(d: str, gen: dict[str, Path]) -> dict[str, list[Path]]:
    out = {k: [v] for k, v in gen.items()}
    if d and Path(d).exists():
        for k, pat in (("whoosh", "whoosh*"), ("pop", "cam_shutter*"), ("boom", "braams*")):
            f = sorted(Path(d).glob(pat))
            if f:
                out[k] = f
    return out


# --------------------------------------------------------------------------- textos
def captions_de_frase(frase: str, ini: float, fin: float, palabras: int = 3) -> list[dict]:
    """Parte una frase hablada en trozos de 2-3 palabras repartidos en [ini, fin]."""
    w = frase.split()
    trozos = [" ".join(w[i:i + palabras]) for i in range(0, len(w), palabras)]
    if not trozos:
        return []
    paso = (fin - ini) / len(trozos)
    return [{"t": t, "ini": ini + i * paso, "fin": ini + (i + 1) * paso, "estilo": "caption"}
            for i, t in enumerate(trozos)]


def _frases_de_voz(voz: str, texto: str, umbral: float = 0.22) -> list[tuple[float, float]]:
    """Ubica cada oración del guion dentro del audio usando las pausas (silencedetect)."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", voz, "-af", f"silencedetect=n=-35dB:d={umbral}", "-f", "null", "-"],
                       capture_output=True, text=True)
    import re
    ini = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    fin = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    D = _dur(voz)
    habla, t = [], (fin[0] if ini and ini[0] < 0.05 and fin else 0.0)
    for a_, b_ in zip(ini, fin):
        if a_ > t + 0.15:
            habla.append((t, a_))
        t = b_
    if D > t + 0.15:
        habla.append((t, D))
    return habla


def captions_de_voz(voz: str, texto: str, offset: float = 0.0, palabras: int = 3) -> list[dict]:
    """Captions de 2-3 palabras sincronizados a la narración: reparte las palabras entre los tramos con voz
    en proporción a su duración (sin servicios externos)."""
    habla = _frases_de_voz(voz, texto)
    w = texto.split()
    if not habla or not w:
        return []
    total = sum(b - a for a, b in habla)
    trozos = [" ".join(w[i:i + palabras]) for i in range(0, len(w), palabras)]
    # tiempo "hablado" acumulado -> tiempo real
    def real(x):
        acc = 0.0
        for a, b in habla:
            if acc + (b - a) >= x:
                return a + (x - acc)
            acc += b - a
        return habla[-1][1]
    pesos = [len(t) + 2 for t in trozos]
    P, acc, out = sum(pesos), 0.0, []
    for t, p in zip(trozos, pesos):
        x0, x1 = total * acc / P, total * (acc + p) / P
        acc += p
        out.append({"t": t, "ini": offset + real(x0), "fin": offset + real(x1) - 0.02, "estilo": "caption"})
    return out


FLECHA = "↓"


def _fuente_simbolos() -> str:
    for c in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/seguisym.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(c).exists():
            return c
    return _fuente()


def _drawtext(fuente: str, tmp: Path, nombre: str, texto: str, a: float, b: float, estilo: str) -> list[str]:
    """Una línea = un drawtext (centrado de verdad). Efecto pop: 70 % → 100 % en 0.12 s."""
    if estilo == "gancho":
        size, yc, borde, ancho = 92, 0.60, 6, 16
    elif estilo == "cta":
        size, yc, borde, ancho = 84, 0.70, 6, 16
    else:  # caption chico al centro, como los videos que venden
        size, yc, borde, ancho = 58, 0.62, 5, 22
    flecha = FLECHA in texto
    limpio = texto.replace(FLECHA, "").strip()
    n = max(1, math.ceil(len(limpio) / ancho))
    lineas = textwrap.wrap(limpio, max(math.ceil(len(limpio) / n) + 2, 6))  # líneas balanceadas
    salto = int(size * 1.18)
    y0 = f"h*{yc}-{salto * len(lineas) / 2:.0f}"
    fs = f"{size}*min(1\\,0.7+0.3*(t-{a:.2f})/0.12)"
    out = []
    for i, ln in enumerate(lineas):
        tf = tmp / f"{nombre}_{i}.txt"
        tf.write_text(ln, encoding="utf-8")
        out.append(f"drawtext=fontfile='{_esc(fuente)}':textfile='{_esc(tf)}':fontsize='{fs}':fontcolor=white:"
                   f"borderw={borde}:bordercolor=black:x=(w-text_w)/2:y={y0}+{i * salto}+({size}-text_h)/2:"
                   f"enable='between(t,{a:.2f},{b:.2f})'")
    if flecha:
        tf = tmp / f"{nombre}_f.txt"
        tf.write_text(FLECHA, encoding="utf-8")
        # flecha que rebota hacia abajo-izquierda (donde está el carrito)
        out.append(f"drawtext=fontfile='{_esc(_fuente_simbolos())}':textfile='{_esc(tf)}':fontsize={int(size * 1.6)}:"
                   f"fontcolor=0xFF7A00:borderw={borde}:bordercolor=black:x=w*0.12:"
                   f"y={y0}+{len(lineas) * salto + 10}+18*abs(sin(t*7)):enable='between(t,{a:.2f},{b:.2f})'")
    return out


# --------------------------------------------------------------------------- presentadora
def color_fondo(src: str, t: float = 1.0) -> str:
    """Color real del fondo verde (promedio de las 2 esquinas de arriba). Veo no da #00FF00 puro."""
    vals = []
    for x in ("8", "iw-48"):
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", src, "-frames:v", "1", "-vf",
                            f"crop=40:40:{x}:8,scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True)
        if len(r.stdout) >= 3:
            vals.append(r.stdout[:3])
    if not vals:
        return "0x00FF00"
    rgb = [sum(v[i] for v in vals) // len(vals) for i in range(3)]
    return "0x%02X%02X%02X" % tuple(rgb)


def _desvanecer(entrada: str, salida: str, frac: float, n: int) -> list[str]:
    """Desvanece la parte inferior del busto (alfa 1 → 0 en la fracción `frac` de abajo) para que no se vea
    el corte recto del recorte. La rampa se calcula UNA vez (1 cuadro en bucle) y se multiplica con el alfa,
    así casi no suma tiempo de render. Con frac <= 0 solo pasa la entrada."""
    if frac <= 0:
        return [f"{entrada}null{salida}"]
    return [f"color=c=black:s=8x512:r={FPS}:d=1,format=gray,geq=lum='255*clip((H-1-Y)/(H*{frac:.4f})\\,0\\,1)',"
            f"trim=end_frame=1,loop=-1:1:0,setpts=N/{FPS}/TB[gr{n}]",
            f"{entrada}split[pc{n}][pa{n}]", f"[pa{n}]alphaextract[al{n}]",
            f"[gr{n}][al{n}]scale2ref=w=iw:h=ih[gs{n}][ar{n}]",
            f"[ar{n}][gs{n}]blend=all_mode=multiply:shortest=1[am{n}]",
            f"[pc{n}][am{n}]alphamerge{salida}"]


def _pos(pos: str, pw: int, ph: int) -> tuple[str, str]:
    m = 36
    if pos == "arriba_izquierda":
        return f"{m}", "200"
    if pos == "abajo_centro":
        return "(W-w)/2", "H-h-260"
    return f"W-w-{m}", "200"   # arriba_derecha: debajo de la barra superior de TikTok


# --------------------------------------------------------------------------- armado
def armar(tl: dict, base_dir: str | Path = ".") -> Path:
    if not shutil.which("ffmpeg"):
        raise SystemExit("Instala ffmpeg")
    bd = Path(base_dir)
    R = lambda p: str((bd / p).resolve()) if p and not Path(p).is_absolute() else p  # noqa: E731
    salida = Path(R(tl.get("salida", "FINAL.mp4")))
    salida.parent.mkdir(parents=True, exist_ok=True)
    fuente = _fuente()

    pres0 = tl.get("presentadora")
    if pres0 and not tl.get("voz") and all(c.get("en", "auto") == "auto" for c in pres0["clips"]):
        # la presentadora narra: sus clips van seguidos y el video dura lo que ella habla
        t, clips = float(pres0.get("inicio", 0.0)), []
        for c in pres0["clips"]:
            clips.append(dict(c, en=round(t, 3)))
            t += float(c["dur"])
        objetivo = t + float(tl.get("cola", 0.5))
        suma = sum(float(e["dur"]) for e in tl["escenas"])
        f = objetivo / suma
        tl = dict(tl, presentadora=dict(pres0, clips=clips),
                  escenas=[dict(e, dur=round(float(e["dur"]) * f, 2)) for e in tl["escenas"]])
        print(f"Escenas ajustadas a la presentadora: {suma:.1f} s → {objetivo:.1f} s")
    if tl.get("voz") and tl.get("ajustar_a_voz", True):
        objetivo = _dur(R(tl["voz"])) + float(tl.get("voz_en", 0)) + float(tl.get("cola", 0.7))
        suma = sum(float(e["dur"]) for e in tl["escenas"])
        f = objetivo / suma
        tl = dict(tl, escenas=[dict(e, dur=round(float(e["dur"]) * f, 2)) for e in tl["escenas"]])
        print(f"Escenas ajustadas a la voz: {suma:.1f} s → {objetivo:.1f} s")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # 1) escenas de fondo
        partes, cortes, t = [], [], 0.0
        dinamico = 0.0
        trabajos = []
        for i, e in enumerate(tl["escenas"]):
            e = dict(e, src=R(e["src"]))
            if e["tipo"] == "foto" and pres0 and pres0.get("pos", "arriba_derecha").startswith("arriba"):
                e.setdefault("debajo", 700)
                e.setdefault("ancho_foto", 1000)
            if e.get("fondo"):
                e["fondo"] = R(e["fondo"])
            trabajos.append((e, tmp / f"e{i:03d}.mp4"))
        # cada escena es un ffmpeg independiente: 2 a la vez aprovechan los núcleos que una sola deja libres
        # ("hilos_escenas": 1 = en serie, como antes). El resultado es idéntico; solo cambia el tiempo.
        hilos = max(1, int(tl.get("hilos_escenas", min(2, os.cpu_count() or 1))))
        fn = {"video": _escena_video, "foto": _escena_foto, "recorte": _escena_recorte}
        with ThreadPoolExecutor(max_workers=hilos) as pool:
            for f in [pool.submit(fn[e["tipo"]], e, o) for e, o in trabajos]:
                f.result()
        for e, o in trabajos:
            d = _dur(o)
            if e["tipo"] == "video":
                dinamico += d
            partes.append(o)
            t += d
            cortes.append(t)
        lista = tmp / "l.txt"
        lista.write_text("".join(f"file '{p.as_posix()}'\n" for p in partes), encoding="utf-8")
        fondo = tmp / "fondo.mp4"
        _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(fondo)])
        D = _dur(fondo)

        # 2) video: presentadora + textos
        entradas = ["-i", str(fondo)]
        fc, ultimo, k = [], "[0:v]", 1
        pres = tl.get("presentadora")
        pres_audio = []
        if pres:
            pw = int(W * float(pres.get("ancho", 0.42)))
            y0, y1 = pres.get("recorte_y", [0.0, 0.62])
            sim, suav = pres.get("similitud", 0.08), pres.get("suavizado", 0.03)
            fade = float(pres.get("desvanecer", 0.12))   # fracción inferior del busto que se desvanece (0 = corte recto)
            for j, c in enumerate(pres["clips"]):
                src = R(c["src"])
                verde = pres.get("verde") or color_fondo(src)
                entradas += ["-ss", f"{c.get('ini', 0)}", "-t", f"{c['dur']}", "-i", src]
                en, du = float(c["en"]), float(c["dur"])
                if en < 0:          # negativo = contado desde el final
                    en = max(D + en, 0)
                x, y = _pos(pres.get("pos", "arriba_derecha"), pw, 0)
                # entra deslizándose 0.22 s desde el borde
                lado = "-" if pres.get("pos") == "arriba_izquierda" else "+"
                xexp = f"{x}{lado}if(lt(t-{en:.2f}\\,0.22)\\,(1-(t-{en:.2f})/0.22)*{pw}\\,0)"
                # se escala ANTES del chroma: chromakey/despill trabajan sobre ~2.5× menos píxeles (−5 s de filtros
                # en un video de 18 s, medido 2026-11-11) y el verde residual del QA no cambia
                fc.append(f"[{k}:v]crop=iw:ih*{y1 - y0}:0:ih*{y0},scale={pw}:-2,chromakey={verde}:{sim}:{suav},"
                          f"despill=green,fps={FPS}[ps{j}]")
                fc += _desvanecer(f"[ps{j}]", f"[pf{j}]", fade, j)
                fc.append(f"[pf{j}]setpts=PTS-STARTPTS+{en:.3f}/TB[p{j}]")
                fc.append(f"{ultimo}[p{j}]overlay=x='{xexp}':y={y}:eof_action=pass:"
                          f"enable='between(t,{en:.2f},{en + du:.2f})'[o{j}]")
                ultimo = f"[o{j}]"
                if c.get("audio", not tl.get("voz")) and _tiene_audio(src):
                    pres_audio.append((k, en))
                k += 1
                dinamico += du * 0.5   # la presentadora cuenta como movimiento (aprox.)

        # tiempos negativos = contados desde el final (p. ej. CTA: ini -2.2, fin 0 → últimos 2.2 s)
        textos = [dict(x, ini=D + x["ini"] if x["ini"] < 0 else x["ini"],
                       fin=D + x["fin"] if x["fin"] <= 0 else x["fin"]) for x in tl.get("textos", [])]
        # captions de lo que dice la presentadora en cada clip (sincronizados con las pausas de su audio)
        if pres and not tl.get("voz"):
            for c in pres["clips"]:
                if c.get("texto"):
                    en = float(c["en"]) if float(c["en"]) >= 0 else D + float(c["en"])
                    with tempfile.TemporaryDirectory() as t2:
                        wav = Path(t2) / "a.wav"
                        _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{c.get('ini', 0)}", "-t", f"{c['dur']}",
                              "-i", R(c["src"]), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
                        textos += captions_de_voz(str(wav), c["texto"], en)
        if tl.get("voz") and tl.get("narracion"):
            textos += captions_de_voz(R(tl["voz"]), tl["narracion"], float(tl.get("voz_en", 0)))
        for f in tl.get("frases", []):
            textos += captions_de_frase(f["t"], f["ini"], f["fin"], f.get("palabras", 3))
        # captions que choquen con el gancho o el CTA: se recortan o se quitan (nunca dos textos encimados)
        grandes = [(x["ini"], x["fin"]) for x in textos if x.get("estilo") in ("gancho", "cta")]
        limpios = []
        for x in textos:
            if x.get("estilo", "caption") == "caption":
                for a_, b_ in grandes:
                    if x["ini"] < b_ and x["fin"] > a_:
                        x = dict(x, ini=max(x["ini"], b_)) if x["ini"] >= a_ else dict(x, fin=min(x["fin"], a_))
                if x["fin"] - x["ini"] < 0.25:
                    continue
            limpios.append(x)
        textos = limpios
        dt = []
        for i, tx in enumerate(textos):
            dt += _drawtext(fuente, tmp, f"t{i}", tx["t"], float(tx["ini"]), float(tx["fin"]),
                            tx.get("estilo", "caption"))
        fc.append(f"{ultimo}{','.join(dt) if dt else 'null'}[vout]")

        # 3) audio
        mezcla = []
        gen = _sfx_generados(tmp)
        sfx = _sfx_carpeta(R(tl.get("sfx_dir", "")), gen)
        a_idx = []
        for kk, en in pres_audio:
            d = int(en * 1000)
            mezcla.append(f"[{kk}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={d}|{d}[pa{kk}]")
            a_idx.append(f"[pa{kk}]")
        if tl.get("voz"):
            entradas += ["-i", R(tl["voz"])]
            d = int(float(tl.get("voz_en", 0)) * 1000)
            mezcla.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={d}|{d}[voz]")
            a_idx.append("[voz]")
            k += 1
        eventos = []
        if tl.get("sfx_cortes", True):
            eventos.append(("boom", 0.0, 0.55))
            for n, c in enumerate(cortes[:-1]):
                eventos.append((("whoosh", "pop")[n % 2], max(c - 0.12, 0), 0.45))
        for nm, t0, vol in eventos + [(s["f"], s["t"], s.get("vol", 0.6)) for s in tl.get("sfx", [])]:
            lista_f = sfx.get(nm) or [Path(R(nm))]
            f = lista_f[len(mezcla) % len(lista_f)]
            entradas += ["-i", str(f)]
            d = int(t0 * 1000)
            mezcla.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,volume={vol},adelay={d}|{d}[s{k}]")
            a_idx.append(f"[s{k}]")
            k += 1
        if tl.get("musica"):
            entradas += ["-stream_loop", "-1", "-i", R(tl["musica"])]
            mezcla.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,volume={tl.get('musica_vol', 0.12)}[mu]")
            a_idx.append("[mu]")
            k += 1
        entradas += ["-f", "lavfi", "-t", f"{D:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
        a_idx.append(f"[{k}:a]")
        mezcla.append("".join(a_idx) + f"amix=inputs={len(a_idx)}:duration=longest:normalize=0,"
                      f"atrim=0:{D:.3f}[mix]")
        # la mezcla se renderiza una vez (solo audio) → se mide → el render final solo le aplica la ganancia
        wav = tmp / "mezcla.wav"
        i0 = _render_mezcla(entradas, mezcla, "[mix]", wav)
        entradas += ["-i", str(wav)]
        mezcla = [f"[{k + 1}:a]{_loudnorm_2p(wav, i0=i0) if i0 is not None else 'loudnorm=I=-14:TP=-1.5'}[aout]"]

        _run(["ffmpeg", "-y", "-v", "error", *entradas, "-filter_complex", ";".join(fc + mezcla),
              "-map", "[vout]", "-map", "[aout]", "-t", f"{D:.3f}", "-c:v", "libx264", "-preset", "medium",
              "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
              "-movflags", "+faststart", str(salida)])

    pct = 100 * min(dinamico / D, 1) if D else 0
    print(f"✅ {salida}  {D:.1f} s  · movimiento real ≈ {pct:.0f} %  · cortes: {len(cortes) - 1}")
    if pct < 50:
        print("⚠️  Menos de 50 % de movimiento real: agrega videos de la ficha o más presentadora.")
    return salida


# --------------------------------------------------------------------------- timeline automático
def plan_auto(carpeta: str | Path, duracion: float = 22.0, paso: float = 1.3) -> dict:
    """Arma un timeline a partir de Downloads/<Producto>/{videos,fotos,recortes,presentadora}.
    Alterna tramos de video (paso s) con fotos en movimiento; el gancho es el primer tramo de video."""
    c = Path(carpeta)
    vids = sorted((c / "videos").glob("*.mp4")) if (c / "videos").exists() else []
    fotos = sorted([*c.glob("fotos/*.jp*g"), *c.glob("fotos/*.png"), *c.glob("fotos/*.webp")])
    recs = sorted(c.glob("recortes/*.png"))
    tramos = []
    for v in vids:
        d = _dur(v)
        t = 0.3
        while t + paso <= d - 0.2:
            tramos.append({"tipo": "video", "src": str(v.relative_to(c)), "ini": round(t, 2), "dur": paso})
            t += paso + 0.4
    escenas, t, i, fi, ri, mov = [], 0.0, 0, 0, 0, ["in", "der", "out", "izq"]
    while t < duracion:
        usar_video = tramos and (i < len(tramos)) and (len(escenas) % 3 != 2 or not fotos)
        if usar_video:
            e = dict(tramos[i], punch=(len(escenas) == 0 or len(escenas) % 4 == 0))
            i += 1
        elif recs and ri < len(recs) and len(escenas) % 6 == 5:
            e = {"tipo": "recorte", "src": str(recs[ri].relative_to(c)), "dur": 1.2,
                 "fondo": str(fotos[ri % len(fotos)].relative_to(c)) if fotos else None}
            ri += 1
        elif fotos:
            e = {"tipo": "foto", "src": str(fotos[fi % len(fotos)].relative_to(c)), "dur": 1.0,
                 "mov": mov[fi % 4]}
            fi += 1
        elif tramos:
            i = 0
            continue
        else:
            raise SystemExit("No hay videos ni fotos en la carpeta")
        escenas.append(e)
        t += e["dur"]
    return {"salida": "FINAL.mp4", "escenas": escenas, "sfx_cortes": True}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    p = Path(sys.argv[1])
    armar(json.loads(p.read_text(encoding="utf-8")), p.parent)
