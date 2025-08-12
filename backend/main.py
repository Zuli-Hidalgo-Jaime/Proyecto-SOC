"""
Main FastAPI application for ProyectoSoc ticket management system.
"""
import os
from dotenv import load_dotenv

# --- Cargar .env ANTES de importar módulos que leen variables (muy importante) ---
load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from backend.config.settings import get_settings
from backend.database.connection import init_db
from backend.routes import tickets, embeddings
from backend.routes.search import router as search_router
from backend.routes.twilio_voice import router as twilio_router
from backend.routes.attachments import router as attachments_router
from backend.auth import jwt_auth
from backend.logging_config import setup_logging
from backend.auth.basic_auth import verify_basic_auth
from backend.realtime_call import inbound_routes
from backend.realtime_call import agent_tools


# ==== Setup logging (ya con .env cargado) ====
setup_logging()

# ==== Initialize settings ====
settings = get_settings()

# ==== Create FastAPI app ====
app = FastAPI(
    title="ProyectoSoc API",
    description="API para gestión de tickets con integración de IA y voz",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ==== Static Frontend ====  (dejamos solo el frontend)
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# ==== CORS ====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajusta para producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== Routers ====
app.include_router(tickets.router)
app.include_router(embeddings.router)
app.include_router(search_router)
app.include_router(twilio_router)
app.include_router(attachments_router)
app.include_router(jwt_auth.router)
app.include_router(inbound_routes.router)
app.include_router(agent_tools.router)

# ==== Lifecycle Events ====
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    pass

# ==== Root, Health, Protected Endpoints ====
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ProyectoSoc API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/protected")
def protected_route(username: str = Depends(verify_basic_auth)):
    """Protected route for basic auth demo."""
    return {"message": f"¡Hola {username}! Tienes acceso protegido."}

# ==== Run app ====
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",  # ← usa el import path correcto si el archivo está en backend/main.py
        host="0.0.0.0",
        port=8000,
        reload=True
    )

