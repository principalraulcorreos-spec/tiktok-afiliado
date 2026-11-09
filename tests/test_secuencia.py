"""Pruebas del modo REAL + REACCIÓN con material sintético (no necesita internet ni archivos del usuario).

    pip install pytest && python -m pytest -q tests
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from afiliado import qa, secuencia

VERDE_VEO = "0x3F9D3E"   # el verde real que entrega Veo (no es #00FF00)


def _ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


@pytest.fixture(scope="module")
def material(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("prod")
    for sub in ("videos", "fotos", "presentadora"):
        (d / sub).mkdir()
    _ff("-f", "lavfi", "-i", "testsrc2=s=576x1024:r=30:d=8", d / "videos/v1.mp4")
    _ff("-f", "lavfi", "-i", "color=c=orange:s=1000x1000,drawbox=x=600:y=50:w=350:h=200:color=black:t=fill",
        "-frames:v", "1", d / "fotos/01.jpg")
    # presentadora sintética: "persona" blanca/rosa sobre el verde de Veo, con voz (tono) que se corta a los 5 s
    _ff("-f", "lavfi", "-i", f"color=c={VERDE_VEO}:s=720x1280:r=30:d=7",
        "-f", "lavfi", "-i", "sine=f=300:d=5", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=2",
        "-filter_complex", "[1:a][2:a]concat=n=2:v=0:a=1[a];[0:v]drawbox=x=220:y=150:w=280:h=650:color=white:t=fill[v]",
        "-map", "[v]", "-map", "[a]", "-shortest", d / "presentadora/r1.mp4")
    return d


def test_color_fondo_detecta_verde_de_veo(material):
    c = secuencia.color_fondo(str(material / "presentadora/r1.mp4"))
    r, g, b = (int(c[i:i + 2], 16) for i in (2, 4, 6))
    assert abs(r - 0x3F) < 12 and abs(g - 0x9D) < 12 and abs(b - 0x3E) < 12


def test_captions_de_frase_reparte_todo_el_tramo():
    caps = secuencia.captions_de_frase("uno dos tres cuatro cinco seis siete", 1.0, 4.0)
    assert caps[0]["ini"] == 1.0 and abs(caps[-1]["fin"] - 4.0) < 1e-6
    assert " ".join(c["t"] for c in caps) == "uno dos tres cuatro cinco seis siete"


def test_armar_video_completo(material):
    tl = secuencia.plan_auto(material, duracion=6)
    tl["presentadora"] = {"clips": [{"src": "presentadora/r1.mp4", "dur": 5.0, "en": "auto",
                                     "texto": "mira lo que encontré para tu casa"}]}
    tl["textos"] = [{"t": "GANCHO", "ini": 0, "fin": 1.5, "estilo": "gancho"},
                    {"t": "CARRITO NARANJA ↓", "ini": -1.5, "fin": 0, "estilo": "cta"}]
    out = secuencia.armar(tl, material)
    m = qa.medir(out)
    assert 5.0 <= m["duracion_s"] <= 6.0          # dura lo que habla la presentadora (+ cola)
    assert m["verde_residual_pct"] < 0.5          # el chroma quitó el verde
    assert m["negro_s"] == 0
    assert -15.5 <= m["lufs"] <= -12.5


def test_qa_detecta_verde_sin_recortar(material, tmp_path):
    """Control negativo: si la presentadora se pega SIN chroma, el QA debe marcarlo."""
    out = tmp_path / "malo.mp4"
    _ff("-f", "lavfi", "-i", "color=c=gray:s=1080x1920:r=30:d=3", "-i", material / "presentadora/r1.mp4",
        "-filter_complex", "[1:v]scale=453:-2[p];[0:v][p]overlay=591:200:shortest=1", "-an", out)
    assert qa.medir(out)["verde_residual_pct"] > 20


def _salto_max_borde(video: Path) -> float:
    """Mayor salto de luminancia entre filas consecutivas alrededor del borde inferior del busto (y≈600–780)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "3", "-i", str(video), "-frames:v", "1",
                          "-vf", "crop=150:180:750:600,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    filas = [sum(raw[r * 150:(r + 1) * 150]) / 150 for r in range(180)]
    return max(abs(filas[i + 1] - filas[i]) for i in range(179))


@pytest.fixture(scope="module")
def material_liso(tmp_path_factory, material) -> Path:
    """Fondo negro liso y sin fotos, para aislar el borde inferior del busto."""
    d = tmp_path_factory.mktemp("liso")
    for sub in ("videos", "presentadora"):
        (d / sub).mkdir()
    _ff("-f", "lavfi", "-i", "color=c=black:s=576x1024:r=30:d=8", d / "videos/v1.mp4")
    (d / "presentadora/r1.mp4").write_bytes((material / "presentadora/r1.mp4").read_bytes())
    return d


@pytest.mark.parametrize("fade,maximo", [(0.12, 30), (0, None)])
def test_busto_se_desvanece_abajo(material_liso, fade, maximo):
    """Con `desvanecer` el busto no termina en un corte recto; con 0 se conserva el corte (control)."""
    material = material_liso
    tl = secuencia.plan_auto(material, duracion=6)
    tl["presentadora"] = {"desvanecer": fade,
                          "clips": [{"src": "presentadora/r1.mp4", "dur": 5.0, "en": "auto", "texto": "mira"}]}
    salto = _salto_max_borde(secuencia.armar(tl, material))
    if maximo is None:
        assert salto > 60      # corte recto: el control negativo sí debe verse
    else:
        assert salto < maximo


def test_loudnorm_2_pasadas_sin_voz(material, tmp_path):
    """Sin voz (solo efectos y mucho silencio) el loudnorm de 1 pasada quedaba en −16.6 LUFS; debe quedar en −14 ±0.5
    sin pasar el true peak del QA."""
    tl = secuencia.plan_auto(material, duracion=8)
    tl["salida"] = str(tmp_path / "sin_voz.mp4")
    m = qa.medir(secuencia.armar(tl, material))
    assert -14.5 <= m["lufs"] <= -13.5
    assert m["true_peak_db"] <= -1.0


def test_loudnorm_2p_silencio_regresa_1_pasada(tmp_path):
    wav = tmp_path / "silencio.wav"
    _ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "2", wav)
    assert secuencia._loudnorm_2p(wav).startswith("loudnorm=")
