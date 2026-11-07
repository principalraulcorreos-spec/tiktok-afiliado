import sys; sys.path.insert(0,'/home/claude/tiktok_afiliado')
from afiliado.rapido import armar
C='/home/claude/gato/clips'; c1=f'{C}/ga_clip1.mp4'; c2=f'{C}/ga_clip2.mp4'; c3=f'{C}/ga_clip3.mp4'
A=lambda a,b,z=1.0:(a,b,z,.5,.35); B=lambda a,b,z=1.15:(a,b,z,.5,.5)
P1=[A(0,1.1),A(1.1,2.27,1.28)]; R1=[A(2.54,3.84,1.28),A(4.1,4.5,1.28),A(4.5,5.4),A(5.4,6.26,1.28),A(6.59,7.59)]
G2=[B(0,1.67),B(2.2,2.66,1.35)]; O2=[B(3.03,3.9),B(3.9,4.78,1.35)]; L2=[B(5.03,6.3),B(6.3,7.5,1.35)]
S3=[A(0,1.0),A(1.0,1.98,1.28)]; H3=[A(2.58,3.74)]; K3=[A(4.12,5.35,1.28)]; CTA=[A(5.74,6.7),A(6.7,7.62,1.28)]
V={'Arenero_B_gato_primero':[(c2,G2),(c1,P1+R1),(c2,O2+L2),(c3,S3+H3+K3+CTA)],
   'Arenero_C_corto':[(c1,P1),(c1,[A(2.54,3.84,1.28)]),(c2,G2+O2),(c3,CTA)],
   'Arenero_D_olor':[(c1,P1),(c2,O2),(c1,R1),(c2,G2+L2),(c3,K3+CTA)],
   'Arenero_E_casa_limpia':[(c3,S3),(c1,P1+R1),(c2,G2+O2+L2),(c3,H3+K3+CTA)]}
for n,cl in V.items(): armar(cl,f'out/{n}.mp4',etiqueta_ia=False)
