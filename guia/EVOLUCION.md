# EVOLUCIÓN — mejora continua del sistema TikTok Shop

Registro histórico de auditorías, experimentos y mejoras. La tarea programada "Mejora diaria TikTok Shop" (16:23 CDMX) lo lee y lo actualiza en cada ejecución. Cada cambio vive en Git: para revertir, `git revert <commit>`. La rama `estable` siempre apunta a la última versión validada (la tarea solo la mueve cuando pruebas y QA pasan).

## Tarea programada
- **Mejora diaria TikTok Shop**: todos los días a las 16:23 (CDMX), en la nube, con aprobación automática. Hace un ciclo: estabilidad → métricas → una mejora técnica validada → registro aquí → notificación al celular.
- Límite actual: corre en la nube, **sin acceso a la PC**. No puede leer TikTok Studio, el Centro de afiliados ni `Downloads`. Las métricas de rendimiento se capturan en los chats de producción (`python -m afiliado qa ... --registro` y `guia/metricas_rendimiento.csv`) o se suben al repo.

## Reglas del ciclo
1. **Una mejora por ciclo**, con hipótesis, métrica y prueba antes/después. Nunca dos cambios a la vez sobre la misma métrica.
2. **Nada se fusiona a `main` sin** `pytest` en verde, pyflakes limpio y, si toca el video, `python -m afiliado qa` aprobado y sin empeorar ninguna métrica.
3. Si no se puede validar: rama `mejora/AAAA-MM-DD-<tema>` sin fusionar y anotada aquí como pendiente.
4. **Prohibido sin aprobación de Raúl:** publicar, gastar dinero o créditos de Flow, activar facturación, cambiar la estrategia comercial o el formato principal, borrar funciones y tocar credenciales.
5. **No inventar métricas.** Si falta un dato, se escribe "sin datos" y qué hace falta para conseguirlo.
6. **Experimentos de rendimiento** (vistas, retención, ventas): solo 1 activo a la vez, con ≥3 videos por variante antes de decidir.

## Métricas que se siguen
| Tipo | Métrica | Fuente | Meta |
|---|---|---|---|
| Producción | duración, LUFS, true peak, cortes/s, % congelado, s en negro, % verde residual | `python -m afiliado qa` → `metricas_videos.csv` | todas ✅ |
| Producción | tiempo de render, créditos por video | medición del ciclo | ↓ |
| Código | pruebas que pasan, avisos de pyflakes, líneas | `scripts/auditoria.py` | 100 % / 0 |
| Rendimiento | vistas, retención (vista completa, tiempo medio), CTR del producto, ventas, comisión | TikTok Studio + Centro de afiliados → `metricas_rendimiento.csv` | por definir con la línea base |
| Cumplimiento | infracciones / avisos de TikTok Shop | Centro de cuenta | 0 |

