"""Plantillas: prompt de video (Veo / Flow), guion de voz, gancho, descripción y hashtags.

Reglas que todas las plantillas respetan (políticas TikTok Shop México):
- El producto se genera A PARTIR DE SU FOTO REAL (imagen inicial) y no cambia de forma, color ni tamaño.
- Sin efectos imposibles, sin resultados instantáneos exagerados, sin doctores ni "expertos".
- Sin texto ni logos generados (el texto lo pone el editor).
- Tu voz narra: el creador "habla" en el video.
"""
from __future__ import annotations

import random
import re
import unicodedata

FORMATOS = ["problema_solucion", "antes_despues", "unboxing", "pov"]

# Escenarios donde el producto tiene sentido. Se elige por categoría.
ESCENARIOS = {
    "hogar": "a tidy Mexican home kitchen with warm daylight from a window",
    "cocina": "a real Mexican home kitchen countertop with daylight",
    "limpieza": "a real home bathroom / laundry area with natural light",
    "belleza": "a bedroom vanity table with soft daylight (no mirror in frame, so no face is reflected)",
    "cabello": "a bedroom vanity table with soft daylight (no mirror in frame, so no face is reflected)",
    "mascotas": "a cozy living room floor with a friendly dog",
    "auto": "a home garage with a parked car, daylight",
    "tecnologia": "a clean desk with a laptop, daylight",
    "fiestas": "a simple Mexican home with a plain white wall and a wooden table, natural daylight",
    "bodega": "a small warehouse with stacked cardboard boxes and several identical units of the product on a table",
}

# ---------------------------------------------------------------------------
# ESTÁNDAR DE PROMPT v2 (aprendido de las pruebas del 15-oct-2026, ver ESTANDAR_PROMPTS.md)
# Bloques fijos, en este orden. Cada regla viene de un error real:
#  R1 producto visible desde el cuadro 0        (plancha: entró hasta el seg 4)
#  R2 sin cara "de principio a fin" + recorte   (globos v1 y v2: aparece la persona al final)
#  R3 física explícita: cómo se sostiene        (globos v1: un globo flotando sin helio)
#  R4 lista EXCLUDE de lo que NO viene          (globos v1: letras HAPPY BIRTHDAY en la mesa)
#  R5 material descrito en cada estado          (globos v1: desinflados parecían papel metálico)
#  R6 una sola toma continua, máx. 3 momentos   (menos deformaciones)
#  R11 toma cenital + "off-screen narrator" (P9 v1: con voz, Veo mostró a la mujer hablando a cámara)
#  R7 voz: frase exacta entre comillas, ≤ 20 palabras, "natural Mexican Spanish"
# ---------------------------------------------------------------------------
ENCUADRE = ("FRAMING: filmed from directly above or close on the hands; only the product and a woman's hands and "
            "forearms are in frame; no person's head, face, mouth, hair or body is ever in frame, from the first frame to the last frame.")
EXCLUIR_BASE = ("no other products, no letters, banners or signs, no patterned backgrounds with text, "
                "no on-screen text, no subtitles, no logos, no watermarks")
AUDIO_SIN_VOZ = "AUDIO: no dialogue; only natural ambient sounds of the action and light upbeat background music."
AUDIO_CON_VOZ = ("AUDIO: excited, euphoric young woman's voice-over (off-screen narrator, nobody speaks on camera) in natural Mexican Spanish, fast and energetic like sharing an amazing find, says exactly: "
                 '"{linea}" She finishes speaking before the 7-second mark. Light upbeat background music.')

