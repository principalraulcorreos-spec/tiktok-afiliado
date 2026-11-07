import sys, subprocess, tempfile
from pathlib import Path
sys.path.insert(0, '/home/claude/tiktok_afiliado')
from afiliado.rapido import tramos_auto, armar
from afiliado.editor import _drawtext, _fuente, duracion

U = '/mnt/user-data/uploads/Downloads/Cortinas_Blackout'
OUT = Path('/home/claude/cortinas/out'); OUT.mkdir(exist_ok=True)
base = OUT / 'base.mp4'
clips = [(f'{U}/clips/cb_clip1b.mp4', tramos_auto(8)), (f'{U}/clips/cb_clip2.mp4', tramos_auto(8)),
         (f'{U}/clips/cb_clip3.mp4', tramos_auto(8))]
if not base.exists(): armar(clips, base, gancho='', etiqueta_ia=False, whoosh=False)
# --- quitar silencios (pausas de voz), dejando 0.15 s de aire a cada lado ---
QUITAR = [(1.81, 2.52), (3.85, 4.10), (6.74, 7.42), (10.69, 11.27)]
corte = OUT / 'base_cut.mp4'
D0 = duracion(base)
keep, t = [], 0.0
for a, b in QUITAR:
    keep.append((t, a)); t = b
keep.append((t, D0))
fc = ''.join(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={max(b-a-0.02,0)}:d=0.02[a{i}];" for i, (a, b) in enumerate(keep))
fc += ''.join(f"[v{i}][a{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=1:a=1[v][a]"
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(base), '-filter_complex', fc, '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-c:a', 'aac', str(corte)], check=True)
def m(t):
    """tiempo original -> tiempo en el video recortado"""
    r = 0.0
    for a, b in QUITAR:
        if t >= b: r += b - a
        elif t > a: return a - r
    return t - r
base = corte
D = duracion(base); print('base recortada', D0, '->', D)

# Textos: (texto, inicio, fin, tamaño, y)
textos = [("¿TE DESPIERTA", 0.0, 2.4, 96, "h*0.60"), ("EL SOL?", 0.0, 2.4, 96, "h*0.60+120"),
          ("TELA TRIPLE CAPA", 7.95, 10.3, 84, "h*0.70"),
          ("AÍSLAN EL CALOR", 12.95, 15.6, 84, "h*0.70"),
          ("2 PANELES · 10 COLORES", 15.9, 18.35, 70, "h*0.70"),
          ("¡HOY EN OFERTA!", 18.45, 21.1, 96, "h*0.68"),
          ("CARRITO NARANJA ↓", 21.15, D0, 84, "h*0.74")]
S = f'{U}/sfx'
sfx0 = [('cam_shutter.wav', 0.0, 0.0, 0.8, 0.8),
       ('riser.wav', 3.03, 4.6, 1.5, 0.5),
       ('braams.wav', 4.03, 0.0, 2.0, 0.35),
       ('whoosh1.wav', 6.35, 0.0, 1.4, 1.0),
       ('cam_shutter.wav', 7.75, 0.0, 0.8, 0.7),
       ('cam_shutter.wav', 12.75, 0.0, 0.8, 0.7),
       ('whoosh2.wav', 15.03, 2.6, 1.2, 0.6),
       ('melodic.wav', 17.55, 0.0, 2.0, 0.7),
       ('ring.mp3', 20.65, 0.0, 1.2, 0.35)]

textos = [(t, m(a), (D if b >= D0 - 0.01 else m(b)), sz, y) for t, a, b, sz, y in textos]
sfx = [(f, m(t0), ss, du, v) for f, t0, ss, du, v in sfx0]
print(textos); print(sfx)
fuente = _fuente()
with tempfile.TemporaryDirectory() as td:
    td = Path(td); f = []
    for i, (t, a, b, sz, y) in enumerate(textos):
        tf = td / f't{i}.txt'; tf.write_text(t, encoding='utf-8')
        f.append(_drawtext(fuente, tf, sz, y, a, b))
    tf = td / 'ia.txt'; tf.write_text('Contenido generado con IA', encoding='utf-8')
    f.append(_drawtext(fuente, tf, 30, 'h*0.045', box=True))
    entradas = ['-i', str(base)]; mix = ''
    for i, (arch, t0, ss, du, vol) in enumerate(sfx):
        entradas += ['-ss', str(ss), '-t', str(du), '-i', f'{S}/{arch}']
        d = int(t0 * 1000)
        mix += (f'[{i+1}:a]aformat=sample_rates=44100:channel_layouts=stereo,afade=t=out:st={max(du-0.3,0)}:d=0.3,'
                f'volume={vol},adelay={d}|{d}[s{i}];')
    mix += '[0:a]volume=1.0[v];[v]' + ''.join(f'[s{i}]' for i in range(len(sfx))) + \
           f'amix=inputs={len(sfx)+1}:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]'
    salida = OUT / 'Cortinas_Blackout_FINAL.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *entradas, '-filter_complex', f"[0:v]{','.join(f)}[vv];{mix}",
                    '-map', '[vv]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt',
                    'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(salida)], check=True)
    print(salida, duracion(salida))