## Historial
| Fecha | Tipo | Qué | Antes | Después | Evidencia | Estado |
|---|---|---|---|---|---|---|
| 2026-11-11 | Mejora | Render: la presentadora se escala **antes** del `chromakey`/`despill` (`secuencia.armar`), así el chroma trabaja sobre 453 px de ancho en vez de 720 (~2.5× menos píxeles). Perfil por etapa de `armar()` (P2) en material sintético de 18 s con 3 clips: escenas ~11–13 s, pasada final ~23–25 s (62 %), concat/mezcla/LUFS <1 s; de la pasada final, ~12 s son filtros y el chroma a tamaño completo era lo más pesado (5 s) | Pasada final 25.6 / 24.5 / 24.3 s (prom. 24.8); total 41.2 s | 19.1 / 20.5 / 20.4 s (prom. 20.0, **−19 %**); total 35.8 s (**−13 %**). Corridas A/B intercaladas. QA 7/7 idéntico (18.17 s, −14.0 LUFS, TP −2.0, 0.5 cortes/s, 0 % congelado, 0 s negro, verde 0.02 %); 10.11 → 10.08 MB. PSNR en la zona de la presentadora entre ambos: 40.4 dB (diferencia no visible) | Prueba nueva `test_chroma_se_aplica_ya_escalado` (falla con el código anterior); 11/11 en 58 s; pyflakes 0. Variantes medidas y no adoptadas: quitar `despill` (−2.4 s, pero deja borde verde) y quitar textos (−0.7 s) | ✅ en main y `estable` |
| 2026-11-10 | Corrección | `python -m afiliado qa` (P3): (a) si el video no existe o no se puede leer, sale con `QA: No existe el video: <ruta>` en vez de un `ValueError` interno; (b) `--registro` ya no tiene valor por defecto: solo agrega fila al histórico si se pide (`--registro guia/metricas_videos.csv`, como ya decía `MODO_REAL_REACCION.md`) | (a) rc=1 con `ValueError: could not convert string to float: ''`; (b) 1 QA sintético sin `--registro` → +1 fila en `metricas_videos.csv` | (a) rc=1 con mensaje claro; (b) +0 filas; con `--registro` a otro CSV: 1 fila. 7 métricas del QA idénticas antes/después en video sintético (3.0 s, −21.8 LUFS, TP −17.7…). Render no se toca | 2 pruebas nuevas (`test_qa_cli_ruta_inexistente_da_mensaje_claro`, `test_qa_cli_registra_solo_si_se_pide`; ambas fallan con el código anterior); 10/10 en 59 s; pyflakes 0 | ✅ en main y `estable` |
| 2026-11-09 | Mejora | Normalización de audio en 2 pasadas (`secuencia._loudnorm_2p`): la mezcla se renderiza 1 vez a WAV midiendo su sonoridad (pasada 1); la pasada 2 prueba 3 ganancias con limitador de picos en una sola llamada e interpola la que da −14 LUFS. Si la medición falla, vuelve al `loudnorm` de 1 pasada | LUFS: −14.8 (presentadora) / −16.5 (sin voz, solo efectos) / −16.6 (voz baja); QA de LUFS ⚠️ en 2 de 3 casos | −14.0 / −14.0 / −14.0 (error máx. 2.6 → 0.1 LU); QA de LUFS ✅ en los 3. True peak −1.6 / −1.9 / −1.6 (umbral −1.0). Duración, cortes/s, congelado, negro y verde idénticos. Render prom. 3 corridas: 12.78→12.57 s, 18.04→18.46 s, 18.59→18.71 s (dentro del ruido: 1 s de variación entre corridas del original) | 2 pruebas nuevas (`test_loudnorm_2_pasadas_sin_voz`, falla con el código anterior: −15.8; y silencio → 1 pasada); 8/8 en 53 s; pyflakes 0. Intentos descartados: `loudnorm` lineal (−15.3, lo frena el true peak de los efectos) y 3–4 re-mediciones en serie (+1.5 s de render) | ✅ en main y `estable` |
| 2026-11-08 | Mejora | Desvanecido inferior del busto de la presentadora (`presentadora.desvanecer`, 0.12 por defecto; 0 = corte recto). Rampa calculada 1 vez y multiplicada con el alfa | Corte recto: salto de luminancia de 203 (fondo liso) / 119 (fondo con movimiento) en una sola fila | Salto de 6 / 4; transición repartida en ~40 filas. QA de 7 métricas idéntico (verde 0.01–0.02 %, LUFS −14.8, TP −1.7). Render 11.27 → 10.93 s (3 corridas c/u, ruido) | 2 pruebas nuevas (`test_busto_se_desvanece_abajo` + control negativo), 6/6 en 31 s; pyflakes 0. Primer intento con `geq` por cuadro: +2.5 s de render (+23 %) → descartado | ✅ en main y `estable` |
| 2026-11-07 | Mejora | Fotos en la zona libre (debajo de la presentadora) | 13.2 % del área de cada foto quedaba bajo la presentadora (tapaba textos como "CORTINAS SUPER OPACAS") | 0 % (foto de 1000 px desde y=700; la presentadora termina en y≈699) | hoja `qa_hoja.jpg` v3; QA igual (7/7 ✅) | ✅ en main |
| 2026-11-07 | Calidad | Pruebas automáticas (`tests/test_secuencia.py`), incluido un control negativo de chroma | 0 pruebas | 4 pruebas, 17 s | `pytest -q` | ✅ |
| 2026-11-07 | Calidad | QA objetivo (`afiliado/qa.py`, `python -m afiliado qa/video`) | revisión solo a ojo | 7 métricas con umbral + hoja de contacto + histórico CSV | `metricas_videos.csv` | ✅ |
| 2026-11-07 | Código | Limpieza de imports sin usar y f-strings vacíos | 6 avisos de pyflakes | 0 | `pyflakes` | ✅ |
| 2026-11-07 | Proceso | Tarea programada diaria (16:23 CDMX) y rama `estable` como punto de recuperación | sin ciclo de mejora | 1 ciclo/día | `list_triggers`: activa, siguiente 2026-11-07 16:23 | ✅ |
| 2026-11-07 | Mejora | Chroma con el color detectado + similitud 0.08 | recuadro gris o cara transparente | 0.0 % de verde residual | QA | ✅ |

