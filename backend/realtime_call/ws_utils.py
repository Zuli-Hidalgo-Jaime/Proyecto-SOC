# backend/realtime_call/ws_utils.py
import os
import asyncio
import json
import base64
import audioop
import logging
import websockets
import contextlib
import inspect
from textwrap import dedent
from asyncio import Queue
from typing import List, Dict, Optional, Callable
from fastapi import WebSocket

from .elevenlabs_client import get_signed_url

LOG = logging.getLogger("realtime_call.ws_utils")

# Audio (8 kHz μ-law <-> PCM16 8k)
FRAME_WIDTH = 2
CHANNELS = 1
ULAW_SR = 8000
CHUNK_MS = 20.0
SAMPLES_PER_CHUNK = int(ULAW_SR * (CHUNK_MS / 1000.0))  # 160
ULAW_CHUNK_SIZE = SAMPLES_PER_CHUNK
ULAW_SILENCE = bytes([0xFF]) * ULAW_CHUNK_SIZE
END_UTTERANCE_MS = 1600  # ~1.6 s


def align_frames(b: bytes, width: int = FRAME_WIDTH, ch: int = CHANNELS) -> bytes:
    """
    Alinea un buffer para que su longitud sea múltiplo de (width * channels).
    """
    fs = width * ch
    rem = len(b) % fs
    return b if rem == 0 else b + b"\x00" * (fs - rem)


def ulaw_8k_to_pcm16_8k(ulaw_b64: str) -> bytes:
    """
    Convierte μ-law 8 kHz (base64) a PCM16 8 kHz.
    Origen: Twilio Media Streams.
    """
    ulaw_bytes = base64.b64decode(ulaw_b64)
    return audioop.ulaw2lin(align_frames(ulaw_bytes, 1, 1), 2)


async def _silence_timer(wait_ms: int, cb):
    """
    Temporizador asíncrono para notificar fin de habla tras inactividad.
    """
    try:
        await asyncio.sleep(wait_ms / 1000.0)
        await cb()
    except asyncio.CancelledError:
        pass


def el_audio_to_ulaw8k(audio_b64: str) -> bytes:
    """
    Decodifica audio μ-law 8 kHz desde base64 (salida de ElevenLabs).
    """
    return base64.b64decode(audio_b64)


