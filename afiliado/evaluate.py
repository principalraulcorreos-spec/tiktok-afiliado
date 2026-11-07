"""Evaluación mensual: mide, decide y reescribe las reglas del siguiente ciclo (data/reglas.json).

Métricas por video (última lectura de cada fuente, combinadas):
  CTR carrito = clics_producto / vistas      Conversión = pedidos / clics_producto
  RPM = comisión por cada 1,000 vistas       Retención = % que vio completo

Decisiones:
  Producto  → escalar / mantener / pausar / descartar
  Formato   → reparte los 4 espacios diarios según RPM (mín. 10 % a cada uno para seguir probando)
  Gancho    → pesos por CTR
  Horario   → los 4 horarios con más vistas promedio
  Categoría → bono +5 a la mejor, −5 a la peor (con datos suficientes)
  Pesos del puntaje de productos → se ajustan ±2 según qué criterio correlaciona con el RPM real
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import date

from . import db, prompts
from .config import REPORTS_DIR, RULES_PATH, TIPO_CAMBIO
from .scoring import PESOS_BASE, cargar_reglas, criterios

UMBRAL = {
    "min_videos_decidir": 3,        # no juzgues un producto con menos de 3 videos
    "escalar_rpm": 15.0,            # MXN de comisión por 1,000 vistas
    "escalar_comision": 300.0,      # o al menos $300 MXN de comisión en el mes
    "descartar_ctr": 0.5,           # % — con 4+ videos, 0 pedidos y CTR < 0.5 % → descartar
    "pausar_rpm": 3.0,              # con 4+ videos y RPM < $3 → pausar
    "retencion_baja": 25.0,         # % — si el promedio cae debajo, acortar videos / gancho más fuerte
    "ctr_bajo": 0.8,                # % — si el promedio cae debajo, revisar precio/oferta y CTA
}


def _mes_anterior(hoy: date) -> str:
    y, m = (hoy.year, hoy.month - 1) if hoy.month > 1 else (hoy.year - 1, 12)
    return f"{y:04d}-{m:02d}"


def datos_videos(mes: str) -> list[dict]:
    """Une cada video del mes con su última lectura de cada fuente."""
    vids = db.query(
        "SELECT v.*, p.nombre producto, p.categoria FROM videos v JOIN productos p ON p.id=v.producto_id "
        "WHERE substr(COALESCE(v.publicado, v.fecha_plan),1,7)=? AND v.estado IN ('publicado','borrador')",
        (mes,))
    salida = []
    campos = ["vistas", "likes", "comentarios", "compartidos", "guardados", "tiempo_prom_seg",
              "retencion_pct", "clics_producto", "pedidos", "gmv", "comision"]
    for v in vids:
        filas = db.query("SELECT * FROM metricas WHERE video_id=? ORDER BY fecha", (v["id"],))
        m = {c: None for c in campos}
        for f in filas:                      # la lectura más reciente gana, campo por campo
            for c in campos:
                if f[c] is not None:
                    m[c] = f[c]
        d = dict(v) | {k: (m[k] or 0) for k in campos}
        d["ctr"] = 100 * d["clics_producto"] / d["vistas"] if d["vistas"] else 0
        d["cvr"] = 100 * d["pedidos"] / d["clics_producto"] if d["clics_producto"] else 0
        d["rpm"] = 1000 * d["comision"] / d["vistas"] if d["vistas"] else 0
        salida.append(d)
    return salida


def _agrupar(videos: list[dict], clave: str) -> dict[str, dict]:
    g = defaultdict(list)
    for v in videos:
        g[v[clave]].append(v)
    res = {}
    for k, vs in g.items():
        vistas = sum(v["vistas"] for v in vs)
        clics = sum(v["clics_producto"] for v in vs)
        res[k] = {
            "videos": len(vs), "vistas": vistas, "clics": clics,
            "pedidos": sum(v["pedidos"] for v in vs), "comision": sum(v["comision"] for v in vs),
            "costo_mxn": sum((v["costo_usd"] or 0) for v in vs) * TIPO_CAMBIO,
            "ctr": 100 * clics / vistas if vistas else 0,
            "rpm": 1000 * sum(v["comision"] for v in vs) / vistas if vistas else 0,
            "retencion": statistics.mean([v["retencion_pct"] for v in vs]) if vs else 0,
            "producto_id": vs[0]["producto_id"],
        }
    return res


def _pesos_relativos(stats: dict[str, dict], opciones: list[str], minimo: float = 0.10) -> dict[str, float]:
    con_datos = {o: stats[o]["rpm"] if o in stats and stats[o]["videos"] >= 5 else None for o in opciones}
    if sum(1 for x in con_datos.values() if x is not None) < 2:
        return {o: 1.0 for o in opciones}
    base = statistics.mean([x for x in con_datos.values() if x is not None]) or 1
    w = {o: (x / base if x is not None else 1.0) for o, x in con_datos.items()}
    total = sum(w.values()) or 1
    w = {o: max(minimo, x / total) for o, x in w.items()}
    total = sum(w.values())
    return {o: round(x / total, 3) for o, x in w.items()}


def _correlacion(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 3 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return 0.0
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)
    return cov / (statistics.pstdev(xs) * statistics.pstdev(ys))


def evaluar(mes: str | None = None) -> tuple[str, dict]:
    mes = mes or _mes_anterior(date.today())
    reglas = cargar_reglas()
    videos = datos_videos(mes)
    if not videos:
        return f"Sin videos publicados con métricas en {mes}.", reglas

    por_prod = _agrupar(videos, "producto")
    por_formato = _agrupar(videos, "formato")
    por_gancho = _agrupar(videos, "tipo_gancho")
    por_horario = _agrupar(videos, "horario")
    por_cat = _agrupar(videos, "categoria")
    decisiones = []

    # 1) Productos
    for nombre, s in por_prod.items():
        accion, motivo = "mantener", "datos insuficientes" if s["videos"] < UMBRAL["min_videos_decidir"] else "rendimiento medio"
        if s["videos"] >= UMBRAL["min_videos_decidir"] and (
                s["rpm"] >= UMBRAL["escalar_rpm"] or s["comision"] >= UMBRAL["escalar_comision"]):
            accion, motivo = "escalar", f"RPM ${s['rpm']:.1f} / comisión ${s['comision']:.0f}"
        elif s["videos"] >= 4 and s["pedidos"] == 0 and s["ctr"] < UMBRAL["descartar_ctr"]:
            accion, motivo = "descartar", f"0 pedidos y CTR {s['ctr']:.2f}% en {s['videos']} videos"
        elif s["videos"] >= 4 and s["rpm"] < UMBRAL["pausar_rpm"]:
            accion, motivo = "pausar", f"RPM ${s['rpm']:.1f} bajo"
        estado = {"escalar": "escalar", "descartar": "descartado", "pausar": "pausado"}.get(accion)
        if estado:
            db.actualizar("productos", s["producto_id"], estado=estado)
        decisiones.append(("producto", nombre, accion, motivo))

    # 2) Formatos, ganchos, horarios
    reglas["formatos"] = _pesos_relativos(por_formato, prompts.FORMATOS)
    tipos = sorted({t for ts in prompts.FORMATO_A_GANCHOS.values() for t in ts})
    g = {t: (por_gancho[t]["ctr"] if t in por_gancho and por_gancho[t]["videos"] >= 5 else None) for t in tipos}
    if sum(x is not None for x in g.values()) >= 2:
        media = statistics.mean([x for x in g.values() if x is not None]) or 1
        reglas["ganchos"] = {t: round(max(0.2, (x / media) if x is not None else 1.0), 2) for t, x in g.items()}
    con_vistas = {h: s["vistas"] / s["videos"] for h, s in por_horario.items() if s["videos"] >= 5}
    if len(con_vistas) >= 4:
        reglas["horarios_top"] = sorted(con_vistas, key=con_vistas.get, reverse=True)[:4]
    for k, w in reglas["formatos"].items():
        decisiones.append(("formato", k, "ajustar", f"peso {w}"))

    # 3) Categorías
    cats = {c: s for c, s in por_cat.items() if s["videos"] >= 6}
    if len(cats) >= 2:
        mejor = max(cats, key=lambda c: cats[c]["rpm"])
        peor = min(cats, key=lambda c: cats[c]["rpm"])
        bono = reglas.setdefault("bono_categoria", {})
        bono[(mejor or "").lower()] = min(10, bono.get((mejor or "").lower(), 0) + 5)
        bono[(peor or "").lower()] = max(-10, bono.get((peor or "").lower(), 0) - 5)
        decisiones += [("categoria", mejor, "escalar", "mejor RPM"), ("categoria", peor, "ajustar", "peor RPM")]

    # 4) Pesos del puntaje: ¿qué criterio predijo mejor el RPM real?
    prods = [s for s in por_prod.values() if s["videos"] >= UMBRAL["min_videos_decidir"]]
    if len(prods) >= 6:
        filas = {p["id"]: p for p in db.productos()}
        pesos = {**PESOS_BASE, **reglas.get("pesos", {})}
        crit = {s["producto_id"]: criterios(filas[s["producto_id"]]) for s in prods if s["producto_id"] in filas}
        rpms = {s["producto_id"]: s["rpm"] for s in prods}
        for k in PESOS_BASE:
            ids = list(crit)
            r = _correlacion([crit[i][k] for i in ids], [rpms[i] for i in ids])
            if r > 0.3:
                pesos[k] = min(25, pesos[k] + 2)
            elif r < -0.3:
                pesos[k] = max(5, pesos[k] - 2)
        reglas["pesos"] = pesos

    # 5) Alertas de contenido
    alertas = []
    ret = statistics.mean([v["retencion_pct"] for v in videos])
    ctr = statistics.mean([v["ctr"] for v in videos])
    if ret and ret < UMBRAL["retencion_baja"]:
        alertas.append(f"Retención promedio {ret:.1f}% < {UMBRAL['retencion_baja']}%: usa clips de 6 s, "
                       "producto visible desde el segundo 0 y gancho más directo.")
    if ctr < UMBRAL["ctr_bajo"]:
        alertas.append(f"CTR al carrito {ctr:.2f}% < {UMBRAL['ctr_bajo']}%: menciona el precio en voz, "
                       "muestra el resultado antes y termina con 'toca el carrito naranja'.")
    reglas["alertas"] = alertas
    reglas["actualizado"] = date.today().isoformat()
    reglas["mes_evaluado"] = mes
    RULES_PATH.write_text(json.dumps(reglas, ensure_ascii=False, indent=2), encoding="utf-8")

    for tipo, clave, accion, motivo in decisiones:
        db.insertar("decisiones", {"mes": mes, "tipo": tipo, "clave": str(clave), "accion": accion,
                                   "motivo": motivo, "creado": db.now()})

    reporte = _reporte(mes, videos, por_prod, por_formato, por_gancho, decisiones, alertas, reglas)
    (REPORTS_DIR / f"evaluacion_{mes}.md").write_text(reporte, encoding="utf-8")
    return reporte, reglas


def _tabla(titulo: str, stats: dict[str, dict]) -> list[str]:
    out = [f"\n## {titulo}\n", "| | Videos | Vistas | CTR % | Pedidos | Comisión $ | RPM $ | Retención % |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k, s in sorted(stats.items(), key=lambda x: -x[1]["rpm"]):
        out.append(f"| {k} | {s['videos']} | {s['vistas']:,.0f} | {s['ctr']:.2f} | {s['pedidos']:.0f} | "
                   f"{s['comision']:,.0f} | {s['rpm']:.1f} | {s['retencion']:.1f} |")
    return out


def _reporte(mes, videos, por_prod, por_formato, por_gancho, decisiones, alertas, reglas) -> str:
    total_com = sum(v["comision"] for v in videos)
    total_vis = sum(v["vistas"] for v in videos)
    costo = sum((v["costo_usd"] or 0) for v in videos) * TIPO_CAMBIO
    top = sorted(videos, key=lambda v: -v["comision"])[:5]
    out = [f"# Evaluación {mes}", "",
           f"- Videos: **{len(videos)}** · Vistas: **{total_vis:,.0f}** · Comisión: **${total_com:,.0f} MXN**",
           f"- Costo IA estimado: **${costo:,.0f} MXN** · Ganancia neta: **${total_com - costo:,.0f} MXN**",
           f"- RPM global: **${(1000 * total_com / total_vis if total_vis else 0):.1f}** por 1,000 vistas"]
    out += _tabla("Productos", por_prod) + _tabla("Formatos", por_formato) + _tabla("Ganchos", por_gancho)
    out += ["\n## Top 5 videos", "| Video | Producto | Formato | Gancho | Vistas | Comisión $ |", "|---|---|---|---|---:|---:|"]
    out += [f"| {v['id']} | {v['producto']} | {v['formato']} | {v['gancho']} | {v['vistas']:,.0f} | {v['comision']:,.0f} |"
            for v in top]
    out += ["\n## Decisiones aplicadas"] + [f"- **{t}** `{c}` → **{a}** ({m})" for t, c, a, m in decisiones]
    out += ["\n## Alertas"] + ([f"- {a}" for a in alertas] or ["- Ninguna"])
    out += ["\n## Reglas nuevas (data/reglas.json)", "```json", json.dumps(reglas, ensure_ascii=False, indent=2), "```"]
    return "\n".join(out) + "\n"