## Primera auditoría (2026-11-07)
**Línea base medida**
- Video Cortinas Blackout v3: 20.83 s · −14.0 LUFS · TP −1.4 dB · 0.96 cortes/s · 0 % congelado · 0 s en negro · 0.0 % de verde · 10.8 MB · QA 7/7 ✅.
- Render: 52 s por video (2 vCPU del espacio de trabajo). Pruebas: 17 s.
- Costo: 24 créditos de Flow por video (10 + 7 + 7) → 2 videos/día por cuenta (50 créditos).
- Código: 3,015 líneas en `afiliado/`, 4 pruebas, 0 avisos de pyflakes.
- Rendimiento publicado: **sin datos**. En la PC servidor (DESKTOP-296HQMG) el navegador integrado no tiene sesión de TikTok, y no hay registros de vistas ni ventas del modo nuevo. Es la brecha principal: sin esos datos no se puede optimizar lo que vende.

**Problemas y riesgos detectados**
1. Sin métricas de rendimiento → los experimentos de contenido no se pueden evaluar (falta la sesión de TikTok Studio y del Centro de afiliados en el navegador integrado).
2. Dependencia de la interfaz de Flow: cambió de modelo solo (Omni 1.2) al usar un video como ingrediente. Hay que vigilar el costo en cada ciclo.
3. La ficha de TikTok Shop pide captcha ("Security Check") y no se puede resolver solo.
4. El TTS de AI Studio pide facturación → la voz depende de Veo (lip-sync). Si se aprueba un TTS de pago, la presentadora muda + banco de reacciones bajaría el costo a ~0 créditos/video.
5. Scripts de un solo uso del modo anterior (`scripts/editar_*.py`, `variantes_*.py`): no se borran (son historial); candidatos a moverse a `scripts/legacy/`.
6. ~~`loudnorm` en una pasada da −16.4 LUFS cuando casi no hay audio~~ → resuelto 2026-11-09 (2 pasadas, −14.0 en todos los formatos).
7. ~~El busto de la presentadora termina con un corte recto abajo~~ → resuelto 2026-11-08 (`desvanecer`).

## Backlog priorizado
| # | Oportunidad | Hipótesis | Métrica | Necesita |
|---|---|---|---|---|
| P1 | Selección automática de fotos sin texto en la esquina superior derecha. Revisado 2026-11-11: desde el 7-nov las fotos bajan a la zona libre (0 % bajo la presentadora), así que el texto de la esquina ya no se tapa. Queda solo si se quiere descartar fotos con mucho texto en general; para medirlo hace falta material real de varias fichas | Menos fotos inútiles | % de fotos aprovechadas | fotos reales de ≥3 productos |
| P2 | Tiempo de render del modo REAL+REACCIÓN. Revisado 2026-11-10: las escenas intermedias YA usan `veryfast` (`secuencia.ENC`) y solo la final `medium` → la idea original ya está aplicada. Perfilado 2026-11-11 y chroma escalado aplicado (−19 % en la pasada final). Siguiente: las escenas de fondo (~11–13 s, 1 ffmpeg por escena, en serie) → probar 2 en paralelo (hay 2 vCPU) o `fps`/`scale` antes del `boxblur` de las fotos | menos s por video sin cambiar el QA | segundos por etapa | nada |
| ~~P3~~ | ~~`afiliado qa`: error con ruta inexistente y registro siempre activo~~ → resuelto 2026-11-10 | | | |
| P4 | Aplicar la misma normalización de 2 pasadas en `editor.py` y `rapido.py` (modo anterior; hoy siguen en 1 pasada) | LUFS ±0.5 también ahí | LUFS del QA | nada (baja prioridad: no es el formato principal) |
| X1 | Presentadora arriba a la derecha vs abajo al centro (estilo @lojavibebr) | Abajo retiene más | % vista completa, tiempo medio | datos de TikTok Studio, ≥3 videos por variante, OK de Raúl |
| X2 | Gancho de texto grande vs sin texto | Con texto retiene más en los primeros 2 s | retención a 2 s | ídem |
| X3 | ~15 s vs ~21 s | Más corto = más vistas completas, mismas ventas | % vista completa, CTR del producto | ídem |
| X4 | Horario 12:30 vs 19:00 | 19:00 vende más | ventas por 1,000 vistas | ídem |

