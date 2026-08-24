
import json

from pydantic import BaseModel, Field, field_validator
from langchain_core.tools import tool


ENERGY_STATE = {
    "inverter_1": {
        "pv_power_w": 4200,
        "load_power_w": 2800,
        "battery_soc": 72,
        "battery_power_w": -900,
        "grid_power_w": -500,
        "power_limit_w": 6000,
    }
}


class EnergyStatusInput(BaseModel):
    inverter_id: str = Field(
        ...,
        description="Ідентифікатор інвертора, наприклад inverter_1"
    )

    @field_validator("inverter_id")
    @classmethod
    def validate_inverter_id(cls, value: str) -> str:
        value = value.strip().lower()

        if not value:
            raise ValueError("inverter_id не може бути порожнім")

        if not value.startswith("inverter_"):
            raise ValueError(
                "inverter_id повинен починатися з 'inverter_'"
            )

        return value


@tool(args_schema=EnergyStatusInput)
def get_energy_status(inverter_id: str) -> str:
    """Отримує поточний стан енергосистеми."""

    try:
        if inverter_id not in ENERGY_STATE:
            return json.dumps(
                {
                    "status": "error",
                    "error": f"Інвертор {inverter_id} не знайдено"
                },
                ensure_ascii=False
            )

        return json.dumps(
            {
                "status": "success",
                "data": ENERGY_STATE[inverter_id]
            },
            ensure_ascii=False
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "error": str(exc)
            },
            ensure_ascii=False
        )


class SafeLoadInput(BaseModel):
    pv_power_w: int = Field(..., ge=0, le=50000)
    current_load_w: int = Field(..., ge=0, le=50000)
    reserve_w: int = Field(default=500, ge=0, le=10000)

    @field_validator("reserve_w")
    @classmethod
    def validate_reserve(cls, value: int) -> int:
        if value % 50 != 0:
            raise ValueError(
                "reserve_w повинен бути кратним 50 Вт"
            )
        return value


@tool(args_schema=SafeLoadInput)
def calculate_safe_load(
    pv_power_w: int,
    current_load_w: int,
    reserve_w: int = 500
) -> str:
    """Розраховує безпечну додаткову потужність."""

    try:
        available_power = (
            pv_power_w
            - current_load_w
            - reserve_w
        )

        available_power = max(0, available_power)

        return json.dumps(
            {
                "status": "success",
                "data": {
                    "available_power_w": available_power,
                    "reserve_w": reserve_w,
                    "can_add_load": available_power > 0
                }
            },
            ensure_ascii=False
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "error": str(exc)
            },
            ensure_ascii=False
        )


class BatteryCheckInput(BaseModel):
    soc: int = Field(..., ge=0, le=100)
    minimum_soc: int = Field(default=20, ge=5, le=90)

    @field_validator("minimum_soc")
    @classmethod
    def validate_minimum_soc(cls, value: int) -> int:
        if value < 10:
            raise ValueError(
                "minimum_soc не рекомендується нижче 10%"
            )
        return value


@tool(args_schema=BatteryCheckInput)
def check_battery_safety(
    soc: int,
    minimum_soc: int = 20
) -> str:
    """Перевіряє безпечність розряду батареї."""

    try:
        safe = soc > minimum_soc

        return json.dumps(
            {
                "status": "success",
                "data": {
                    "soc": soc,
                    "minimum_soc": minimum_soc,
                    "discharge_allowed": safe
                }
            },
            ensure_ascii=False
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "error": str(exc)
            },
            ensure_ascii=False
        )


class SetPowerLimitInput(BaseModel):
    inverter_id: str
    limit_w: int = Field(..., ge=500, le=12000)
    reason: str = Field(..., min_length=5, max_length=200)

    @field_validator("inverter_id")
    @classmethod
    def validate_inverter_id(cls, value: str) -> str:
        value = value.strip().lower()

        if not value.startswith("inverter_"):
            raise ValueError(
                "inverter_id повинен починатися з 'inverter_'"
            )

        return value

    @field_validator("limit_w")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        if value % 100 != 0:
            raise ValueError(
                "Ліміт повинен бути кратним 100 Вт"
            )
        return value


@tool(args_schema=SetPowerLimitInput)
def set_inverter_power_limit(
    inverter_id: str,
    limit_w: int,
    reason: str
) -> str:
    """Ризиковий tool зміни ліміту інвертора."""

    try:
        if inverter_id not in ENERGY_STATE:
            return json.dumps(
                {
                    "status": "error",
                    "error": f"Інвертор {inverter_id} не знайдено"
                },
                ensure_ascii=False
            )

        old_limit = ENERGY_STATE[inverter_id]["power_limit_w"]
        ENERGY_STATE[inverter_id]["power_limit_w"] = limit_w

        return json.dumps(
            {
                "status": "success",
                "data": {
                    "old_limit_w": old_limit,
                    "new_limit_w": limit_w,
                    "reason": reason
                }
            },
            ensure_ascii=False
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "error": str(exc)
            },
            ensure_ascii=False
        )
