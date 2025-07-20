"""
Main FastAPI application for ProyectoSoc ticket management system
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Depends
from backend.routes.twilio_voice import router as twilio_router
from backend.routes.audio import router as audio_router

import uvicorn

from backend.config.settings import get_settings
from backend.database.connection import init_db
from backend.routes import tickets
from backend.logging_config import setup_logging
from backend.auth.basic_auth import verify_basic_auth
from backend.routes import embeddings
from backend.routes.search import router as search_router
from backend.routes.attachments import router as attachments_router

#Frontend
from fastapi.staticfiles import StaticFiles

load_dotenv()
setup_logging()

# Initialize settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="ProyectoSoc API",
    description="API para gestión de tickets con integración de IA y voz",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tickets.router)  # <--- sin prefix ni tags aquí
app.include_router(embeddings.router)
app.include_router(search_router)
app.include_router(twilio_router)
app.include_router(attachments_router)

#app.include_router(audio_router)

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    pass

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ProyectoSoc API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/protected")
def protected_route(username: str = Depends(verify_basic_auth)):
    return {"message": f"¡Hola {username}! Tienes acceso protegido."}

'''
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
'''
os.makedirs("./audio_tmp", exist_ok=True)
app.mount("/audio", StaticFiles(directory="./audio_tmp"), name="audio")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 