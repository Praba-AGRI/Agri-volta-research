from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        from app.mqtt.client import mqtt_manager
        asyncio.create_task(mqtt_manager.start())
    except Exception as e:
        print(f"[MQTT] MQTT manager notice: {e}")
    yield
    try:
        from app.mqtt.client import mqtt_manager
        await mqtt_manager.stop()
    except Exception:
        pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Research-grade Agrivoltaic Field Monitoring API",
    lifespan=lifespan
)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "environment": settings.ENVIRONMENT,
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }

from app.api.live import router as live_router
from app.api.history import router as history_router
from app.api.comparison import router as comparison_router
from app.api.agronomy import router as agronomy_router
from app.api.predictions import router as predictions_router
from app.api.shap import router as shap_router
from app.api.diagnostics import router as diagnostics_router
from app.api.validation import router as validation_router
from app.api.export import router as export_router
from app.api.experiment import router as experiment_router
from app.api.field_archive import router as field_router

app.include_router(live_router, prefix="/api/live", tags=["Live"])
app.include_router(history_router, prefix="/api/history", tags=["History"])
app.include_router(comparison_router, prefix="/api/comparison", tags=["Comparison"])
app.include_router(agronomy_router, prefix="/api/agronomy", tags=["Agronomy"])
app.include_router(predictions_router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(shap_router, prefix="/api/shap", tags=["SHAP"])
app.include_router(diagnostics_router, prefix="/api/diagnostics", tags=["Diagnostics"])
app.include_router(validation_router, prefix="/api/validation", tags=["Validation"])
app.include_router(export_router, prefix="/api/export", tags=["Export"])
app.include_router(experiment_router, prefix="/api/experiment", tags=["Experiment"])
app.include_router(field_router, prefix="/api/field", tags=["Field Archive"])
