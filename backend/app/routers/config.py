from fastapi import APIRouter

from app.config import settings
from app.schemas import ConfigResponse

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    return ConfigResponse(
        telemetry_interval_seconds=settings.telemetry_interval_seconds,
        electricity_rate=settings.electricity_rate,
        currency=settings.currency,
        carbon_intensity_kg_per_kwh=settings.carbon_intensity_kg_per_kwh,
        water_wue_l_per_kwh=settings.water_wue_l_per_kwh,
        water_estimation_enabled=settings.water_estimation_enabled,
    )
