# EVOLUCIÓN — mejora continua del sistema TikTok Shop

Registro histórico de auditorías, experimentos y mejoras. La tarea programada "Mejora diaria TikTok Shop" (16:23 CDMX) lo lee y lo actualiza en cada ejecución. Cada cambio vive en Git: para revertir, `git revert <commit>`.

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
| 2026-11-07 | Mejora | Fotos en la zona libre (debajo de la presentadora) | 13.2 % del área de cada foto quedaba bajo la presentadora (tapaba textos como "CORTINAS SUPER OPACAS") | 0 % (foto de 1000 px desde y=700; la presentadora termina en y≈699) | hoja `qa_hoja.jpg` v3; QA igual (7/7 ✅) | ✅ en main |
| 2026-11-07 | Calidad | Pruebas automáticas (`tests/test_secuencia.py`), incluido un control negativo de chroma | 0 pruebas | 4 pruebas, 17 s | `pytest -q` | ✅ |
| 2026-11-07 | Calidad | QA objetivo (`afiliado/qa.py`, `python -m afiliado qa/video`) | revisión solo a ojo | 7 métricas con umbral + hoja de contacto + histórico CSV | `metricas_videos.csv` | ✅ |
| 2026-11-07 | Código | Limpieza de imports sin usar y f-strings vacíos | 6 avisos de pyflakes | 0 | `pyflakes` | ✅ |
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
6. `loudnorm` en una pasada da −16.4 LUFS cuando casi no hay audio (modo sin presentadora). Solo afecta al formato sin voz.
7. El busto de la presentadora termina con un corte recto abajo (se nota en fondos claros).

## Backlog priorizado
| # | Oportunidad | Hipótesis | Métrica | Necesita |
|---|---|---|---|---|
| P1 | Desvanecido inferior del busto (corte suave) | Se ve más natural sin afectar el QA | QA 7/7 + revisión de la hoja | nada |
| P2 | `loudnorm` en 2 pasadas | LUFS dentro de ±0.5 en todos los formatos | LUFS del QA | nada |
| P3 | Selección automática de fotos sin texto en la esquina superior derecha | Menos fotos inútiles | % de fotos aprovechadas | nada |
| P4 | Tiempo de render: preset `veryfast` en las escenas intermedias, `medium` solo en la final | −30 % de tiempo sin perder calidad | segundos de render; tamaño/calidad iguales | nada |
| X1 | Presentadora arriba a la derecha vs abajo al centro (estilo @lojavibebr) | Abajo retiene más | % vista completa, tiempo medio | datos de TikTok Studio, ≥3 videos por variante, OK de Raúl |
| X2 | Gancho de texto grande vs sin texto | Con texto retiene más en los primeros 2 s | retención a 2 s | ídem |
| X3 | ~15 s vs ~21 s | Más corto = más vistas completas, mismas ventas | % vista completa, CTR del producto | ídem |
| X4 | Horario 12:30 vs 19:00 | 19:00 vende más | ventas por 1,000 vistas | ídem |

## Pendientes que requieren a Raúl
- Iniciar sesión en TikTok (Studio y Centro de afiliados) en el navegador integrado de la PC servidor, para medir vistas, retención y ventas.
- Aprobar el primer experimento de contenido (X1) cuando haya ≥6 videos publicados del modo nuevo.
