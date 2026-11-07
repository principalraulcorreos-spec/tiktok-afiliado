# PROTOCOLO — 1 enlace de producto → 1 video publicado con carrito naranja

Instrucción para Claude: cuando Raúl mande solo un enlace de TikTok Shop (o "inicia la investigación"), ejecuta este protocolo completo sin preguntar, con el mínimo de tokens. Detente solo en los 3 puntos de confirmación marcados con ✋.

## Reglas fijas
- Si una etapa falla: no avances; di qué falló y propón cómo resolverlo.
- Lleva un registro de una línea por etapa: `Etapa N/6 ✅ …`.
- Nunca publiques, compres ni aceptes términos sin confirmación de Raúl. El clic final en "Publicar" lo da Raúl (el sistema bloquea que Claude lo haga).
- Ahorro de tokens: no narrar; capturas solo para verificar; usar `javascript_tool`/`find` antes que capturas; no repetir textos largos en el chat.
- Respuestas en español, cortas.

## Sincronización con GitHub (automática — Raúl solo usa el chat)
Repo: `principalraulcorreos-spec/tiktok-afiliado` (rama main). Raúl NO decide entre chat y Code: todo se pide en el chat del proyecto y Claude se encarga.
- **Al empezar cada chat:** `add_repo` del repo y `git clone --depth 1` → usar SIEMPRE el código y el protocolo del repo (no copias viejas).
- **Si la petición cambia cómo funciona el sistema** (editor, prompts, scripts nuevos, reglas del protocolo): hacer el cambio en el clon, probarlo, `git commit` + `git push`, y actualizar también `claude/PROTOCOLO.md` del proyecto. Avisar en una línea: "Guardado en GitHub".
- **Si la petición es operar** (hacer un video, investigar, publicar): no tocar el repo, salvo anotar el video en la bitácora de este archivo y hacer push.
- Si el push falla por permisos: avisar a Raúl que revise la app de Claude en GitHub (Only select repositories → tiktok-afiliado).

## ⚠️ Reglas anti-sanción (oct-2026: 2 infracciones "Promoción de productos inconsistente", −15 pts c/u)
Causa: la IA dibujó el producto distinto al vinculado (mármol: cocina completa forrada con 10 piezas = 1.8 m²; arenero: cambiaba de gris a blanco y de forma).
- El producto en video debe coincidir EXACTO con la variante vinculada: forma, color, tamaño y cantidad. Revisar cuadro por cuadro contra las fotos de la ficha antes de entregar.
- La IA solo PRESENTA el producto (lo sostiene o señala). Nada de demostraciones simuladas ni antes/después que el producto no logra con 1 paquete.
- Solo decir lo que viene literal en la ficha. Nada de "mi gato", "yo lo uso" ni testimonios.
- Si un clip muestra el producto distinto: no se usa, aunque sea "casi igual".
- Revisar los términos de afiliado de cada producto: algunas marcas prohíben contenido IA.
- Formato más seguro: fotos reales de la ficha (`fotos.py`) + presentadora IA que solo habla en el gancho.
- Herramientas probadas: Google Flow (Veo 3.1 Lite) = baja fidelidad del producto. Dola AI (app, Seedance 2.0 Fast, 2 videos de 10 s/día gratis) = pendiente de validar fidelidad.

