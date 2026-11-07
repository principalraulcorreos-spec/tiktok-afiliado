import sys; sys.path.insert(0,'/home/claude/tiktok_afiliado')
from afiliado.rapido import armar
C='/home/claude/hidro/clips'
def tr(l): return [(a,b,(1.0,1.28)[i%2],0.5,0.35) for i,(a,b) in enumerate(l)]
c1=f'{C}/hd_clip1.mp4'; c2=f'{C}/hd_clip2.mp4'; c3=f'{C}/hd_clip3.mp4'
# B: abre con la espuma en la llanta (gancho visual) y luego la historia
armar([(c2,tr([(5.82,6.7)])),(c1,tr([(0,1.1),(1.1,2.1),(2.38,2.86),(3.24,4.25),(4.25,5.24),(5.9,6.6),(6.94,7.62)])),
       (c2,tr([(0,1.0),(1.0,2.04),(2.4,3.05),(3.25,4.1),(4.1,4.98),(6.7,7.65)])),
       (c3,tr([(0,1.15),(2.1,2.8),(2.8,3.52),(3.87,4.5),(4.5,5.12),(5.43,6.6),(6.6,7.7)]))],'out/Hidro_B_espuma_primero.mp4',etiqueta_ia=False)
# C: corta ~11 s
armar([(c1,tr([(0,1.1),(1.1,2.1),(3.24,4.25)])),(c2,tr([(0,1.0),(5.82,6.7),(6.7,7.65)])),(c3,tr([(2.1,2.8),(2.8,3.52),(5.43,6.6),(6.6,7.7)]))],'out/Hidro_C_corto.mp4',etiqueta_ia=False)
