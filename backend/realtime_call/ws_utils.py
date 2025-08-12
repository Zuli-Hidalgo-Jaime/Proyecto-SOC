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

# -------- audio (8 kHz μ-law <-> PCM16 16k) --------
FRAME_WIDTH = 2
CHANNELS = 1
ULAW_SR = 8000
CHUNK_MS = 20.0
SAMPLES_PER_CHUNK = int(ULAW_SR * (CHUNK_MS / 1000.0))  # 160
ULAW_CHUNK_SIZE = SAMPLES_PER_CHUNK  # μ-law: 1 byte por muestra @8kHz
ULAW_SILENCE = bytes([0xFF]) * ULAW_CHUNK_SIZE
END_UTTERANCE_MS = 1600  # ~1.6 s de inactividad

def align_frames(b: bytes, width=FRAME_WIDTH, ch=CHANNELS) -> bytes:
    fs = width * ch
    rem = len(b) % fs
    return b if rem == 0 else b + b"\x00" * (fs - rem)

def ulaw_8k_to_pcm16_16k(ulaw_b64: str) -> bytes:
    """Twilio (μ-law 8k) -> PCM16 16k para ElevenLabs."""
    ulaw_bytes = base64.b64decode(ulaw_b64)
    pcm16_8k = audioop.ulaw2lin(align_frames(ulaw_bytes, 1, 1), 2)
    pcm16_16k, _ = audioop.ratecv(align_frames(pcm16_8k, 2, 1), 2, 1, 8000, 16000, None)
    return pcm16_16k

async def _silence_timer(wait_ms: int, cb):
    try:
        await asyncio.sleep(wait_ms / 1000.0)
        await cb()
    except asyncio.CancelledError:
        pass

def el_audio_to_ulaw8k(audio_b64: str) -> bytes:
    """
    Convierte audio PCM16 16k → μ-law 8k. Si ya fuera μ-law, regresa los bytes crudos.
    """
    raw = base64.b64decode(audio_b64)
    try:
        if len(raw) % 2 == 0:
            pcm16_16k = align_frames(raw, 2, 1)
            pcm16_8k, _ = audioop.ratecv(pcm16_16k, 2, 1, 16000, 8000, None)
            ulaw = audioop.lin2ulaw(align_frames(pcm16_8k, 2, 1), 2)
            return ulaw
    except Exception:
        pass
    return raw


