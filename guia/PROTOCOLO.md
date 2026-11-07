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
- **Formato principal desde 7-nov-2026: REAL + REACCIÓN** (`guia/MODO_REAL_REACCION.md`): el producto sale solo en videos/fotos reales de la ficha; la presentadora IA va con fondo verde arriba a la derecha y NUNCA sostiene ni dibuja el producto.
- Herramientas probadas: Google Flow (Veo 3.1 Lite) = baja fidelidad del producto. Dola AI (app, Seedance 2.0 Fast, 2 videos de 10 s/día gratis) = pendiente de validar fidelidad.

## Recursos
- Código: repo clonado en `/home/claude/tiktok-afiliado` (`afiliado/`). Guías: `guia/MODO_REAL_REACCION.md` (actual) y `ESTANDAR_PROMPTS.md` (modo anterior).
- Carpeta en la PC: `Downloads\<Producto>\` (fotos/, clips/, sfx/, FINAL.mp4, descripcion.txt).
- Efectos de sonido: `C:\Users\Raúl\Videos\Sound FX` (en device_bash: `$HOME/mnt/Sound FX`).
- Google Flow: 3 cuentas de 50 créditos/día cada una (principal se recarga ~10:12 pm). Veo 3.1 Lite = 10 créditos por clip de 8 s, modo Ingredientes con foto de referencia, 9:16, x1. Evitar 8–11 am (saturado).
- Navegador integrado con sesión de TikTok (Studio) y Flow abiertos.

## Etapa 1 — Investigación (sin créditos)
1. Abrir el enlace en el navegador integrado; con `get_page_text` sacar: nombre, precio, comisión, calificación, ventas, variantes, medidas/material, qué incluye el paquete.
2. Revisar si ya está en la vitrina. Si no: ✋ pedir a Raúl que dé "Agregar a la vitrina" (el sistema bloquea ese clic).
3. Definir: problema que resuelve, 3 beneficios visibles, qué NO incluye (para EXCLUDE).
Salida: ficha de 6 líneas.

## Etapa 2 — Material (modo REAL + REACCIÓN)
1. En la ficha (shop.tiktok.com/mx/pdp/...; si sale "Security Check", ✋ Raúl lo resuelve): sacar el video de la galería (`document.querySelector('video').currentSrc`) y 8–12 fotos (`~tplv-...-resize-webp:800:800.webp` → `origin-jpeg.jpeg`).
2. Descargar con **XHR blob** (fetch está intervenido en la página) → `<a download>`. Chrome los guarda en Downloads a veces como `.tmp`: identificarlos por tamaño, pasarlos con device_stage_files y ordenarlos en `<Producto>/videos`, `/fotos`.
3. Hacer una hoja de contacto del video (`fps=1/2,tile`) para elegir tramos y ver si trae subtítulos quemados (→ `quitar_abajo`).
4. Si la ficha no trae ningún video, el producto baja de prioridad (la política pide ≥3 s de contenido dinámico real).

## Etapa 3 — Guion (18–24 s)
Resultado más impactante primero (0–1.5 s) → problema → detalles reales → carrito.
- 2 clips de presentadora de 8 s (gancho+problema / beneficios+"carrito naranja"), frases ≤17 palabras, solo lo que dice la ficha. Sin "yo lo uso" ni testimonios. Nunca el precio: "está en oferta".
- Textos: gancho grande (0–1.9 s), captions chicos de 2–3 palabras sincronizados a su voz, CTA "CARRITO NARANJA ↓" al final. Nada más.
- Tabla de escenas (tramo de video/foto, con duración de 1.0–1.6 s) → `timeline.json`.
✋ Confirmación 1: guion + tabla de escenas.

## Etapa 4 — Presentadora (20 créditos)
- `prompts.construir_reaccion(linea, gesto)` (gestos: sorpresa, explica, senala_abajo, duda_a_wow). Flow → **texto a video** (sin Ingredientes ni foto del producto), Veo 3.1 Lite, 9:16, x1.
- QA: fondo verde parejo, sin objetos ni producto en las manos, cara estable, lip-sync, termina antes de 7 s. Si falla → regenerar máximo 1 vez.
- Descargar a `<Producto>/presentadora/`. Ir juntando clips buenos en un **banco de reacciones** reutilizable (`Downloads/banco_reacciones/`).

## Etapa 5 — Edición (`afiliado/secuencia.py`)
- `python -m afiliado.secuencia <Producto>/timeline.json` (o `plan_auto()` y luego ajustar). Hace: escenas 1080x1920 con movimiento (zoom de golpe, Ken Burns, recortes que rebotan), chroma key de la presentadora arriba a la derecha que entra deslizándose, captions con efecto pop, whoosh/pop en cada corte, loudnorm −14 LUFS.
- Debe imprimir movimiento real ≥50 %. QA en `MODO_REAL_REACCION.md`.
- Copiar FINAL.mp4 + descripcion.txt a `Downloads\<Producto>\` con device_commit_files.
✋ Confirmación 2: enviar el video (SendUserFile).

### Modo anterior (100 % IA con producto): DESCONTINUADO
Solo si una herramienta reproduce el producto idéntico. Referencia: `ESTANDAR_PROMPTS.md`, `editar_final_plantilla.py`.

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