# Cada formato define los 3 momentos. Placeholders: {producto} {problema} {uso} {resultado}
# El producto se describe completo UNA sola vez (momento 1); después es "it" (evita que la IA
# lo "re-imagine" a mitad del clip y acorta el prompt).
MOMENTOS = {
    "problema_solucion": (
        "a woman's hands already hold the {producto}; in the same frame: {problema}",
        "her hands use it: {uso}",
        "{resultado}",
    ),
    "antes_despues": (
        "hands hold up the {producto} next to the 'before' state: {problema}",
        "her hands use it: {uso}",
        "the 'after', side by side with an untreated part: {resultado}",
    ),
    "unboxing": (
        "hands hold the {producto}, just taken out of an open plain brown shipping box",
        "hands turn it slowly to show three angles and close-ups of its details",
        "first real use: {uso}; {resultado}",
    ),
    "pov": (
        "first-person view: the viewer's own hands hold the {producto} in front of {problema}",
        "the viewer's hands use it: {uso}",
        "{resultado}",
    ),
}

PLANTILLA_V2 = (
    "Vertical 9:16 smartphone video, one continuous handheld shot with energetic fast camera motion (quick punch-in zooms, whip moves), realistic UGC style, set in {escenario}. "
    "{encuadre} "
    "0-2s: the product is visible from the very first frame, mid-action: {m1}. "
    "2-5s: {m2}. "
    "5-8s: {m3}. "
    "{soporte}"
    "{audio} "
    "PRODUCT ACCURACY: the product is exactly this: {producto}{ref}; same shape, color, size and quantity in every frame; "
    "realistic physics, normal speed, no effects the real product does not have. "
    "EXCLUDE: {excluir}."
)

# ---------------------------------------------------------------------------
# ESTILO "PRESENTADORA IA" (copiado del formato de @bnrrkkmf821, oct-2026)
# Una misma chava latina generada con IA, a cuadro, habla a cámara y usa el producto.
# 15 s = 2 clips de 8 s, sin textos encima, escenas aspiracionales, producto cerca de cámara.
# Regla de honestidad: describe el producto; NO dice "yo lo uso / me cambió la vida" (sería testimonio falso).
# ---------------------------------------------------------------------------
PERSONA = ("a friendly, pretty 26-year-old Mexican woman with long wavy dark brown hair, warm natural makeup, "
           "bright smile, wearing a plain white t-shirt and light blue jeans")
ESCENAS_PRESENTADORA = {
    "hogar": "a bright cozy bedroom with soft window light, a round mirror and a wooden dresser",
    "cocina": "a bright modern Mexican home kitchen with white counters and daylight",
    "belleza": "a bright bedroom vanity with a round mirror and soft window light",
    "cabello": "a bright bedroom vanity with a round mirror and soft window light",
    "tecnologia": "a bright cozy bedroom with soft window light and a neat desk",
    "fiestas": "a bright living room with a plain white wall and daylight",
    "tienda": "a big Mexican supermarket aisle with shelves fully stocked with this same product",
}
PLANTILLA_PRESENTADORA = (
    "Vertical 9:16 smartphone selfie-style video, realistic UGC influencer style, one continuous shot, set in {escena}. "
    "{persona}. "
    "0-2s: from the very first frame she holds the product close to the camera next to her face, excited: {producto}{ref}. "
    "2-6s: {accion}. "
    "6-8s: she smiles at the camera holding the product up. "
    "She speaks directly to the camera with natural lip-sync, excited and warm, in natural Mexican Spanish, says exactly: "
    '"{linea}" She finishes speaking before the 7-second mark. Soft upbeat background music. '
    "PRODUCT ACCURACY: the product is exactly this: {producto}; same shape, color, size and quantity in every frame; "
    "realistic physics, normal speed, no effects the real product does not have. "
    "EXCLUDE: {excluir}no other products, no logos or brand names, no on-screen text, no subtitles, no watermarks."
)


def construir_presentadora(producto_en: str, escena: str, accion1: str, linea1: str,
                           accion2: str, linea2: str, excluir: str = "", con_imagen: bool = True) -> tuple[str, str]:
    """Devuelve (prompt_clip1, prompt_clip2) con la misma persona y escena para un video de ~15 s."""
    base = dict(escena=ESCENAS_PRESENTADORA.get(escena, escena), persona=PERSONA[0].upper() + PERSONA[1:],
                producto=producto_en, ref=", as in the reference image" if con_imagen else "",
                excluir=(excluir.rstrip(".; ") + "; ") if excluir else "")
    return (PLANTILLA_PRESENTADORA.format(accion=accion1, linea=linea1, **base),
            PLANTILLA_PRESENTADORA.format(accion=accion2, linea=linea2, **base))