# -------- relay principal: SOLO streaming RT con start/end de habla + tools --------
async def relay_twilio(ws_twilio: WebSocket, tools: Optional[List[Dict]] = None):
    """
    Puente Twilio ↔ ElevenLabs.
    - Mantiene tu flujo de audio y VAD por tiempo.
    - Acepta `tools` desde inbound_routes y ejecuta tools locales al recibir `tool_request`.
    - Alias: 'get_ticket_info' → mapea a handle_ticket_query(query_text -> text).
    """
    await ws_twilio.accept()
    LOG.info("✅ Twilio WS aceptado")

    # 1) signed URL NUEVO por llamada
    signed_url = await get_signed_url()
    LOG.info("🔗 WS ElevenLabs signed URL obtenido")

    async with websockets.connect(signed_url) as ws_11:
        stream_sid: Optional[str] = None
        caller_phone: Optional[str] = None
        out_q: Queue = Queue(maxsize=200)

        # Estado para utterances
        user_speaking = False
        silence_task: Optional[asyncio.Task] = None

        # ==== TOOLS MAP (por nombre) ====
        tool_map: Dict[str, Callable] = {}
        tool_schema_map: Dict[str, Dict] = {}
        if tools:
            for t in tools:
                name = t["name"]
                tool_map[name] = t["func"]
                tool_schema_map[name] = t.get("schema", {}) or {}
            # alias opcional si tu agente pide 'get_ticket_info'
            if "handle_ticket_query" in tool_map and "get_ticket_info" not in tool_map:
                tool_map["get_ticket_info"] = tool_map["handle_ticket_query"]
                tool_schema_map["get_ticket_info"] = tool_schema_map["handle_ticket_query"]

            # (opcional) enviar definición de tools si tu plan lo soporta
            try:
                await ws_11.send(json.dumps({
                    "type": "session.update",
                    "tools": [
                        {
                            "name": n,
                            "description": "",
                            "input_schema": tool_schema_map.get(n) or {
                                "type": "object",
                                "properties": {}
                            }
                        } for n in tool_map.keys()
                    ]
                }))
                LOG.info("🧰 Tools publicados a ElevenLabs: %s", ", ".join(tool_map.keys()))
            except Exception as e:
                LOG.warning("No se pudieron publicar tools (continuamos con prompt/portal): %s", e)

        # 2) Inicializa conversación (tu prompt original)
        INIT_PROMPT = dedent("""
        # Política de herramientas (ES)
        SIEMPRE usa el tool para obtener información de tickets cuando:
        - El usuario pida “estado/estatus/información de mi ticket”.
        - El usuario describa un problema (ej.: “mi compu no enciende”, “no puedo entrar a SharePoint”, “tengo un error con Outlook”, “se cayó la VPN”).

        Procedimiento:
        1) Haz UNA pregunta breve si hace falta: “¿Cuál es tu número de ticket o descríbeme el problema en una frase?”.
        2) Llama al tool con el texto literal del usuario (no parafrasees ni traduzcas).
        3) Di en voz alta EXACTAMENTE el texto que regrese el tool.
        4) Termina con: “¿Te ayudo con algo más?”.
        """).strip()

        init_payload = {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {"language": "es", "prompt": {"prompt": INIT_PROMPT}}
            }
        }
        await ws_11.send(json.dumps(init_payload))
        LOG.info("🟢 Conversación iniciada con ElevenLabs")

        # 3) ElevenLabs -> Twilio (μ-law 8k con pacing constante)
        async def streamer():
            nonlocal stream_sid
            while True:
                try:
                    ulaw_bytes = await asyncio.wait_for(out_q.get(), timeout=8.0)
                except asyncio.TimeoutError:
                    ulaw_bytes = ULAW_SILENCE

                if ulaw_bytes is None:
                    break

                # Nota: Twilio Media Streams son unidireccionales (Twilio -> servidor).
                # Mandar 'media' de vuelta suele ser ignorado por Twilio.
                # Dejamos este pacing por si usas algún proxy/puente que lo acepte.
                if stream_sid is None:
                    await asyncio.sleep(0.01)
                    continue

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

        streamer_task = asyncio.create_task(streamer())

        # Helpers para marcar inicios/finales de habla
        async def start_user_audio():
            nonlocal user_speaking
            if not user_speaking:
                with contextlib.suppress(Exception):
                    await ws_11.send(json.dumps({"type": "start_of_user_audio"}))
                user_speaking = True
                LOG.debug("▶️ start_of_user_audio")

        async def end_user_audio():
            nonlocal user_speaking
            if user_speaking:
                with contextlib.suppress(Exception):
                    await ws_11.send(json.dumps({"type": "end_of_user_audio"}))
                user_speaking = False
                LOG.debug("⏹ end_of_user_audio")

        def reset_silence_timer():
            nonlocal silence_task
            if silence_task and not silence_task.done():
                silence_task.cancel()
            silence_task = asyncio.create_task(_silence_timer(END_UTTERANCE_MS, end_user_audio))

        # 4) Twilio -> ElevenLabs (μ-law 8k -> PCM16 16k) + capturar caller
        async def twilio_to_11():
            nonlocal stream_sid, caller_phone, silence_task
            try:
                while True:
                    frame = json.loads(await ws_twilio.receive_text())
                    ev = frame.get("event")

                    if ev == "start":
                        start_info = frame.get("start") or {}
                        stream_sid = start_info.get("streamSid")
                        caller_phone = start_info.get("from") or caller_phone
                        LOG.info(f"Twilio SID: {stream_sid} | Caller: {caller_phone}")

                    elif ev == "media":
                        await start_user_audio()
                        pcm16_16k = ulaw_8k_to_pcm16_16k(frame["media"]["payload"])
                        await ws_11.send(json.dumps({
                            "type": "user_audio_chunk",
                            "user_audio_chunk": base64.b64encode(pcm16_16k).decode()
                        }))
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
                LOG.exception(f"Error en twilio_to_11: {e}")

            if silence_task and not silence_task.done():
                silence_task.cancel()

        # 5) ElevenLabs -> (audio + eventos) -> Tools/Twilio
        async def eleven_to_twilio():
            try:
                while True:
                    raw = await ws_11.recv()
                    # algunos frames pueden ser binarios; intenta JSON
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
                                LOG.debug(f"put audio error: {e}")

                    elif mtype == "user_transcript":
                        ev = msg.get("user_transcription_event", {}) or {}
                        if ev.get("is_final"):
                            LOG.info(f"[11labs] transcript: {ev.get('user_transcript')}")

                    # === NUEVO: ejecución de tools locales ===
                    elif mtype == "tool_request":
                        # Estructuras posibles:
                        # {type:"tool_request", tool_name, call_id/tool_call_id, parameters:{...}}
                        call_id = msg.get("call_id") or msg.get("tool_call_id")
                        tool_name = msg.get("tool_name") or (msg.get("tool", {}) or {}).get("name")
                        params = msg.get("parameters") or msg.get("args") or {}

                        # alias 'get_ticket_info' -> 'handle_ticket_query'
                        if tool_name == "get_ticket_info" and "handle_ticket_query" in tool_map:
                            tool_name = "handle_ticket_query"
                            # mapear query_text -> text si viene así
                            if isinstance(params, dict) and "query_text" in params and "text" not in params:
                                params["text"] = params["query_text"]

                        fn = tool_map.get(tool_name)
                        if not fn:
                            out_text = f"No se encontró el tool '{tool_name}'."
                        else:
                            # inyecta phone si el schema lo contempla
                            schema_props = (tool_schema_map.get(tool_name) or {}).get("properties", {})
                            if caller_phone and "phone" in schema_props:
                                params.setdefault("phone", caller_phone)

                            try:
                                if inspect.iscoroutinefunction(fn):
                                    result = await fn(**params)
                                else:
                                    result = fn(**params)
                                out_text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
                            except Exception as e:
                                LOG.exception("Error en tool '%s': %s", tool_name, e)
                                out_text = f"Ocurrió un error al ejecutar {tool_name}."

                        # Responder según el protocolo que estás viendo en logs
                        resp = {
                            "type": "tool_response",
                            "call_id": call_id,
                            "tool_name": tool_name,
                            "response": out_text,
                        }
                        await ws_11.send(json.dumps(resp))
                        LOG.info("📤 Tool '%s' ejecutado. call_id=%s", tool_name, call_id)

                    elif mtype in ("tool_response", "tool_error"):
                        LOG.info(f"[11labs] tool evt: {msg}")

                    elif mtype in ("agent_response", "status_update", "conversation_initiation_metadata"):
                        LOG.debug(f"[11labs] evt={mtype}")

                    elif mtype == "error":
                        LOG.error(f"[11labs] error: {msg}")

            except websockets.ConnectionClosed:
                LOG.info("🔌 WS ElevenLabs cerrado")
            except Exception as e:
                LOG.exception(f"Error en eleven_to_twilio: {e}")

        try:
            await asyncio.gather(twilio_to_11(), eleven_to_twilio())
        finally:
            await out_q.put(None)
            with contextlib.suppress(Exception):
                await streamer_task
