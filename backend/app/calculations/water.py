"""Water estimation (Section 9).

Water consumption cannot be directly measured on this hardware. This is an
illustrative estimation model (energy x Water Usage Effectiveness), not a
measurement, and can be disabled entirely.
"""

from app.schemas import WaterResult

WATER_ENABLED_NOTE = (
    "Illustrative estimate only, based on energy consumed and a configurable "
    "Water Usage Effectiveness (WUE) assumption. Water consumption is not "
    "directly measurable on this hardware - treat this as methodology, not data."
)
WATER_DISABLED_NOTE = "Water estimation disabled by configuration."


def compute_water(
    energy_kwh: float, wue_l_per_kwh: float | None, enabled: bool
) -> WaterResult:
    if not enabled or wue_l_per_kwh is None:
        return WaterResult(
            enabled=False,
            wue_l_per_kwh=wue_l_per_kwh,
            estimated_liters=None,
            note=WATER_DISABLED_NOTE,
        )

    return WaterResult(
        enabled=True,
        wue_l_per_kwh=wue_l_per_kwh,
        estimated_liters=energy_kwh * wue_l_per_kwh,
        note=WATER_ENABLED_NOTE,
    )