# Compatibilidad: los formatos siguen siendo las llaves de PLANTILLAS_VIDEO
PLANTILLAS_VIDEO = {k: PLANTILLA_V2 for k in MOMENTOS}
BASE_RESTRICCIONES = ""

# Checklist de calidad: se revisa en 3 cuadros (0.5 s, 4 s, 7.5 s) antes de aprobar un clip.
QA_CHECKLIST = [
    ("Producto en el cuadro 0", True),
    ("El producto se ve igual que en la ficha (forma, color, tamaño, cantidad)", True),
    ("No aparecen objetos que no vienen en el paquete", True),
    ("La física es real (nada flota, nada se transforma)", True),
    ("No se ve ninguna cara", True),
    ("No hay texto, letras, logos ni marcas de agua generados", True),
    ("La voz dice la frase exacta y suena natural", False),
    ("El resultado se ve creíble, no exagerado", False),
]
# True = si falla, se rechaza el clip. False = se puede corregir en edición.


_UNI = "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciséis diecisiete dieciocho diecinueve veinte veintiuno veintidós veintitrés veinticuatro veinticinco veintiséis veintisiete veintiocho veintinueve".split()
_DEC = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta", 9: "noventa"}
_CEN = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos", 6: "seiscientos",
        7: "setecientos", 8: "ochocientos", 9: "novecientos"}


def numero_a_letras(n: int) -> str:
    """0-9999 en español (para que la voz de la IA no lea "$399" como dólares o dígito por dígito)."""
    if n < 30:
        return _UNI[n]
    if n < 100:
        d, u = divmod(n, 10)
        return _DEC[d] + (f" y {_UNI[u]}" if u else "")
    if n < 1000:
        c, r = divmod(n, 100)
        return "cien" if n == 100 else _CEN[c] + (f" {numero_a_letras(r)}" if r else "")
    m, r = divmod(n, 1000)
    return ("mil" if m == 1 else f"{numero_a_letras(m)} mil") + (f" {numero_a_letras(r)}" if r else "")


def para_voz(t: str) -> str:
    """Pasa precios y números a palabras: "$399" → "trescientos noventa y nueve pesos"."""
    t = re.sub(r"^POV:\s*", "Imagina que ", t)
    t = re.sub(r"\$\s?(\d{1,4})", lambda m: numero_a_letras(int(m.group(1))) + " pesos", t)
    return re.sub(r"\b(\d{1,4})\b", lambda m: numero_a_letras(int(m.group(1))), t)


def linea_voz(gancho: str, beneficio: str, max_palabras: int = 17) -> str:
    """Frase para que Veo la diga dentro de ~7 s (~2.4 palabras/s): gancho + 1 beneficio + carrito naranja.
    Números en letras; si no cabe, se quita el beneficio."""
    def oracion(t: str) -> str:
        t = para_voz(t.strip())
        t = t if t[-1:] in ".?!" else t + "."
        return t[:1].upper() + t[1:] if not t.startswith("¿") else "¿" + t[1:2].upper() + t[2:]
    cierre = "Búscalo en el carrito naranja."
    partes = [oracion(gancho), oracion(beneficio), cierre]
    if len(" ".join(partes).split()) > max_palabras:
        partes.pop(1)
    return " ".join(partes)


