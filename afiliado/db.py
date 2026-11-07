"""Base de datos SQLite: productos, videos, métricas y decisiones."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS productos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tiktok_id       TEXT UNIQUE,              -- id del producto en TikTok Shop (del enlace)
    nombre          TEXT NOT NULL,
    nombre_corto    TEXT,                     -- como lo dices en voz alta: "esta plancha"
    url             TEXT,
    categoria       TEXT,
    precio          REAL,                     -- MXN
    comision_pct    REAL,                     -- 0-100
    ventas_30d      INTEGER,                  -- ventas recientes del producto (catálogo de afiliados)
    ventas_7d       INTEGER,
    ventas_7d_prev  INTEGER,                  -- semana anterior, para tendencia
    calificacion    REAL,                     -- 0-5
    num_resenas     INTEGER,
    videos_afiliados INTEGER,                 -- cuántos videos de afiliados ya tiene (competencia)
    demostrable     INTEGER,                  -- 1-5: ¿se entiende en 2 s en video?
    muestra_gratis  INTEGER DEFAULT 0,        -- 1 si ofrece muestra
    descripcion     TEXT,
    beneficios      TEXT,                     -- separados por "|"
    problema        TEXT,                     -- problema que resuelve (para el guion)
    producto_en     TEXT,                     -- descripción visual en inglés (ej. "black ceramic flat iron")
    problema_en     TEXT,                     -- el problema, visual y en inglés (para la IA de video)
    uso_en          TEXT,                     -- cómo se usa, en inglés
    resultado_en    TEXT,                     -- resultado realista, en inglés
    soporte_en      TEXT,                     -- física: cómo se sostiene/queda el producto (R3)
    excluir_en      TEXT,                     -- objetos que NO vienen y la IA suele inventar (R4)
    imagenes        TEXT,                     -- rutas separadas por "|"
    en_vitrina      INTEGER DEFAULT 0,
    puntaje         REAL,
    estado          TEXT DEFAULT 'candidato', -- candidato | activo | escalar | pausado | descartado
    notas           TEXT,
    creado          TEXT,
    actualizado     TEXT
);

CREATE TABLE IF NOT EXISTS videos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id     INTEGER REFERENCES productos(id),
    fecha_plan      TEXT,                     -- día para el que se planeó
    horario         TEXT,
    formato         TEXT,                     -- problema_solucion | antes_despues | unboxing | pov
    gancho          TEXT,                     -- texto del gancho (primeros 2 s)
    tipo_gancho     TEXT,
    prompt          TEXT,
    caption         TEXT,
    hashtags        TEXT,
    guion_voz       TEXT,
    motor           TEXT,                     -- flow | veo_api
    costo_usd       REAL DEFAULT 0,
    clip_path       TEXT,
    voz_path        TEXT,
    final_path      TEXT,
    tiktok_video_id TEXT,
    publish_id      TEXT,
    publicado       TEXT,                     -- fecha/hora real de publicación
    etiqueta_ia     INTEGER DEFAULT 1,
    estado          TEXT DEFAULT 'planeado',  -- planeado | clip_ok | editado | borrador | publicado | descartado
    creado          TEXT
);

CREATE TABLE IF NOT EXISTS metricas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id            INTEGER REFERENCES videos(id),
    fecha               TEXT,                 -- fecha de la lectura
    vistas              INTEGER,
    likes               INTEGER,
    comentarios         INTEGER,
    compartidos         INTEGER,
    guardados           INTEGER,
    tiempo_prom_seg     REAL,                 -- tiempo promedio visto
    retencion_pct       REAL,                 -- % que vio completo
    clics_producto      INTEGER,              -- clics al carrito
    pedidos             INTEGER,
    gmv                 REAL,                 -- MXN vendidos
    comision            REAL,                 -- MXN ganados
    fuente              TEXT,                 -- api | csv_studio | csv_afiliados | manual
    UNIQUE(video_id, fecha, fuente)
);

CREATE TABLE IF NOT EXISTS decisiones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mes         TEXT,
    tipo        TEXT,                         -- producto | formato | gancho | horario | categoria
    clave       TEXT,
    accion      TEXT,                         -- escalar | mantener | descartar | ajustar
    motivo      TEXT,
    creado      TEXT
);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def conectar():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init() -> None:
    with conectar() as con:
        con.executescript(SCHEMA)


def upsert_producto(datos: dict) -> int:
    datos = {k: v for k, v in datos.items() if v is not None}
    datos["actualizado"] = now()
    with conectar() as con:
        existe = None
        if datos.get("tiktok_id"):
            existe = con.execute("SELECT id FROM productos WHERE tiktok_id=?", (datos["tiktok_id"],)).fetchone()
        if existe:
            sets = ", ".join(f"{k}=?" for k in datos)
            con.execute(f"UPDATE productos SET {sets} WHERE id=?", (*datos.values(), existe["id"]))
            return existe["id"]
        datos["creado"] = now()
        cols = ", ".join(datos)
        qs = ", ".join("?" for _ in datos)
        cur = con.execute(f"INSERT INTO productos ({cols}) VALUES ({qs})", tuple(datos.values()))
        return cur.lastrowid


def productos(estados: tuple[str, ...] | None = None) -> list[sqlite3.Row]:
    with conectar() as con:
        if estados:
            q = f"SELECT * FROM productos WHERE estado IN ({','.join('?' for _ in estados)}) ORDER BY puntaje DESC"
            return con.execute(q, estados).fetchall()
        return con.execute("SELECT * FROM productos ORDER BY puntaje DESC").fetchall()


def actualizar(tabla: str, id_: int, **campos) -> None:
    sets = ", ".join(f"{k}=?" for k in campos)
    with conectar() as con:
        con.execute(f"UPDATE {tabla} SET {sets} WHERE id=?", (*campos.values(), id_))


def insertar(tabla: str, datos: dict) -> int:
    cols = ", ".join(datos)
    qs = ", ".join("?" for _ in datos)
    with conectar() as con:
        return con.execute(f"INSERT INTO {tabla} ({cols}) VALUES ({qs})", tuple(datos.values())).lastrowid


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with conectar() as con:
        return con.execute(sql, params).fetchall()
