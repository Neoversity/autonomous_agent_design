
import json
import pytest
from pydantic import ValidationError

from energy_agent_core import (
    EnergyStatusInput,
    SafeLoadInput,
    BatteryCheckInput,
    SetPowerLimitInput,
    get_energy_status,
    calculate_safe_load,
    check_battery_safety,
)


def test_valid_inverter_id():
    model = EnergyStatusInput(
        inverter_id="inverter_1"
    )
    assert model.inverter_id == "inverter_1"


def test_invalid_inverter_id():
    with pytest.raises(ValidationError):
        EnergyStatusInput(
            inverter_id="device_1"
        )


def test_valid_reserve():
    model = SafeLoadInput(
        pv_power_w=4200,
        current_load_w=2800,
        reserve_w=500
    )
    assert model.reserve_w == 500


def test_invalid_reserve():
    with pytest.raises(ValidationError):
        SafeLoadInput(
            pv_power_w=4200,
            current_load_w=2800,
            reserve_w=525
        )


def test_invalid_soc():
    with pytest.raises(ValidationError):
        BatteryCheckInput(
            soc=120,
            minimum_soc=20
        )


def test_invalid_minimum_soc():
    with pytest.raises(ValidationError):
        BatteryCheckInput(
            soc=70,
            minimum_soc=5
        )


def test_invalid_power_limit():
    with pytest.raises(ValidationError):
        SetPowerLimitInput(
            inverter_id="inverter_1",
            limit_w=5555,
            reason="Некоректний тестовий ліміт"
        )


def test_get_energy_status_tool():
    result = json.loads(
        get_energy_status.invoke(
            {"inverter_id": "inverter_1"}
        )
    )

    assert result["status"] == "success"
    assert "pv_power_w" in result["data"]


def test_calculate_safe_load_tool():
    result = json.loads(
        calculate_safe_load.invoke(
            {
                "pv_power_w": 4200,
                "current_load_w": 2800,
                "reserve_w": 500
            }
        )
    )

    assert result["status"] == "success"
    assert (
        result["data"]["available_power_w"]
        == 900
    )


def test_check_battery_safety_tool():
    result = json.loads(
        check_battery_safety.invoke(
            {
                "soc": 72,
                "minimum_soc": 20
            }
        )
    )

    assert result["status"] == "success"
    assert (
        result["data"]["discharge_allowed"]
        is True
    )

def test_basic_react_components():
    """
    Базова перевірка компонентів ReAct-агента без виклику Gemini.
    Перевіряємо, що основні tools доступні та мають коректні імена.
    """

    from energy_agent_core import (
        get_energy_status,
        calculate_safe_load,
        check_battery_safety,
        set_inverter_power_limit,
    )

    tools = [
        get_energy_status,
        calculate_safe_load,
        check_battery_safety,
        set_inverter_power_limit,
    ]

    names = [tool.name for tool in tools]

    assert "get_energy_status" in names
    assert "calculate_safe_load" in names
    assert "check_battery_safety" in names
    assert "set_inverter_power_limit" in names
