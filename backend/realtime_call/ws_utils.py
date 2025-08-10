import os
import asyncio
import json
import base64
import audioop
import logging
import unicodedata
import websockets
import re
from enum import Enum
from asyncio import Queue
from fastapi import WebSocket

from backend.services.ticket_service import handle_ticket_query
from .elevenlabs_client import get_signed_url

LOG = logging.getLogger("realtime_call.ws_utils")

# -------- audio (8 kHz) --------
FRAME_WIDTH = 2
CHANNELS = 1
ULAW_SR = 8000
CHUNK_MS = 20.0
SAMPLES_PER_CHUNK = int(ULAW_SR * (CHUNK_MS / 1000.0))  # 160
ULAW_CHUNK_SIZE = SAMPLES_PER_CHUNK

def align_frames(b: bytes, width=FRAME_WIDTH, ch=CHANNELS) -> bytes:
    fs = width * ch
    rem = len(b) % fs
    return b if rem == 0 else b + b"\x00" * (fs - rem)

def ulaw_8k_to_pcm16_16k(ulaw_b64: str) -> bytes:
    ulaw_bytes = base64.b64decode(ulaw_b64)
    pcm16_8k = audioop.ulaw2lin(align_frames(ulaw_bytes, 1, 1), 2)
    pcm16_16k, _ = audioop.ratecv(align_frames(pcm16_8k, 2, 1), 2, 1, 8000, 16000, None)
    return pcm16_16k

# -------- modos --------
class Mode(str, Enum):
    KNN = "knn"
    AGENT = "agent"

def detect_intent(text: str) -> Mode:
    # normaliza (minúsc, sin acentos, sin rarezas)
    t = text.lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9ñ\s#-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    patterns = [
        r"\b(quiero|quisiera|necesito|me gustaria)\s+(saber|conocer|ver|consultar|revisar)\s+(la\s+)?(informacion|info|el\s+estado|estatus|detalles?)\s+(de|del|sobre)\s+(mi|mis)\s+(tickets?|folios?|incidencias?|casos?)\b",
        r"\b(informacion|info|estado|estatus|detalles?)\s+(de|del|sobre)\s+(mi|mis)\s+(tickets?|folios?|incidencias?|casos?)\b",
        r"\b(mi|mis)\s+(ticket|folio|incidencia|caso)s?\s*(#|num|numero|nro)?\s*\d{3,}\b",
    ]
    if any(re.search(p, t) for p in patterns):
        return Mode.KNN

    if "modo tickets" in t or "consulta de tickets" in t:
        return Mode.KNN
    if "modo agente" in t or "hablar con el asistente" in t or "copilot" in t:
        return Mode.AGENT

    return Mode.AGENT

ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