## Recursos
- Código: proyecto → `codigo/*.py` (copiar a `/home/claude/tiktok_afiliado/afiliado/`). Guía de prompts: `ESTANDAR_PROMPTS.md`.
- Carpeta en la PC: `Downloads\<Producto>\` (fotos/, clips/, sfx/, FINAL.mp4, descripcion.txt).
- Efectos de sonido: `C:\Users\Raúl\Videos\Sound FX` (en device_bash: `$HOME/mnt/Sound FX`).
- Google Flow: 3 cuentas de 50 créditos/día cada una (principal se recarga ~10:12 pm). Veo 3.1 Lite = 10 créditos por clip de 8 s, modo Ingredientes con foto de referencia, 9:16, x1. Evitar 8–11 am (saturado).
- Navegador integrado con sesión de TikTok (Studio) y Flow abiertos.

## Etapa 1 — Investigación (sin créditos)
1. Abrir el enlace en el navegador integrado; con `get_page_text` sacar: nombre, precio, comisión, calificación, ventas, variantes, medidas/material, qué incluye el paquete.
2. Revisar si ya está en la vitrina. Si no: ✋ pedir a Raúl que dé "Agregar a la vitrina" (el sistema bloquea ese clic).
3. Definir: problema que resuelve, 3 beneficios visibles, qué NO incluye (para EXCLUDE).
Salida: ficha de 6 líneas.

## Etapa 2 — Material
1. Descargar 6–16 fotos reales del producto (XHR blob → `<a download>` a `Downloads\<Producto>\fotos`).
2. Elegir 1 foto limpia de referencia para Flow.

## Etapa 3 — Guion (estructura viral 22–30 s)
Problema (gancho 0–2 s) → descubrimiento → prueba/usos → oferta → carrito.
- 3 clips de 8 s, presentadora latina IA fija (`PERSONA`: aretes de aro dorados + collar fino), 3 tomas por clip, lip-sync español mexicano, frases ≤17 palabras.
- Honestidad: sin testimonios falsos ("yo lo uso", "me cambió la vida"), sin 100% ni resultados que no da.
- SIN textos en pantalla, sin subtítulos y sin etiqueta "Contenido generado con IA" quemada (la etiqueta se activa en TikTok). Nunca decir ni mostrar el precio (cambia); usar "está en oferta".
- SFX de la carpeta: cam_shutter (cortes de texto), riser→braams (revelación), whoosh (transiciones), melodic (oferta), ring (CTA).
✋ Confirmación 1: mostrar guion en tabla corta.

## Etapa 4 — Generación (30 créditos)
- `prompts.construir_presentadora(...)` por clip. Flow: Ingredientes + foto, subir imagen con el truco de `HTMLInputElement.prototype.click` + File por XHR.
- Escribir prompt con `find` ref y verificar longitud del contenteditable.
- Descargar clips a `Downloads\<Producto>\clips`. QA (ESTANDAR_PROMPTS §5): si falla producto/física/texto generado → regenerar máximo 1 vez.

## Etapa 5 — Edición
- Plantilla `codigo/editar_final.py`: `tramos_auto(8)` jump cuts 1.0/1.28 cada ~1.55 s, corte de silencios (detectar con `silencedetect=-35dB:d=0.25`), SFX en cada corte (sin textos ni etiqueta quemada), loudnorm −14 LUFS, 1080x1920.
- Copiar FINAL.mp4 + descripcion.txt a `Downloads\<Producto>\` con device_commit_files.
✋ Confirmación 2: enviar el video (SendUserFile).

## Etapa 6 — Publicación (TikTok Studio web)
1. `tiktok.com/tiktokstudio/upload`, viewport 1400x950 (`resize_window`).
2. Archivo: Raúl lo selecciona (pendiente automatizar, ver abajo).
3. Descripción con `form_input`/inserción en el contenteditable (≤ 400 caracteres, gancho + beneficios + "carrito naranja 🛒👇" + "Video creado con IA…" + 6 hashtags).
4. Agregar enlace → Productos → radio del producto correcto (verificar ID) → nombre ≤30 caracteres → Agregar.
5. Mostrar más → "Contenido generado por IA" ON (diálogo "Activar"). Verificar con JS que "Comprobación de contenido rápida" siga ON.
6. Esperar comprobaciones en verde.
✋ Confirmación 3: tabla (video, descripción, producto + ID, switches). Raúl presiona "Publicar".
7. Al terminar: `resize_window` preset desktop; anotar en la bitácora de ESTANDAR_PROMPTS.

## Pendiente
- Subida del archivo sin intervención: el selector de archivos de Windows no es controlable. Opción en evaluación: almacén de videos en un artifact de Claude y que la página lo inyecte al input de TikTok. Requiere permiso explícito de Raúl.

## Bitácora de videos
| Fecha | Producto | ID | Duración | Estado |
|---|---|---|---|---|
| 2026-10-19 | Cortinas Blackout 2 Paneles | 1735698904811471953 | 22 s | Publicado |
| 2026-10-19 | Paneles mármol adhesivo 10 pz | 1733217540882335646 | 20 s | Publicado → sancionado (cocina completa forrada, v1 con textos) |
| 2026-10-19 | Hidrolavadora IRONHOOF | 1733359632838526590 | 19 s + 2 var. | Entregado, no subir (demostración simulada) |
| 2026-10-19 | Arenero cerrado UNA MASCOTA | 1731244617720432440 | 20 s + 4 var. | Var. B publicada → sancionada (color/forma cambian) |