# Ganchos (texto en pantalla, primeros 2 s). {p}=producto corto, {precio}=precio
# Sin testimonios inventados ("a mí me funcionó"): solo afirmaciones que el video demuestra.
GANCHOS = {
    "negativo": ["No compres {p} sin ver esto", "Deja de batallar con {problema}", "Error que todos cometen con {problema}"],
    "pregunta": ["¿Sigues batallando con {problema}?", "¿Sabías que existe esto?", "¿Vale la pena por ${precio}?"],
    "pov": ["POV: por fin resolviste {problema}", "POV: encontraste {p} en TikTok Shop", "POV: ya no batallas con {problema}"],
    "precio": ["Esto cuesta menos de ${precio_red}", "${precio} para olvidarte de {problema}", "Lo más útil por menos de ${precio_red}"],
    "curiosidad": ["Mira lo que hace en 5 segundos", "Así funciona {p}", "Esto debería estar en todas las casas"],
}

FORMATO_A_GANCHOS = {
    "problema_solucion": ["negativo", "pregunta", "curiosidad"],
    "antes_despues": ["curiosidad", "precio", "negativo"],
    "unboxing": ["precio", "curiosidad", "pov"],
    "pov": ["pov", "pregunta"],
}

GUIONES_VOZ = {
    "problema_solucion": "{gancho}. Si te pasa esto, {problema}, mira: con {p} {beneficio1}, y además {beneficio2}. Te lo dejo en el carrito naranja.",
    "antes_despues": "{gancho}. Mira el antes... y el después. {p}: {beneficio1}. Cuesta ${precio}. Lo encuentras en el carrito naranja.",
    "unboxing": "{gancho}. Mira {p}. Lo que trae: {beneficio1} y {beneficio2}. Cuesta ${precio} y está en el carrito naranja.",
    "pov": "{gancho}. Así de fácil: {beneficio1}. Y {beneficio2}. Lo encuentras en el carrito naranja.",
}

HASHTAGS_BASE = ["#tiktokshopmx", "#tiktokmademebuyit"]
HASHTAGS_CATEGORIA = {
    "hogar": ["#hogar", "#casa", "#organizacion"],
    "cocina": ["#cocina", "#cocinafacil", "#gadgetsdecocina"],
    "limpieza": ["#limpieza", "#tipsdelimpieza", "#hogar"],
    "belleza": ["#belleza", "#maquillaje"],
    "cabello": ["#cabello", "#peinados", "#plancha"],
    "mascotas": ["#mascotas", "#perros", "#gatos"],
    "auto": ["#autos", "#cuidadodelauto"],
    "tecnologia": ["#tecnologia", "#gadgets"],
    "fiestas": ["#fiesta", "#decoracion", "#cumpleaños"],
}


RELLENO = {"para", "de", "con", "en", "y", "el", "la", "los", "las", "del", "por", "ejemplo", "a"}


def _corto(p, n: int = 3) -> str:
    """Nombre como lo dirías en voz alta: usa nombre_corto si existe; si no, las primeras palabras útiles."""
    keys = p.keys() if hasattr(p, "keys") else []
    if "nombre_corto" in keys and p["nombre_corto"]:
        return p["nombre_corto"].strip()
    palabras = [w for w in re.sub(r"[^\w\sáéíóúñÁÉÍÓÚÑ-]", "", p["nombre"]).split() if w.lower() != "ejemplo"]
    corto = palabras[:n]
    while corto and corto[-1].lower() in RELLENO:
        corto.pop()
    return ("este " if corto else "") + " ".join(corto).lower()


