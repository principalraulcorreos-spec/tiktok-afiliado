"""Puntaje de productos (0-100) con filtros duros.

Cada criterio da 0-1 y se multiplica por su peso. Los pesos y los bonos por
categoría los ajusta la evaluación mensual en data/reglas.json.
"""
from __future__ import annotations

import json
import math

from . import db
from .config import RULES_PATH

PESOS_BASE = {
    "comision_pct": 15,      # % de comisión
    "comision_mxn": 15,      # pesos que ganas por venta
    "precio": 10,            # precio en zona de compra impulsiva
    "ventas": 15,            # ventas de los últimos 30 días
    "tendencia": 10,         # ventas 7 d vs 7 d anteriores
    "calificacion": 10,      # estrellas
    "competencia": 10,       # ventas por cada video de afiliado existente
    "demostrable": 15,       # se entiende en 2 segundos en video
}

# Categorías que en TikTok Shop México tienen reglas estrictas o convierten mal con IA.
CATEGORIAS_PROHIBIDAS = {"suplementos", "bajar de peso", "medicamentos", "dispositivos medicos", "armas"}
CATEGORIAS_RIESGO = {"cosmeticos", "skincare", "moda", "ropa", "fajas", "alimentos"}


def cargar_reglas() -> dict:
    if RULES_PATH.exists():
        return json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return {}


def _lineal(x, malo, bueno):
    if x is None:
        return 0.5  # sin dato: neutral
    if bueno == malo:
        return 1.0
    return max(0.0, min(1.0, (x - malo) / (bueno - malo)))


def filtros_duros(p) -> list[str]:
    """Devuelve la lista de motivos por los que un producto NO se debe promocionar."""
    motivos = []
    cat = (p["categoria"] or "").lower()
    if any(c in cat for c in CATEGORIAS_PROHIBIDAS):
        motivos.append(f"categoría prohibida/restringida: {cat}")
    if p["calificacion"] is not None and p["calificacion"] < 4.3:
        motivos.append("calificación menor a 4.3 (devoluciones y quejas)")
    if p["num_resenas"] is not None and p["num_resenas"] < 10:
        motivos.append("menos de 10 reseñas")
    if p["comision_pct"] is not None and p["comision_pct"] < 8:
        motivos.append("comisión menor a 8%")
    if p["precio"] is not None and (p["precio"] < 80 or p["precio"] > 1500):
        motivos.append("precio fuera de $80-$1,500 MXN")
    if p["demostrable"] is not None and p["demostrable"] <= 2:
        motivos.append("difícil de mostrar en video (demostrable ≤ 2)")
    return motivos


def criterios(p) -> dict[str, float]:
    precio = p["precio"]
    com_mxn = (precio or 0) * (p["comision_pct"] or 0) / 100 if precio and p["comision_pct"] else None

    # Precio: zona dulce $150-$600 MXN = 1.0, cae fuera de ella
    if precio is None:
        s_precio = 0.5
    elif 150 <= precio <= 600:
        s_precio = 1.0
    elif precio < 150:
        s_precio = _lineal(precio, 80, 150)
    else:
        s_precio = 1 - _lineal(precio, 600, 1500)

    # Ventas en escala logarítmica: 50 ventas = 0, 2000+ = 1
    v = p["ventas_30d"]
    s_ventas = 0.5 if v is None else _lineal(math.log10(max(v, 1)), math.log10(50), math.log10(2000))

    # Tendencia: crecimiento semanal -30% = 0, +50% = 1
    if p["ventas_7d"] is not None and p["ventas_7d_prev"]:
        crec = (p["ventas_7d"] - p["ventas_7d_prev"]) / p["ventas_7d_prev"]
        s_tend = _lineal(crec, -0.3, 0.5)
    else:
        s_tend = 0.5

    # Competencia: ventas por video de afiliado. 2 = saturado, 30+ = hueco
    if v is not None and p["videos_afiliados"]:
        s_comp = _lineal(math.log10(max(v / p["videos_afiliados"], 0.1)), math.log10(2), math.log10(30))
    else:
        s_comp = 0.5

    return {
        "comision_pct": _lineal(p["comision_pct"], 8, 25),
        "comision_mxn": _lineal(com_mxn, 15, 80),
        "precio": s_precio,
        "ventas": s_ventas,
        "tendencia": s_tend,
        "calificacion": _lineal(p["calificacion"], 4.3, 4.8),
        "competencia": s_comp,
        "demostrable": _lineal(p["demostrable"], 2, 5),
    }


def puntuar(p, reglas: dict | None = None) -> tuple[float, dict, list[str]]:
    reglas = reglas if reglas is not None else cargar_reglas()
    pesos = {**PESOS_BASE, **reglas.get("pesos", {})}
    c = criterios(p)
    total_peso = sum(pesos.values())
    score = sum(c[k] * pesos[k] for k in pesos) / total_peso * 100

    cat = (p["categoria"] or "").lower()
    score += reglas.get("bono_categoria", {}).get(cat, 0)
    if p["muestra_gratis"]:
        score += 3  # con muestra puedes grabar tu toma real
    if any(r in cat for r in CATEGORIAS_RIESGO):
        score -= 5
    motivos = filtros_duros(p)
    if motivos:
        score = 0
    return round(max(0, min(100, score)), 1), c, motivos


def puntuar_todos() -> list[tuple]:
    reglas = cargar_reglas()
    salida = []
    for p in db.productos():
        score, c, motivos = puntuar(p, reglas)
        estado = p["estado"]
        if motivos and estado == "candidato":
            estado = "descartado"
        db.actualizar("productos", p["id"], puntaje=score, estado=estado,
                      notas="; ".join(motivos) if motivos else p["notas"])
        salida.append((p["id"], p["nombre"], score, motivos))
    return sorted(salida, key=lambda x: -x[2])
