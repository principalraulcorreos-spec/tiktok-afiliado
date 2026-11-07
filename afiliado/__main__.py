"""CLI del sistema. Uso: python -m afiliado <comando> [opciones]   (python -m afiliado -h para ayuda)"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from . import db
from .config import CLIPS_DIR, KITS_DIR, VOICES_DIR

CAMPOS_PRODUCTO = ["tiktok_id", "nombre", "nombre_corto", "url", "categoria", "precio", "comision_pct", "ventas_30d", "ventas_7d",
                   "ventas_7d_prev", "calificacion", "num_resenas", "videos_afiliados", "demostrable",
                   "muestra_gratis", "descripcion", "beneficios", "problema", "producto_en", "problema_en",
                   "uso_en", "resultado_en", "soporte_en", "excluir_en", "imagenes", "en_vitrina", "estado"]
NUMERICOS = {"precio", "comision_pct", "calificacion"}
ENTEROS = {"ventas_30d", "ventas_7d", "ventas_7d_prev", "num_resenas", "videos_afiliados", "demostrable",
           "muestra_gratis", "en_vitrina"}


def _fecha(s: str | None, defecto_manana: bool = True) -> date:
    if s:
        return date.fromisoformat(s)
    return date.today() + timedelta(days=1 if defecto_manana else 0)


def _limpiar(fila: dict) -> dict:
    out = {}
    for k in CAMPOS_PRODUCTO:
        v = fila.get(k)
        if v in (None, ""):
            continue
        if k in NUMERICOS:
            v = float(str(v).replace("$", "").replace(",", "").replace("%", ""))
        elif k in ENTEROS:
            v = int(float(str(v).replace(",", "")))
        out[k] = v
    if not out.get("tiktok_id") and out.get("url"):
        m = re.search(r"(\d{15,})", out["url"])
        if m:
            out["tiktok_id"] = m.group(1)
    return out


def _archivo_para(carpeta: Path, fecha: date, video_id: int, exts: tuple[str, ...]) -> str | None:
    for base in (carpeta / fecha.isoformat(), carpeta):
        for e in exts:
            p = base / f"{video_id}{e}"
            if p.exists():
                return str(p)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="afiliado", description="Sistema de afiliado TikTok Shop con videos IA")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Crea la base de datos")
    a = sub.add_parser("agregar", help="Agrega/actualiza productos desde CSV o JSON (ver ejemplos/productos.csv)")
    a.add_argument("archivo")
    sub.add_parser("puntuar", help="Calcula el puntaje 0-100 de todos los productos")
    a = sub.add_parser("productos", help="Lista productos con puntaje y estado")
    a.add_argument("--estado")
    a = sub.add_parser("activar", help="Marca productos como activos y en vitrina")
    a.add_argument("ids", nargs="+", type=int)
    a = sub.add_parser("estado", help="Cambia el estado de un producto")
    a.add_argument("id", type=int)
    a.add_argument("nuevo", choices=["candidato", "activo", "escalar", "pausado", "descartado"])

    a = sub.add_parser("planear", help="Crea el kit del día (prompts, voces, descripciones)")
    a.add_argument("--fecha")
    a.add_argument("--n", type=int)
    a = sub.add_parser("clip", help="Registra el clip que bajaste de Flow para un video")
    a.add_argument("video_id", type=int)
    a.add_argument("ruta")
    a = sub.add_parser("voz", help="Registra tu voz grabada para un video")
    a.add_argument("video_id", type=int)
    a.add_argument("ruta")
    sub.add_parser("listar-modelos", help="Modelos Veo disponibles en tu cuenta de Gemini API")
    a = sub.add_parser("generar", help="Genera el clip con Veo por API (de pago)")
    a.add_argument("video_id", type=int)
    a.add_argument("--modelo")
    a = sub.add_parser("generar-dia", help="Genera por API todos los clips de un día")
    a.add_argument("--fecha")
    a.add_argument("--modelo")
    a = sub.add_parser("editar", help="Arma el video final de un video")
    a.add_argument("video_id", type=int)
    a.add_argument("--recorte", type=float, default=0.0, help="segundos a cortar al inicio del clip")
    a.add_argument("--recorte-final", type=float, default=0.8, help="segundos a cortar al final (Veo deriva)")
    a = sub.add_parser("editar-dia", help="Arma todos los videos del día (toma clips/voces por nombre <id>.mp4)")
    a.add_argument("--fecha")
    a.add_argument("--recorte", type=float, default=0.0)
    a.add_argument("--recorte-final", type=float, default=0.8)

    sub.add_parser("tiktok-login", help="Imprime la URL para autorizar tu cuenta de TikTok")
    a = sub.add_parser("tiktok-codigo", help="Pega la URL de regreso para guardar el token")
    a.add_argument("url")
    a = sub.add_parser("borrador", help="Sube un video a tu bandeja de TikTok (borrador)")
    a.add_argument("video_id", type=int)
    a = sub.add_parser("borradores-dia", help="Sube todos los videos editados del día como borradores")
    a.add_argument("--fecha")
    a = sub.add_parser("publicar", help="Publica directo con etiqueta IA (sin producto vinculado)")
    a.add_argument("video_id", type=int)
    a = sub.add_parser("publicado", help="Marca un video como publicado y guarda su enlace")
    a.add_argument("video_id", type=int)
    a.add_argument("--link", required=True)

    sub.add_parser("sync-metricas", help="Trae vistas/likes por API")
    a = sub.add_parser("importar-metricas", help="Importa CSV/XLSX de TikTok Studio o del Centro de afiliados")
    a.add_argument("archivo")
    a.add_argument("--fuente", default="csv")
    a.add_argument("--fecha")
    sub.add_parser("plantilla-metricas", help="Crea data/plantilla_metricas.csv para captura manual")
    a = sub.add_parser("evaluar", help="Evaluación mensual y nuevas reglas")
    a.add_argument("--mes", help="AAAA-MM (por defecto, el mes anterior)")
    a = sub.add_parser("dia", help="Rutina automática: planear mañana + (generar por API) + editar lo que tenga clip")
    a.add_argument("--api", action="store_true", help="generar clips con Veo API")

    args = ap.parse_args(argv)
    db.init()

    if args.cmd == "init":
        print("Base de datos lista:", db.DB_PATH)

    elif args.cmd == "agregar":
        ruta = Path(args.archivo)
        filas = json.loads(ruta.read_text(encoding="utf-8")) if ruta.suffix == ".json" else \
            list(csv.DictReader(ruta.open(encoding="utf-8-sig")))
        for f in filas:
            pid = db.upsert_producto(_limpiar(f))
            print(f"  producto {pid}: {f.get('nombre')}")
        from .scoring import puntuar_todos
        puntuar_todos()

    elif args.cmd == "puntuar":
        from .scoring import puntuar_todos
        for pid, nombre, score, motivos in puntuar_todos():
            extra = f"  ✗ {'; '.join(motivos)}" if motivos else ""
            print(f"{pid:>4} {score:>5.1f}  {nombre[:50]}{extra}")

    elif args.cmd == "productos":
        filas = db.productos((args.estado,)) if args.estado else db.productos()
        for p in filas:
            print(f"{p['id']:>4} {p['puntaje'] or 0:>5.1f} {p['estado']:<11} vitrina={p['en_vitrina']} "
                  f"${p['precio'] or 0:>6.0f} {p['comision_pct'] or 0:>4.0f}%  {p['nombre'][:45]}")

    elif args.cmd == "activar":
        for i in args.ids:
            db.actualizar("productos", i, estado="activo", en_vitrina=1)
        print("Activados:", args.ids, "(confirma que ya están en tu vitrina de TikTok)")

    elif args.cmd == "estado":
        db.actualizar("productos", args.id, estado=args.nuevo)

    elif args.cmd == "planear":
        from .planner import planear
        carpeta = planear(_fecha(args.fecha), args.n)
        print("Kit listo:", carpeta / "KIT.md")

    elif args.cmd == "clip":
        db.actualizar("videos", args.video_id, clip_path=str(Path(args.ruta).resolve()), motor="flow", estado="clip_ok")

    elif args.cmd == "voz":
        db.actualizar("videos", args.video_id, voz_path=str(Path(args.ruta).resolve()))

    elif args.cmd == "listar-modelos":
        from .veo import listar_modelos
        print("\n".join(listar_modelos()))

    elif args.cmd == "generar":
        from .veo import generar
        print(generar(args.video_id, args.modelo))

    elif args.cmd == "generar-dia":
        from .veo import generar
        f = _fecha(args.fecha)
        for v in db.query("SELECT id FROM videos WHERE fecha_plan=? AND estado='planeado'", (f.isoformat(),)):
            try:
                print("✓", generar(v["id"], args.modelo))
            except Exception as e:  # sigue con el siguiente
                print(f"✗ video {v['id']}: {e}", file=sys.stderr)

    elif args.cmd == "editar":
        from .editor import editar_video
        print(editar_video(args.video_id, args.recorte, recorte_final=args.recorte_final))

    elif args.cmd in ("editar-dia", "dia"):
        from .editor import editar_video
        f = _fecha(getattr(args, "fecha", None), defecto_manana=False)
        if args.cmd == "dia":
            from .planner import planear
            manana = date.today() + timedelta(days=1)
            if not db.query("SELECT 1 FROM videos WHERE fecha_plan=?", (manana.isoformat(),)):
                print("Kit de mañana:", planear(manana) / "KIT.md")
            if args.api:
                from .veo import generar
                for v in db.query("SELECT id FROM videos WHERE fecha_plan=? AND estado='planeado'",
                                  (manana.isoformat(),)):
                    try:
                        generar(v["id"])
                    except Exception as e:
                        print(f"✗ Veo video {v['id']}: {e}", file=sys.stderr)
        for v in db.query("SELECT * FROM videos WHERE fecha_plan=? AND estado IN ('planeado','clip_ok','editado')",
                          (f.isoformat(),)):
            clip = v["clip_path"] or _archivo_para(CLIPS_DIR, f, v["id"], (".mp4", ".mov"))
            voz = v["voz_path"] or _archivo_para(VOICES_DIR, f, v["id"], (".m4a", ".mp3", ".wav", ".aac", ".ogg"))
            if not clip:
                print(f"… video {v['id']}: falta clip (guárdalo como data/clips/{f}/{v['id']}.mp4)")
                continue
            db.actualizar("videos", v["id"], clip_path=clip, voz_path=voz, estado="clip_ok")
            try:
                print("✓", editar_video(v["id"], getattr(args, "recorte", 0.0),
                                         recorte_final=getattr(args, "recorte_final", 0.8)), "(con voz)" if voz else "(SIN voz)")
            except Exception as e:
                print(f"✗ video {v['id']}: {e}", file=sys.stderr)

    elif args.cmd == "tiktok-login":
        from .publisher import url_autorizacion
        print("Abre esta URL, autoriza y copia la URL a la que te regresa:\n", url_autorizacion())

    elif args.cmd == "tiktok-codigo":
        from .publisher import canjear_codigo
        canjear_codigo(args.url)
        print("Token guardado.")

    elif args.cmd == "borrador":
        from .publisher import subir_borrador
        print("publish_id:", subir_borrador(args.video_id))

    elif args.cmd == "borradores-dia":
        from .publisher import subir_borrador
        f = _fecha(args.fecha, defecto_manana=False)
        for v in db.query("SELECT id FROM videos WHERE fecha_plan=? AND estado='editado'", (f.isoformat(),)):
            print(v["id"], "→", subir_borrador(v["id"]))

    elif args.cmd == "publicar":
        from .publisher import publicar_directo
        print("publish_id:", publicar_directo(args.video_id))

    elif args.cmd == "publicado":
        m = re.search(r"/video/(\d+)", args.link)
        db.actualizar("videos", args.video_id, tiktok_video_id=m.group(1) if m else args.link,
                      estado="publicado", publicado=datetime.now().isoformat(timespec="minutes"))

    elif args.cmd == "sync-metricas":
        from .metrics import sincronizar_api
        print("Videos actualizados:", sincronizar_api())

    elif args.cmd == "importar-metricas":
        from .metrics import importar_archivo
        ok, sin = importar_archivo(args.archivo, args.fuente, args.fecha)
        print(f"Filas importadas: {ok} · sin video asociado: {sin}")

    elif args.cmd == "plantilla-metricas":
        from .metrics import plantilla
        print(plantilla(db.DB_PATH.parent / "plantilla_metricas.csv"))

    elif args.cmd == "evaluar":
        from .evaluate import evaluar
        reporte, _ = evaluar(args.mes)
        print(reporte)


if __name__ == "__main__":
    main()
