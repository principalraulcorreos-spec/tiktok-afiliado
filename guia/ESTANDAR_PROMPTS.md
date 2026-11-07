# Estándar de prompts para videos IA (v2)

El código (`afiliado/prompts.py`) arma el prompt solo. Este documento explica **por qué** cada parte existe, cómo llenar la ficha del producto y cómo revisar el clip antes de usarlo. Si algo nuevo falla, se agrega una regla a la bitácora y luego al código.

## 1. Estructura fija del prompt (en este orden)

```
Vertical 9:16 smartphone video, one continuous handheld shot, realistic UGC style, set in {escenario}.
FRAMING: tight shots of hands and the product only; the person's head and face are never in frame, from the first frame to the last frame.
0-2s: the product is visible from the very first frame: {momento 1 — aquí se describe el producto COMPLETO}.
2-5s: {momento 2 — uso; el producto ya es "it"}.
5-8s: {momento 3 — resultado}.
{SOPORTE — física: cómo se sostiene o queda el producto}.
AUDIO: ... says exactly: "{frase ≤17 palabras}" She finishes speaking before the 7-second mark. Light upbeat background music.
PRODUCT ACCURACY: the product is exactly this: {producto}; same shape, color, size and quantity in every frame; realistic physics, normal speed, no effects the real product does not have.
EXCLUDE: {lo que NO viene en el paquete}; no other products, no letters, banners or signs, ..., no logos, no watermarks.
```

## 2. Reglas (cada una viene de un error real)

| # | Regla | Error que la originó |
|---|---|---|
| R1 | El producto aparece en el **cuadro 0**. | Plancha: entró hasta el segundo 4; nadie ve 4 s sin producto. |
| R2 | Sin cara "from the first frame to the last frame". Escenarios sin espejos. | Globos v1 y v2: la persona entra al final. |
| R3 | **Soporte/física** explícita: cómo se sostiene, qué no flota. | Globos v1: un globo flotaba (con aire no flotan). |
| R4 | **EXCLUDE** con lo que la IA suele "regalar" en esa categoría. | Globos v1: letras HAPPY BIRTHDAY que no vienen. |
| R5 | Describir el material **en cada estado** (desinflado, cerrado, apagado...). | Globos v1: desinflados parecían papel metálico. |
| R6 | Una sola toma continua, 3 momentos máximo. | Cortes = más deformaciones del producto. |
| R7 | Voz: frase exacta entre comillas, ≤17 palabras, "natural Mexican Spanish", números en letras. | "$399" lo puede leer como dólares o dígito por dígito. |
| R8 | Producto descrito completo **una sola vez**; después "it". | Repetirlo hace que la IA lo re-imagine a mitad del clip. |
| R9 | El editor corta **0.8 s del final** (`--recorte-final`). | Veo "deriva" al final: cara, objetos nuevos. |
| R11 | Toma **desde arriba** ("filmed from directly above") y voz como **"off-screen narrator, nobody speaks on camera"**. | Audífonos v1: con voz, Veo puso a la mujer hablando a cámara (boca y barbilla todo el clip). |
| R10 | Con foto real → Flow en modo **Ingredientes** y el prompt dice "as in the reference image". Sin foto, esa frase no va. | Prueba de solo texto. |

## 3. Cómo llenar la ficha (columnas `*_en` del CSV, en inglés)

- `producto_en`: lo que se ve, con medidas, color, material y cantidad. *"standard 10-inch round chrome GOLD latex balloons with a mirror-like reflective gold surface, pack of 50"*
- `problema_en`: el "antes" visible, describiendo el producto en su estado inicial (R5).
- `uso_en`: una sola acción, a velocidad normal.
- `resultado_en`: creíble, no perfecto ("visibly cleaner", no "brand new").
- `soporte_en` (R3): dónde queda el producto y qué NO hace. *"air-filled latex balloons do not float; every balloon rests against the wall or on the table"*
- `excluir_en` (R4): lo que la IA suele inventar en esa categoría. Ideas por categoría:
  - fiestas: letras, banners, globos de helio o de foil, manteles con estampado
  - cabello/belleza: otros cepillos, frascos con marca, espejos
  - cocina: otros utensilios con logo, comida que no es la del uso
  - limpieza: botellas de limpiador con etiqueta, cabezales extra
  - tecnología: pantallas con texto, cables o accesorios que no vienen
- `problema` (español): frase sustantiva que encaje en "Deja de batallar con ___" (ej. *la decoración de último minuto*).

## 4. Audio

- `VOZ_IA=1` (en `.env`): Veo dice la frase dentro del clip. Es lo más rápido. El kit muestra la frase.
- `VOZ_IA=0`: el clip va sin diálogo y tú grabas la voz larga (~15 s) del kit. Más trabajo, pero suena más tuyo; TikTok premia que el creador hable.
- Recomendación: empezar con `VOZ_IA=1` para probar volumen; si las visitas se quedan bajas, probar voz propia en la mitad de los videos y comparar en la evaluación mensual.

## 5. Revisión del clip (QA) — 3 cuadros: 0.5 s, 4 s y 7.5 s

Crítico (si falla, se regenera):
1. Producto en el cuadro 0
2. Producto igual a la ficha (forma, color, tamaño, cantidad)
3. Nada que no venga en el paquete
4. Física real (nada flota, nada se transforma)
5. Ninguna cara (si solo sale después de 7.2 s, el recorte lo arregla)
6. Sin texto, letras, logos ni marcas de agua generados

