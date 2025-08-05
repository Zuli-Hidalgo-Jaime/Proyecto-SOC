"""
Ruta para servir archivos de audio generados (por ejemplo, por TTS).
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/audio")

@router.get("/{filename}")
async def get_audio(filename: str):
    """
    Devuelve el archivo de audio solicitado, si existe en el directorio TMP_DIR.
    """
    path = os.path.join(os.getenv("TMP_DIR", "/tmp"), filename)
    if not os.path.isfile(path):
        raise HTTPException(404, "Audio no encontrado")
    return FileResponse(path, media_type="audio/mpeg")
