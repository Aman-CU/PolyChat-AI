from fastapi import APIRouter
from typing import Dict, Any

from app.providers.router import router as provider_router

router = APIRouter()


@router.get("/models")
async def get_models() -> Dict[str, Any]:
    """Get available models grouped by provider from the registered providers."""
    models_by_provider = await provider_router.list_models()
    providers: Dict[str, Any] = {}
    for pid, models in models_by_provider.items():
        providers[pid] = {
            "name": pid.capitalize(),
            "models": [m.dict() for m in models],
        }
    return {"providers": providers}
