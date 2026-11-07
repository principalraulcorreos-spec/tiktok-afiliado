import sys, subprocess, tempfile
from pathlib import Path
sys.path.insert(0, '/home/claude/tiktok_afiliado')
from afiliado.rapido import armar
from afiliado.editor import _drawtext, _fuente, duracion
C = '/home/claude/gato/clips'; S = '/mnt/user-data/uploads/Downloads/Cortinas_Blackout/sfx'
OUT = Path('/home/claude/gato/out')
def tr(lista):  # (a,b) alternando zoom
    return [(a, b, (1.0, 1.28)[i % 2], 0.5, 0.35) for i, (a, b) in enumerate(lista)]
def z2(l): return [(a, b, (1.15, 1.35)[i % 2], 0.5, 0.5) for i, (a, b) in enumerate(l)]
clips = [(f'{C}/ga_clip1.mp4', [(0, 1.1, 1.0, .5, .35), (1.1, 2.27, 1.28, .5, .35), (2.54, 3.84, 1.28, .5, .35), (4.1, 4.5, 1.28, .5, .35), (4.5, 5.4, 1.0, .5, .35), (5.4, 6.26, 1.28, .5, .35), (6.59, 7.59, 1.0, .5, .35)]),
         (f'{C}/ga_clip2.mp4', z2([(0, 1.67), (2.2, 2.66), (3.03, 3.9), (3.9, 4.78), (5.03, 6.3), (6.3, 7.5)])),
         (f'{C}/ga_clip3.mp4', tr([(0, 1.0), (1.0, 1.98), (2.58, 3.74), (4.12, 5.35), (5.74, 6.7), (6.7, 7.62)]))]
base = OUT / 'base.mp4'
if not base.exists(): armar(clips, base, gancho='', etiqueta_ia=False, whoosh=False)
D = duracion(base); print('dur', D)
c1 = sum(b - a for a, b, *_ in clips[0][1]); c2 = c1 + sum(b - a for a, b, *_ in clips[1][1])
K = D / (c2 + sum(b - a for a, b, *_ in clips[2][1]))
O = (0, c1, c2)
s = lambda k, j: K * (sum(b - a for a, b, *_ in clips[k][1][:j]) + O[k])
c1, c2 = K * c1, K * c2
T = [("¿TU COCINA", 0, s(0, 2), 96, "h*0.60"), ("SE VE VIEJA?", 0, s(0, 2), 96, "h*0.60+120"),
     ("MÁRMOL ADHESIVO", s(0, 2), s(0, 4), 84, "h*0.70"),
     ("SIN OBRA", s(0, 4), c1, 96, "h*0.70"),
     ("QUITAS Y PEGAS", c1, s(1, 4), 84, "h*0.70"),
     ("AGUANTA EL AGUA", s(1, 4), c2, 84, "h*0.70"),
     ("10 PIEZAS · 1.8 m²", s(2, 1), s(2, 3), 80, "h*0.72"),
     ("¡HOY EN OFERTA!", s(2, 3), s(2, 5), 96, "h*0.68"),
     ("CARRITO NARANJA ↓", s(2, 5), D, 84, "h*0.74")]
X = [('cam_shutter.wav', 0.0, 0, 0.8, 0.8), ('riser.wav', max(s(0, 2) - 1.2, 0), 4.6, 1.2, 0.5),
     ('braams.wav', s(0, 2), 0, 2.0, 0.35), ('whoosh1.wav', c1 - 0.3, 0, 1.4, 1.0), ('cam_shutter.wav', s(1, 2), 0, 0.8, 0.6),
     ('whoosh2.wav', c2 - 0.3, 2.6, 1.2, 0.6), ('melodic.wav', s(2, 3), 0, 2.0, 0.7), ('ring.mp3', s(2, 4) - 0.1, 0, 1.2, 0.35)]
T = []
print([(t, round(a, 2), round(b, 2)) for t, a, b, *_ in T])
fuente = _fuente()
with tempfile.TemporaryDirectory() as td:
    td = Path(td); f = []
    for i, (t, a, b, sz, y) in enumerate(T):
        p = td / f't{i}.txt'; p.write_text(t, encoding='utf-8'); f.append(_drawtext(fuente, p, sz, y, a, b))
    p = td / 'ia.txt'; p.write_text('Contenido generado con IA', encoding='utf-8'); f.append(_drawtext(fuente, p, 30, 'h*0.045', box=True))
    ent = ['-i', str(base)]; mix = ''
    for i, (ar, t0, ss, du, vol) in enumerate(X):
        ent += ['-ss', str(ss), '-t', str(du), '-i', f'{S}/{ar}']; d = int(t0 * 1000)
        mix += f'[{i+1}:a]aformat=sample_rates=44100:channel_layouts=stereo,afade=t=out:st={max(du-0.3,0)}:d=0.3,volume={vol},adelay={d}|{d}[s{i}];'
    mix += '[0:a]' + ''.join(f'[s{i}]' for i in range(len(X))) + f'amix=inputs={len(X)+1}:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]'
    sal = OUT / 'Arenero_FINAL.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *ent, '-filter_complex', f"[0:v]null[vv];{mix}", '-map', '[vv]', '-map', '[a]',
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                    '-movflags', '+faststart', str(sal)], check=True)
    print(sal, duracion(sal))