## Pendientes que requieren a Raúl
- En el próximo video real, confirmar que el audio no suena "apretado" (el QA debe dar −14 LUFS; si la voz se oye comprimida, avisar).
- En el próximo video real, mirar el borde de la presentadora (pelo, manos): desde el 11-nov el chroma se aplica ya escalado. En sintético no hay diferencia visible (PSNR 40 dB), pero el pelo real es el caso difícil; si se ve verde o dentado, avisar y se revierte con `git revert`.
- Revisar en el próximo video real que el desvanecido del busto se vea natural (si no gusta: `"desvanecer": 0` en el timeline).
- Iniciar sesión en TikTok (Studio y Centro de afiliados) en el navegador integrado de la PC servidor, para medir vistas, retención y ventas.
- Aprobar el primer experimento de contenido (X1) cuando haya ≥6 videos publicados del modo nuevo.

## Rendimiento (revisión 2026-11-11)
- `guia/metricas_rendimiento.csv`: sigue sin existir → sin datos. X1–X4 no evaluables. Falta: sesión de TikTok Studio y Centro de afiliados en la PC servidor (o subir el CSV) y ≥3 videos por variante.
- `guia/metricas_videos.csv`: 2 filas (Cortinas Blackout v2 y v3); sin videos nuevos desde el 7-nov.

## Rendimiento (revisión 2026-11-10)
- `guia/metricas_rendimiento.csv`: sigue sin existir → sin datos. X1–X4 no evaluables. Falta: sesión de TikTok Studio y Centro de afiliados en la PC servidor (o subir el CSV) y ≥3 videos por variante.
- `guia/metricas_videos.csv`: 2 filas (Cortinas Blackout v2 y v3); sin videos nuevos desde el 7-nov.

## Rendimiento (revisión 2026-11-09)
- `guia/metricas_rendimiento.csv`: sigue sin existir → sin datos. Ningún experimento X1–X4 evaluable. Falta lo mismo: sesión de TikTok Studio y Centro de afiliados en la PC servidor (o subir el CSV) y ≥3 videos por variante.
- `guia/metricas_videos.csv`: 2 filas (Cortinas Blackout v2 y v3); sin videos nuevos desde el 7-nov.

## Rendimiento (revisión 2026-11-08)
- `guia/metricas_rendimiento.csv`: no existe. Sin datos de vistas, retención ni ventas → ningún experimento de contenido (X1–X4) se puede evaluar. Falta: sesión de TikTok Studio y Centro de afiliados en la PC servidor, o subir el CSV al repo, y ≥3 videos por variante.
- `guia/metricas_videos.csv`: 2 filas (Cortinas Blackout v2 y v3, 7/7 ✅); sin videos nuevos desde el 7-nov.

## Resumen semanal (semana al 2026-11-08)
- Mejoras en main: fotos en zona libre, QA objetivo (7 métricas), pruebas automáticas (4 → 6), limpieza pyflakes (6 → 0), chroma con color detectado, desvanecido del busto.
- Estabilidad: 6/6 pruebas, 0 avisos, `estable` = main.
- Rendimiento: sin datos (bloqueante principal). Videos REAL+REACCIÓN producidos: 1 (Cortinas Blackout).
