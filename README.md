# Sistema Afiliado TikTok Shop con videos IA

Selección de productos con puntaje → kit diario (prompts, guion de voz, descripción) → clip IA (Flow gratis o Veo API) → edición automática → borrador en TikTok → métricas → evaluación mensual que reescribe las reglas.

## Instalación (Windows, una sola vez)

1. Instala Python 3.11+ y ffmpeg (`winget install Gyan.FFmpeg`).
2. En esta carpeta:
   ```
   pip install -r requirements.txt
   copy .env.example .env
   python -m afiliado init
   ```

## Operación diaria (MVP, ~40 min)

| Cuándo | Qué | Comando |
|---|---|---|
| Noche anterior | Generar el kit de mañana | `python -m afiliado planear` |
| Noche anterior | Abrir `data/kits/<fecha>/KIT.md`, crear los 4 clips en Flow (Veo 3.1 Lite, 9:16, x1) subiendo la **imagen inicial** del producto. Guardar cada clip como `data/clips/<fecha>/<id>.mp4` | — |
| Noche anterior | Revisar cada clip con la lista del kit (cuadros 0.5 s · 4 s · 7.5 s). Con `VOZ_IA=0`: grabar las voces (`data/voces/<fecha>/<id>.m4a`) | — |
| Mañana | Armar los 4 videos | `python -m afiliado editar-dia` (corta 0.8 s del final; cambia con `--recorte-final`) |
| Cada horario | Publicar desde la app: **Agregar enlace → Productos**, activar **Contenido generado por IA**, pegar descripción | — |
| Al publicar | Guardar el enlace | `python -m afiliado publicado <id> --link <url>` |

## Productos

Llena `ejemplos/productos.csv` (o lo llenamos juntos en la sesión semanal) y:
```
python -m afiliado agregar productos.csv     # importa y puntúa
python -m afiliado productos                 # ranking
python -m afiliado activar 1 2 3             # solo los que YA agregaste a tu vitrina
```
`beneficios` = frases separadas por `|` que completen "con este producto ___" (ej. `deja el cabello liso en una pasada`).
Los campos `*_en` (inglés) describen la escena para la IA de video, incluidos `soporte_en` (física) y `excluir_en` (lo que no viene). Cómo llenarlos y cómo revisar cada clip: **guia/ESTANDAR_PROMPTS.md**. `imagenes` = ruta a la foto real del producto (obligatoria).

## Métricas y evaluación

```
python -m afiliado importar-metricas export_studio.xlsx --fuente csv_studio
python -m afiliado importar-metricas export_afiliados.csv --fuente csv_afiliados
python -m afiliado evaluar --mes 2026-11       # reporte en data/reportes + data/reglas.json
```
El planificador y el puntaje leen `data/reglas.json` automáticamente: más espacios a los formatos y ganchos que ganan,
productos marcados como `escalar` salen el doble, los `descartado` dejan de salir.

## Fase 2 (automatizar)

- **Veo por API**: pon `GEMINI_API_KEY`, corre `python -m afiliado listar-modelos`, elige el Lite en `VEO_MODEL`.
  Luego `python -m afiliado dia --api` genera y edita solo. Costo ≈ $0.40 USD por clip de 8 s (Lite 720p).
- **Borradores por API**: crea una app en developers.tiktok.com (Login Kit + Content Posting API, scope `video.upload`),
  `python -m afiliado tiktok-login`, `tiktok-codigo <url>`, y `borradores-dia`. Los videos llegan a tu bandeja;
  en la app solo agregas el producto, la etiqueta IA y publicas.
- **Programar en Windows**: Programador de tareas → `rutina_diaria.bat` diario a las 22:00.

## Lo que NO hace (a propósito)

- No vincula el producto del carrito por API: la Content Posting API no tiene ese campo.
- No publica con ADB ni bots: automatizar la app viola los Términos de TikTok y pone en riesgo la cuenta y tus comisiones.
- No genera productos sin foto real ni testimonios inventados.

## Flujo actual (presentadora IA, oct-2026)

- **Protocolo completo**: [`guia/PROTOCOLO.md`](guia/PROTOCOLO.md), incluidas las reglas anti-sanción. Léelo antes de cada video.
- **Estándar de prompts**: [`guia/ESTANDAR_PROMPTS.md`](guia/ESTANDAR_PROMPTS.md).
- **Edición por producto**: `scripts/editar_<producto>.py` (video original) y `scripts/variantes_<producto>.py` (variaciones gratis con los mismos clips). Copia uno, cambia rutas y tramos.
- **Tablero de avance**: `scripts/tablero_estado.html`.
- Los videos, fotos y SFX **no** van al repo: viven en `Downloads\<Producto>\` o en Google Drive.

### Dónde trabajar
- **Claude Code + este repo** → cambios al código y al protocolo (quedan versionados).
- **Chat de la app de Claude (proyecto TIKTOK SHOP)** → operar: investigar, generar clips, editar y preparar TikTok Studio.
