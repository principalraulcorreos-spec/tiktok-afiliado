import sys; sys.path.insert(0,'/home/claude/tiktok_afiliado')
from afiliado.rapido import armar
C='/home/claude/marmol/clips'
def tr(l): return [(a,b,(1.0,1.28)[i%2],0.5,0.35) for i,(a,b) in enumerate(l)]
c1=f'{C}/mm_clip1.mp4'; c2=f'{C}/mm_clip2.mp4'; c3=f'{C}/mm_clip3b.mp4'
# B: arranca con el resultado (antes/después invertido)
armar([(c3,tr([(0,1.5)])),(c1,tr([(0,1.3),(1.3,2.62),(2.88,3.75),(4.0,5.3)])),(c2,tr([(0.2,1.4),(1.54,2.3),(3.6,4.4),(4.4,5.2),(5.48,6.5),(6.5,7.6)])),
       (c3,tr([(1.5,2.6),(2.6,3.37),(3.37,4.3),(4.3,5.07),(5.34,6.5),(6.5,7.57)]))],'out/Marmol_B_resultado_primero.mp4',etiqueta_ia=False)
# C: corto ~12 s, directo al grano
armar([(c1,tr([(0,1.3),(1.3,2.62)])),(c2,tr([(0.2,1.4),(1.54,2.3),(3.6,4.4),(4.4,5.2)])),(c3,tr([(0,1.5),(5.34,6.5),(6.5,7.57)]))],'out/Marmol_C_corto.mp4',etiqueta_ia=False)
