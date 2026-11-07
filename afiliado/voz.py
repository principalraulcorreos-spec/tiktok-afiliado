"""Voz del narrador (modo REAL + REACCIÓN) con Gemini TTS.

Dos caminos:
1. Web (sin API key): Google AI Studio → "Generate speech" (aistudio.google.com/generate-speech).
   Pegar `instruccion_estudio(texto)` como prompt, voz `VOZ`, descargar el .wav a <Producto>/voz.wav.
2. API (con GEMINI_API_KEY en .env, desde la PC):  python -m afiliado.voz "<texto>" Downloads/<Producto>/voz.wav

Reglas del guion: 40-55 palabras (~16-22 s), solo lo que dice la ficha, sin precio ("está en oferta"),
sin testimonios ("yo lo uso"), cerrar con "en el carrito naranja".
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

VOZ = "Leda"   # voz femenina juvenil y clara; alternativas: Aoede (cálida), Puck (masculina animada)
ESTILO = ("Lee esto en español mexicano natural, como una tiktoker emocionada que comparte un hallazgo: "
          "ritmo rápido y con energía, sonrisa en la voz, pausas cortas entre frases")


def instruccion_estudio(texto: str) -> str:
    return f"{ESTILO}:\n{texto}"


def generar(texto: str, salida: str | Path, voz: str = VOZ) -> Path:
    from google import genai
    from google.genai import types
    from .config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        raise SystemExit("Falta GEMINI_API_KEY en .env (o usa AI Studio en el navegador)")
    cli = genai.Client(api_key=GEMINI_API_KEY)
    r = cli.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=instruccion_estudio(texto),
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voz))),
        ),
    )
    pcm = r.candidates[0].content.parts[0].inline_data.data
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(salida), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    return salida


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    print(generar(sys.argv[1], sys.argv[2]))