async def relay_twilio(ws_twilio: WebSocket, tools: Optional[List[Dict]] = None):
    """
    Puente Twilio ↔ ElevenLabs con ejecución de tools locales.

    - Acepta WebSocket de Twilio (μ-law 8k).
    - Envía audio de usuario a ElevenLabs y recibe audio de respuesta.
    - Publica tools (si el plan lo soporta) y atiende 'tool_request'.
    """
    await ws_twilio.accept()
    LOG.info("✅ Twilio WS aceptado")

    signed_url = await get_signed_url()
    LOG.info("🔗 WS ElevenLabs signed URL obtenido")

    async with websockets.connect(signed_url) as ws_11:
        stream_sid: Optional[str] = None
        caller_phone: Optional[str] = None
        out_q: Queue = Queue(maxsize=200)

        user_speaking = False
        silence_task: Optional[asyncio.Task] = None

        tool_map: Dict[str, Callable] = {}
        tool_schema_map: Dict[str, Dict] = {}
        if tools:
            for t in tools:
                name = t["name"]
                tool_map[name] = t["func"]
                tool_schema_map[name] = t.get("schema", {}) or {}

            if "handle_ticket_query" in tool_map and "get_ticket_info" not in tool_map:
                tool_map["get_ticket_info"] = tool_map["handle_ticket_query"]
                tool_schema_map["get_ticket_info"] = tool_schema_map["handle_ticket_query"]

            try:
                await ws_11.send(
                    json.dumps(
                        {
                            "type": "session.update",
                            "tools": [
                                {
                                    "name": n,
                                    "description": "",
                                    "input_schema": tool_schema_map.get(n)
                                    or {"type": "object", "properties": {}},
                                }
                                for n in tool_map.keys()
                            ],
                        }
                    )
                )
                LOG.info("🧰 Tools publicados a ElevenLabs: %s", ", ".join(tool_map.keys()))
            except Exception as e:
                LOG.warning("No se pudieron publicar tools (continuamos con prompt/portal): %s", e)

        INIT_PROMPT = dedent(
            """
            # Política de herramientas (ES)
            SIEMPRE usa el tool para obtener información de tickets cuando:
            - El usuario pida “estado/estatus/información de mi ticket”.
            - El usuario describa un problema (ej.: “mi compu no enciende”, “no puedo entrar a SharePoint”,
              “tengo un error con Outlook”, “se cayó la VPN”).

            Procedimiento:
            1) Haz UNA pregunta breve si hace falta: “¿Cuál es tu número de ticket o descríbeme el problema en una frase?”.
            2) Llama al tool con el texto literal del usuario (no parafrasees ni traduzcas).
            3) Di en voz alta EXACTAMENTE el texto que regrese el tool.
            4) Termina con: “¿Te ayudo con algo más?”.
            """
        ).strip()

        init_payload = {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {"language": "es", "prompt": {"prompt": INIT_PROMPT}}
            },
        }
        await ws_11.send(json.dumps(init_payload))
        LOG.info("🟢 Conversación iniciada con ElevenLabs")

        async def streamer():
            """
            Envía audio μ-law a Twilio manteniendo ritmo CHUNK_MS.
            """
            nonlocal stream_sid
            while True:
                try:
                    ulaw_bytes = await asyncio.wait_for(out_q.get(), timeout=8.0)
                except asyncio.TimeoutError:
                    ulaw_bytes = ULAW_SILENCE

                if ulaw_bytes is None:
                    break

                if stream_sid is None:
                    await asyncio.sleep(0.01)
                    continue

                for i in range(0, len(ulaw_bytes), ULAW_CHUNK_SIZE):
                    chunk = ulaw_bytes[i : i + ULAW_CHUNK_SIZE]
                    if not chunk:
                        continue
                    await ws_twilio.send_text(
                        json.dumps(
                            {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": base64.b64encode(chunk).decode()},
                            }
                        )
                    )
                    await asyncio.sleep(CHUNK_MS / 1000.0)

        streamer_task = asyncio.create_task(streamer())

        async def start_user_audio():
            """
            Marca inicio de habla hacia ElevenLabs.
            """
            nonlocal user_speaking
            if not user_speaking:
                with contextlib.suppress(Exception):
                    await ws_11.send(json.dumps({"type": "start_of_user_audio"}))
                user_speaking = True
                LOG.debug("▶️ start_of_user_audio")

        async def end_user_audio():
            """
            Marca fin de habla hacia ElevenLabs.
            """
            nonlocal user_speaking
            if user_speaking:
                with contextlib.suppress(Exception):
                    await ws_11.send(json.dumps({"type": "end_of_user_audio"}))
                user_speaking = False
                LOG.debug("⏹ end_of_user_audio")

        def reset_silence_timer():
            """
            Reinicia el temporizador de silencio para detectar fin de utterance.
            """
            nonlocal silence_task
            if silence_task and not silence_task.done():
                silence_task.cancel()
            silence_task = asyncio.create_task(_silence_timer(END_UTTERANCE_MS, end_user_audio))

        async def twilio_to_11():
            """
            Recibe frames de Twilio (start/media/stop), envía audio a ElevenLabs
            y captura número del llamante.
            """
            nonlocal stream_sid, caller_phone, silence_task
            try:
                while True:
                    frame = json.loads(await ws_twilio.receive_text())
                    ev = frame.get("event")

                    if ev == "start":
                        start_info = frame.get("start") or {}
                        stream_sid = start_info.get("streamSid")
                        caller_phone = start_info.get("from") or caller_phone
                        LOG.info("Twilio SID: %s | Caller: %s", stream_sid, caller_phone)

                    elif ev == "media":
                        await start_user_audio()
                        pcm16_8k = ulaw_8k_to_pcm16_8k(frame["media"]["payload"])
                        await ws_11.send(
                            json.dumps(
                                {
                                    "type": "user_audio_chunk",
                                    "user_audio_chunk": base64.b64encode(pcm16_8k).decode(),
                                }
                            )
                        )
                        reset_silence_timer()

                    elif ev == "stop":
                        LOG.info("🛑 Twilio stop; cerrando utterance/sesión")
                        await end_user_audio()
                        with contextlib.suppress(Exception):
                            await ws_11.send(json.dumps({"type": "end_of_user_audio"}))
                        break

            except websockets.ConnectionClosed:
                LOG.info("🔌 Twilio WS cerrado")
            except Exception as e:
                LOG.exception("Error en twilio_to_11: %s", e)

            if silence_task and not silence_task.done():
                silence_task.cancel()

        async def eleven_to_twilio():
            """
            Procesa mensajes de ElevenLabs (audio, transcripciones y tools).
            """
            try:
                while True:
                    raw = await ws_11.recv()
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue

                    mtype = msg.get("type")

                    if mtype == "audio":
                        audio_b64 = (msg.get("audio_event", {}) or {}).get("audio_base_64")
                        if audio_b64:
                            try:
                                ulaw8k = el_audio_to_ulaw8k(audio_b64)
                                if len(ulaw8k) % ULAW_CHUNK_SIZE != 0:
                                    pad = ULAW_CHUNK_SIZE - (len(ulaw8k) % ULAW_CHUNK_SIZE)
                                    ulaw8k += bytes([0xFF]) * pad
                                await out_q.put(ulaw8k)
                            except Exception as e:
                                LOG.debug("put audio error: %s", e)

                    elif mtype == "user_transcript":
                        ev = msg.get("user_transcription_event", {}) or {}
                        if ev.get("is_final"):
                            LOG.info("[11labs] transcript: %s", ev.get("user_transcript"))

                    elif mtype == "tool_request":
                        call_id = msg.get("call_id") or msg.get("tool_call_id")
                        tool_name = msg.get("tool_name") or (msg.get("tool", {}) or {}).get("name")
                        params = msg.get("parameters") or msg.get("args") or {}

                        if tool_name == "get_ticket_info" and "handle_ticket_query" in tool_map:
                            tool_name = "handle_ticket_query"
                            if isinstance(params, dict) and "query_text" in params and "text" not in params:
                                params["text"] = params["query_text"]

                        fn = tool_map.get(tool_name)
                        if not fn:
                            out_text = f"No se encontró el tool '{tool_name}'."
                        else:
                            schema_props = (tool_schema_map.get(tool_name) or {}).get("properties", {})
                            if caller_phone and "phone" in schema_props:
                                params.setdefault("phone", caller_phone)

                            try:
                                if inspect.iscoroutinefunction(fn):
                                    result = await fn(**params)
                                else:
                                    result = fn(**params)
                                out_text = result if isinstance(result, str) else json.dumps(
                                    result, ensure_ascii=False
                                )
                            except Exception as e:
                                LOG.exception("Error en tool '%s': %s", tool_name, e)
                                out_text = f"Ocurrió un error al ejecutar {tool_name}."

                        resp = {
                            "type": "tool_response",
                            "call_id": call_id,
                            "tool_name": tool_name,
                            "response": out_text,
                        }
                        await ws_11.send(json.dumps(resp))
                        LOG.info("📤 Tool '%s' ejecutado. call_id=%s", tool_name, call_id)

                    elif mtype in ("tool_response", "tool_error"):
                        LOG.info("[11labs] tool evt: %s", msg)

                    elif mtype in ("agent_response", "status_update", "conversation_initiation_metadata"):
                        LOG.debug("[11labs] evt=%s", mtype)

                    elif mtype == "error":
                        LOG.error("[11labs] error: %s", msg)

            except websockets.ConnectionClosed:
                LOG.info("🔌 WS ElevenLabs cerrado")
            except Exception as e:
                LOG.exception("Error en eleven_to_twilio: %s", e)

        try:
            await asyncio.gather(twilio_to_11(), eleven_to_twilio())
        finally:
            await out_q.put(None)
            with contextlib.suppress(Exception):
                await streamer_task

