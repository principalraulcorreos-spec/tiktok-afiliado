# Modo REAL + REACCIÓN (desde 7-nov-2026)

Formato principal desde el 7-nov-2026. Sustituye al video 100 % IA, que causó 2 sanciones por "promoción inconsistente".

**Regla de oro:** el producto sale **solo** en material real de la ficha (videos y fotos del vendedor). La IA solo hace de presentadora con fondo verde: reacciona, habla y señala. Nunca sostiene ni dibuja el producto.

## Por qué (investigación 7-nov-2026)

| Fuente | Hallazgo | Cómo se aplica |
|---|---|---|
| Política TikTok Shop EE. UU. (may-2026) | Videos de compra: ≥3 s de contenido dinámico; prohibido un video entero de imágenes fijas sin persona ni producto real; se esperan personas visibles y movimiento | ≥50 % del video con movimiento real; fotos siempre con movimiento y ≤1.2 s |
| Política de contenido no original | Los slideshows hechos en masa con voz IA genérica se marcan como no originales | Presentadora + edición propia; nunca solo fotos con voz |
| Botas acolchadas (64 K likes, 19 s) | Demo real en mano desde el cuadro 0, sin texto | El gancho es un tramo de video real, no una foto |
| Luces LED cascada (62 K likes, 13 s) | Abre con el resultado más espectacular y después muestra cómo se logra | Primero el resultado, después el proceso |
| @lojavibebr (16.7 K likes, 28 s, #react) | Presentadora recortada sobre el video de demo, gesticulando todo el tiempo | Este mismo formato; Raúl la quiere arriba a la derecha |
| @santiago_mxshop (32.8 K likes, 22 s) | Producto en mano con captions chicos sincronizados a la voz | Captions chicos al centro; texto grande solo en el gancho y el CTA |

Duración de los videos ganadores: 13–28 s, con cortes cada 1–2 s.

## Estructura (~18–24 s)

| Tiempo | Fondo (material real) | Presentadora (arriba a la derecha) | Texto |
|---|---|---|---|
| 0–1.5 s | Resultado más impactante, con zoom de golpe | Entra deslizándose, sorpresa | Gancho grande |
| 1.5–8 s | El problema y cómo lo resuelve | Clip 1: gancho + problema | Captions de su frase |
| 8–15 s | Detalles: material, accesorios, usos (fotos con movimiento entre videos) | Clip 2: beneficios + "carrito naranja" | Captions |
| Últimos 2 s | Producto completo / variedad | Señala abajo a la izquierda | "CARRITO NARANJA ↓" con flecha que rebota |

El precio nunca se dice ni se muestra.

## Archivos por producto

`Downloads\<Producto>\`
- `videos\` — videos de la ficha (la galería de TikTok Shop casi siempre trae 1)
- `fotos\` — fotos de la galería
- `recortes\` — producto sin fondo (opcional, `secuencia.recortar_fondo`)
- `presentadora\` — clips con fondo verde de Flow
- `timeline.json` → `FINAL.mp4` + `descripcion.txt`

## Comandos

```python
from afiliado import secuencia, prompts
prompts.construir_reaccion("¡No, espérate! ...", "sorpresa")      # prompt para Flow (texto a video, 9:16)
tl = secuencia.plan_auto("Downloads/Cortinas_Blackout", duracion=20)  # timeline automático (luego se ajusta a mano)
secuencia.armar(tl, "Downloads/Cortinas_Blackout")
```
o `python -m afiliado.secuencia Downloads/<Producto>/timeline.json`.

## Parámetros útiles del timeline

- `quitar_abajo: 0.2` en escenas de video: recorta los subtítulos que el vendedor ya trae quemados.
- `punch: true`: zoom de golpe (úsalo en el primer tramo y cada ~4 cortes).
- `presentadora.recorte_y: [0, 0.62]`: usa solo el busto del clip; `ancho: 0.42` del video.
- `presentadora.similitud`: súbelo (0.18–0.25) si queda borde verde y bájalo si se borra el pelo o la cara.
- `frases`: la frase exacta que dice la presentadora → captions automáticos de 3 palabras.

## QA antes de entregar

1. Ningún cuadro de IA muestra el producto.
2. No hay borde verde ni halos alrededor de la presentadora.
3. La presentadora no tapa el producto (si lo tapa, cambiar `pos` o mover la escena).
4. ≥50 % de movimiento real (el script lo imprime).
5. Nada de subtítulos del vendedor (ajustar `quitar_abajo`) ni precio visible.
6. La etiqueta "Contenido generado por IA" se activa en TikTok al publicar.

## Bitácora

| Fecha | Producto | Versión | Resultado | Aprendizaje |
|---|---|---|---|---|
| 2026-11-07 | Cortinas Blackout | v1 | Prueba del modo | ver PROTOCOLO |
