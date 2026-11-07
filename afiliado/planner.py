"""Plan diario: elige producto + formato + gancho para cada horario y arma el "kit" del día.

El kit (data/kits/AAAA-MM-DD/) trae, por video: prompt para Flow/Veo, imagen del producto que debes
subir como imagen inicial, gancho, guion de voz para que lo grabes, descripción y hashtags.
"""
from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

from . import db, prompts
from .config import HORARIOS, KITS_DIR, VIDEOS_POR_DIA, VOZ_IA
from .scoring import cargar_reglas

MAX_POR_PRODUCTO_SEMANA = 5     # evita saturar la cuenta con el mismo producto
MAX_POR_PRODUCTO_DIA = 1


def _pesos(reglas: dict, clave: str, opciones: list[str]) -> list[float]:
    w = reglas.get(clave, {})
    return [max(0.05, float(w.get(o, 1.0))) for o in opciones]


def _usos_recientes(producto_id: int, dias: int, hasta: date) -> int:
    desde = (hasta - timedelta(days=dias)).isoformat()
    r = db.query("SELECT COUNT(*) n FROM videos WHERE producto_id=? AND fecha_plan>? AND estado!='descartado'",
                 (producto_id, desde))
    return r[0]["n"]


def planear(dia: date | None = None, n: int | None = None, semilla: int | None = None) -> Path:
    dia = dia or date.today() + timedelta(days=1)
    n = n or VIDEOS_POR_DIA
    rng = random.Random(semilla if semilla is not None else dia.toordinal())
    reglas = cargar_reglas()

    candidatos = [p for p in db.productos(("activo", "escalar")) if p["en_vitrina"]]
    if not candidatos:
        raise SystemExit("No hay productos activos y en vitrina. Usa `agregar` y luego `activar`.")

    # Peso por producto: puntaje, x2 si la evaluación dijo "escalar"
    disponibles = [p for p in candidatos if _usos_recientes(p["id"], 7, dia) < MAX_POR_PRODUCTO_SEMANA]
    if not disponibles:
        disponibles = candidatos

    formatos = prompts.FORMATOS
    w_formato = _pesos(reglas, "formatos", formatos)
    horarios = sorted(h.strip() for h in (reglas.get("horarios_top") or HORARIOS))

    elegidos, usados_hoy = [], {}
    for i in range(n):
        pool = [p for p in disponibles if usados_hoy.get(p["id"], 0) < MAX_POR_PRODUCTO_DIA] or disponibles
        pesos = [(p["puntaje"] or 1) * (2 if p["estado"] == "escalar" else 1) for p in pool]
        p = rng.choices(pool, weights=pesos)[0]
        usados_hoy[p["id"]] = usados_hoy.get(p["id"], 0) + 1

        # Evita repetir formato con el mismo producto si ya lo usó esta semana
        hechos = {r["formato"] for r in db.query(
            "SELECT formato FROM videos WHERE producto_id=? AND fecha_plan>?",
            (p["id"], (dia - timedelta(days=7)).isoformat()))}
        opciones = [f for f in formatos if f not in hechos] or formatos
        w = [w_formato[formatos.index(f)] for f in opciones]
        formato = rng.choices(opciones, weights=w)[0]

        tipos = prompts.FORMATO_A_GANCHOS[formato]
        tipo_g = rng.choices(tipos, weights=_pesos(reglas, "ganchos", tipos))[0]
        kit = prompts.construir(p, formato, rng=rng, tipo_gancho=tipo_g, voz_ia=VOZ_IA)
        horario = horarios[i % len(horarios)].strip()

        vid = db.insertar("videos", {
            "producto_id": p["id"], "fecha_plan": dia.isoformat(), "horario": horario,
            "formato": formato, "gancho": kit["gancho"], "tipo_gancho": kit["tipo_gancho"],
            "prompt": kit["prompt"], "caption": kit["caption"], "hashtags": kit["hashtags"],
            "guion_voz": kit["linea_voz_ia"] if VOZ_IA else kit["guion_voz"], "estado": "planeado", "creado": db.now(),
        })
        imagen = (p["imagenes"] or "").split("|")[0]
        elegidos.append({"video_id": vid, "horario": horario, "producto": p["nombre"],
                         "url": p["url"], "imagen_inicial": imagen, **kit})

    carpeta = KITS_DIR / dia.isoformat()
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "kit.json").write_text(json.dumps(elegidos, ensure_ascii=False, indent=2), encoding="utf-8")
    (carpeta / "KIT.md").write_text(_markdown(dia, elegidos), encoding="utf-8")
    return carpeta


def _markdown(dia: date, items: list[dict]) -> str:
    out = [f"# Kit del {dia.strftime('%d/%m/%Y')} — {len(items)} videos\n",
           "Flow: Video · Ingredientes · Veo 3.1 Lite · 9:16 · x1 (10 créditos). Sube la foto real del producto. "
           "Genera de 12:00 a 7:00 (de 8 a 11 am Flow gratis suele bloquear video).\n"]
    for it in items:
        out += [
            f"\n## Video {it['video_id']} · {it['horario']} · {it['producto']}",
            f"- Formato: **{it['formato']}** · Gancho ({it['tipo_gancho']}): **{it['gancho']}**",
            f"- Imagen inicial: `{it['imagen_inicial']}`",
            f"- Enlace del producto: {it['url']}",
            "\n**Prompt (pégalo en Flow):**\n```\n" + it["prompt"] + "\n```",
            ("**Voz:** la dice la IA dentro del clip → \"" + it["linea_voz_ia"] + "\"" if VOZ_IA
             else "**Tu voz (grábala, ~15 s):**\n> " + it["guion_voz"]),
            "\n**Revisión antes de aprobar (cuadros 0.5 s · 4 s · 7.5 s):**\n" + "\n".join(
                f"- [ ] {q}" + ("" if critico else " *(se corrige en edición)*") for q, critico in prompts.QA_CHECKLIST),
            "\n**Descripción:**\n```\n" + it["caption"] + "\n" + it["hashtags"] + "\n```",
            "Al publicar: ✅ etiqueta 'Contenido generado por IA' · ✅ Agregar enlace → Productos → este producto",
        ]
    return "\n".join(out) + "\n"