Se arregla en edición:
7. La voz dice la frase exacta y suena natural (si no, `VOZ_IA=0` y grabas tu voz)
8. Resultado creíble

Regla de créditos: máximo **2 intentos** por producto y formato. Si los dos fallan en lo mismo, se corrige la ficha (`soporte_en` / `excluir_en`) y se anota abajo, no se reintenta igual.

## 6. Bitácora de pruebas

| Fecha | Producto | Versión | Resultado | Aprendizaje |
|---|---|---|---|---|
| 2026-10-15 | Plancha | v0 | Producto entra tarde | R1 |
| 2026-10-15 | Globos cromados | v1 | Globo flotando, letras HAPPY BIRTHDAY, desinflados como foil, cara parcial | R2, R3, R4, R5 |
| 2026-10-15 | Globos cromados | v2 | ✅ Producto en cuadro 0, pared con ~45 globos, sin objetos extra. ⚠️ Cara a los ~7.6 s | R9 (recorte final 0.8 s) |
| 2026-10-16 | Audífonos P9 | A v1 | ❌ Boca y barbilla visibles todo el clip (la IA la hizo hablar a cámara) | R11 |
| 2026-10-16 | Audífonos P9 | C (dinámico) | ✅ Caída + zooms, sin cara, loop | Estilo eufórico funciona |
| 2026-10-16 | Audífonos P9 | D (POV metro) | ⚠️ Pasajeros con cara al fondo; el corte de ruido no se nota en el audio; aparece cabello/diadema del POV abajo | En POV pedir "empty metro car" y hacer el corte de ruido en edición |
| 2026-10-16 | Audífonos P9 | A v2 + B | ✅ Toma cenital sin cara; B en camión sin cara, doblado plano correcto | R11 funciona |

## 7. Energía y enganche (investigación oct-2026)

Lo que retiene en TikTok, aplicado al prompt y a la edición:

| Táctica | En el prompt | En la edición |
|---|---|---|
| Lo decisivo pasa en 1.5-2 s | Empezar **a mitad de la acción** ("mid-action"): el producto cae, se abre, se enciende | Gancho en pantalla desde el cuadro 0 |
| Interrupción de patrón cada 2-4 s | "energetic fast camera motion, punch-in zooms, whip moves" | `energizar()`: zoom de golpe + whoosh en 0 s, cortes y cada ~3.5 s |
| Números concretos y comparación | Voz: "Unos de marca cuestan miles de pesos. ¿Estos? Ciento diecinueve." | Texto con el precio exacto |
| Demostración sensorial | POV del beneficio (ruido → silencio, sucio → limpio) | — |
| Voz eufórica | "excited, euphoric ... fast and energetic like sharing an amazing find" | — |
| Loop | Terminar donde empezó ("set it down exactly where it landed at the start") | — |
| CTA antes del final | "¡Carrito naranja!" antes del segundo 7 | — |

Fuentes: opus.pro (hooks 2026), influenceflow.io (retención 2026).

## 8. Estilo "presentadora IA" (el de @bnrrkkmf821) — ESTILO PRINCIPAL desde 16-oct-2026

- Una **misma** chava latina generada con IA (`PERSONA` en prompts.py; en Flow conviene crearla como *personaje* y llamarla con @ para que salga igual en todos los videos).
- Habla **a cámara** con lip-sync, emocionada, y **usa** el producto (se lo pone, se peina, lo prueba). Producto cerca de la cámara desde el cuadro 0.
- Escenas aspiracionales: recámara/tocador bonito con luz de ventana, cocina clara, pasillo de súper con el producto en anaqueles.
- 15 s = 2 clips de 8 s con la misma persona y escena. **Sin textos encima**, sin zooms ni whoosh. Solo la etiqueta de IA.
- R2 (sin cara) y R11 (toma cenital) aplican **solo** al estilo "manos".
- Honestidad: la presentadora describe el producto y su precio; **no** dice "yo lo uso", "me cambió la vida" ni muestra resultados que el producto no da (sería testimonio falso, prohibido en TikTok Shop). Etiqueta de IA siempre activada.

## 9. Video de 30 s "rápido" (estructura de los que venden)

Problema → descubrimiento → prueba/usos → precio → carrito. 4 clips de 8 s (40 créditos), cada uno pedido como
**3 tomas de ~2.6 s** ("THREE quick shots with hard cuts"), una frase corta por toma, misma persona (bloque de personaje
con un detalle ancla: aretes de aro dorados + collar fino).

| Clip | Toma 1 | Toma 2 | Toma 3 |
|---|---|---|---|
| 1 Problema | Se tapa los oídos en el camión: "¿Ya te cansaste del ruido?" | Saca el producto: "Mira lo que encontré." | Se los pone, sonríe: "¡Silencio total!" |
| 2 Prueba | Abre la caja | Close-up del material | Se ajustan |
| 3 Usos | Gym | Llamadas (micrófono) | Se doblan / mochila |
| 4 Cierre | Dato fuerte (batería) | Precio | "¡Están en el carrito naranja!" señalando abajo |

Edición: `afiliado.rapido.armar()` → cortes cada ~1.5 s alternando encuadre completo / acercado (jump cuts),
audio continuo, whoosh entre clips, gancho grande 0-2.4 s. Con `forzar` se recorta un tramo para quitar logos o texto.
Nota: Veo casi nunca hace los cortes duros que se piden; el ritmo lo da la edición.