def _hashtag(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    t = [w for w in re.sub(r"[^a-z0-9 ]", "", t).split() if w not in RELLENO and w not in {"este", "esta", "estos", "estas"}][:2]
    return "#" + "".join(t) if t else ""


def _beneficios(p) -> list[str]:
    b = [x.strip() for x in (p["beneficios"] or "").split("|") if x.strip()]
    return (b + ["te ahorra tiempo", "es fácil de usar"])[:3]


def construir(p, formato: str, escenario: str | None = None, rng: random.Random | None = None,
              uso_en: str = "", problema_en: str = "", resultado_en: str = "", producto_en: str = "",
              tipo_gancho: str | None = None, voz_ia: bool = False) -> dict:
    """Arma prompt de video + gancho + guion de voz + caption + hashtags para un producto.

    Los campos *_en (en inglés) describen la acción para la IA de video. Si no se dan,
    se usan genéricos; lo ideal es guardarlos en el producto (campo notas) o escribirlos al planear.
    """
    rng = rng or random.Random()
    cat = (p["categoria"] or "hogar").lower()
    escenario = escenario or ESCENARIOS.get(cat, ESCENARIOS["hogar"])
    corto = _corto(p)
    precio = int(p["precio"] or 0)
    problema = (p["problema"] or "ese problema de todos los días").strip().rstrip(".")
    b = _beneficios(p)

    keys = p.keys() if hasattr(p, "keys") else []
    def campo(k, dado, defecto):
        return dado or (p[k] if k in keys and p[k] else defecto)

    producto = campo("producto_en", producto_en, p["nombre"])
    ctx = {
        "producto": producto,
        "problema": campo("problema_en", problema_en, "the everyday problem this product solves, shown realistically"),
        "uso": campo("uso_en", uso_en, "using it the normal, intended way at normal speed"),
        "resultado": campo("resultado_en", resultado_en, "a realistic, believable improvement"),
    }
    m1, m2, m3 = (m.format(**ctx) for m in MOMENTOS[formato])
    soporte = campo("soporte_en", "", "")
    excluir = campo("excluir_en", "", "")
    tiene_imagen = bool((p["imagenes"] if "imagenes" in keys else "") or "")
    _prompt_args = dict(
        escenario=escenario, encuadre=ENCUADRE, m1=m1, m2=m2, m3=m3,
        soporte=(soporte[:1].upper() + soporte[1:].rstrip(".") + ". ") if soporte else "",
        producto=producto, ref=" as in the reference image" if tiene_imagen else "",
        excluir=(excluir.rstrip(".") + "; " if excluir else "") + EXCLUIR_BASE,
    )

    tipo_gancho = tipo_gancho or rng.choice(FORMATO_A_GANCHOS[formato])
    gancho = rng.choice(GANCHOS[tipo_gancho]).format(
        p=corto, problema=problema.lower(), precio=precio, precio_red=(precio // 50 + 1) * 50 if precio else 300)

    guion = GUIONES_VOZ[formato].format(gancho=gancho, problema=problema.lower(), p=corto,
                                        beneficio1=b[0], beneficio2=b[1], precio=precio)

    tags = HASHTAGS_BASE + HASHTAGS_CATEGORIA.get(cat, ["#hogar"])[:2] + [_hashtag(corto)]
    tags = [t for t in tags if t]
    caption = (f"{gancho} 👇\n{b[0].capitalize()} y {b[1]}. Precio y promo en el carrito naranja 🛒\n"
               f"Video generado con IA a partir de la foto real del producto.")
    def pulir(t: str) -> str:
        t = re.sub(r"\bde el\b", "del", t)
        t = re.sub(r"\ba el\b", "al", t)
        t = re.sub(r"(?<!\.\.)\.\s+([a-záéíóúñ])", lambda m: ". " + m.group(1).upper(), t)
        return t[:1].upper() + t[1:]

    gancho, guion = pulir(gancho), pulir(guion)
    linea = linea_voz(gancho, b[0])
    audio = AUDIO_CON_VOZ.format(linea=linea) if voz_ia else AUDIO_SIN_VOZ
    prompt = PLANTILLA_V2.format(audio=audio, **_prompt_args)
    caption = pulir(caption.replace(caption.split(" 👇")[0], gancho, 1))
    return {
        "formato": formato,
        "tipo_gancho": tipo_gancho,
        "gancho": gancho,
        "prompt": prompt,
        "guion_voz": guion,
        "linea_voz_ia": linea,
        "caption": caption,
        "hashtags": " ".join(dict.fromkeys(tags)),
    }