# -------- relay principal --------
async def relay_twilio(ws_twilio: WebSocket):
    current_mode: Mode = Mode.AGENT
    expecting_tts: bool = False

    await ws_twilio.accept()
    signed_url = await get_signed_url()
    LOG.info(f"WS ElevenLabs: {signed_url}")

    async with websockets.connect(signed_url) as ws_11:
        stream_sid = None
        out_q: Queue = Queue(maxsize=200)

        # init agent (lee [TTS] literal)
        init_payload = {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "prompt": {
                        "prompt": (
                            "Eres un agente de soporte. "
                            "Si un mensaje del cliente empieza con [TTS], "
                            "DEBES leer exactamente ese texto y no agregar nada."
                        )
                    },
                    "language": "es"
                },
                "tts": ({"voice_id": ELEVEN_VOICE_ID} if ELEVEN_VOICE_ID else {})
            }
        }
        await ws_11.send(json.dumps(init_payload))

        # streamer: Eleven -> Twilio (μ-law 8k) con pacing
        async def streamer():
            nonlocal stream_sid, expecting_tts, current_mode
            while True:
                try:
                    ulaw_bytes = await asyncio.wait_for(out_q.get(), timeout=8.0)
                    had_real = True
                except asyncio.TimeoutError:
                    ulaw_bytes = bytes([0xFF]) * ULAW_CHUNK_SIZE
                    had_real = False

                if ulaw_bytes is None:
                    break

                while stream_sid is None:
                    await asyncio.sleep(0.005)

                for i in range(0, len(ulaw_bytes), ULAW_CHUNK_SIZE):
                    chunk = ulaw_bytes[i:i + ULAW_CHUNK_SIZE]
                    if not chunk:
                        continue
                    await ws_twilio.send_text(json.dumps({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": base64.b64encode(chunk).decode()}
                    }))
                    await asyncio.sleep(CHUNK_MS / 1000.0)

                # cerrar ciclo KNN -> volver a AGENT tras oír el TTS
                if current_mode == Mode.KNN and expecting_tts and had_real:
                    expecting_tts = False
                    current_mode = Mode.AGENT
                    LOG.info("↩️ back to AGENT")

        streamer_task = asyncio.create_task(streamer())

        # Twilio -> Eleven (μ-law 8k -> PCM16 16k)
        async def twilio_to_11():
            nonlocal stream_sid, current_mode, expecting_tts
            while True:
                frame = json.loads(await ws_twilio.receive_text())
                ev = frame.get("event")

                if ev == "start":
                    stream_sid = frame["start"]["streamSid"]
                    LOG.info(f"Twilio SID: {stream_sid}")

                elif ev == "media":
                    pcm16_16k = ulaw_8k_to_pcm16_16k(frame["media"]["payload"])
                    await ws_11.send(json.dumps({
                        "type": "user_audio_chunk",
                        "user_audio_chunk": base64.b64encode(pcm16_16k).decode()
                    }))

                elif ev == "stop":
                    try:
                        await ws_11.close()
                    finally:
                        break

        # Eleven -> Twilio (transcripts finales + audio)
        async def eleven_to_twilio():
            nonlocal current_mode, expecting_tts, stream_sid, out_q
            while True:
                raw = await ws_11.recv()
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue

                mtype = msg.get("type")

                if mtype == "user_transcript":
                    ev = msg.get("user_transcription_event", {}) or {}
                    text = (ev.get("user_transcript") or "").strip()

                    # SOLO transcripts finales
                    if ev.get("is_final") is False:
                        continue
                    if not text or len(re.sub(r"[^a-záéíóúñ0-9]", "", text.lower())) < 4:
                        continue

                    LOG.info(f"[rx] {text}")
                    new_mode = detect_intent(text)
                    LOG.info(f"[router] intent={new_mode} (current={current_mode})")

                    if new_mode != current_mode:
                        current_mode = new_mode
                        if stream_sid:
                            await ws_twilio.send_text(json.dumps({
                                "event": "clear",
                                "streamSid": stream_sid
                            }))
                        # limpiamos cola de salida y bajamos bandera
                        try:
                            while not out_q.empty():
                                out_q.get_nowait()
                                out_q.task_done()
                        except Exception:
                            pass
                        expecting_tts = False

                    if current_mode == Mode.KNN:
                        reply = "Ocurrió un error buscando tu ticket. Intenta otra vez."
                        try:
                            tmp = await handle_ticket_query(text, phone="")
                            if isinstance(tmp, str) and tmp.strip():
                                reply = tmp.strip()
                        except Exception as e:
                            LOG.exception(f"[KNN] handle_ticket_query error: {e}")

                        prev = reply.replace("\n", " ")[:120]
                        LOG.info(f"[KNN->TTS] {prev}{'…' if len(reply) > 120 else ''}")

                        await ws_11.send(json.dumps({
                            "type": "user_message",
                            "text": f"[TTS] {reply}"
                        }))
                        expecting_tts = True

                elif mtype == "audio":
                    audio_b64 = (msg.get("audio_event", {}) or {}).get("audio_base_64")
                    if not audio_b64:
                        continue
                    # en KNN, solo dejamos pasar audio si esperamos el TTS
                    if current_mode == Mode.KNN and not expecting_tts:
                        continue
                    try:
                        await out_q.put(base64.b64decode(audio_b64))
                    except Exception:
                        pass

        try:
            await asyncio.gather(twilio_to_11(), eleven_to_twilio())
        finally:
            await out_q.put(None)
            try:
                await streamer_task
            except Exception:
                pass
