import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.voice_routes import router as voice_router
from app.api_routes import router as api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ulavu")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing ULAVU (உழவு) application...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(
            f"Database initialization warning (will retry on first request if DB is starting up): {e}"
        )
    
    # Pre-cache voicebot prompts in background for fast TTS response
    import asyncio
    from app.audio_service import precache_prompts
    asyncio.create_task(precache_prompts())

    yield
    logger.info("Shutting down ULAVU application.")

app = FastAPI(
    title="ULAVU (உழவு) — Voice & SMS Agricultural Lead-Routing API",
    description="Live telephony and lead matching platform connecting Tamil Nadu farmers and retailers.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
origins = settings.cors_origins_list
if not origins or "*" not in origins:
    # Ensure frontend dev ports are supported
    origins.extend(["http://localhost:3000", "http://127.0.0.1:3000", "*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(voice_router)
app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "service": "ULAVU (உழவு)",
        "status": "online",
        "voice_webhook_exotel": "/voice/exotel",
        "voice_websocket": "/voice/exotel/ws",
        "api_docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
