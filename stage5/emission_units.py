"""
emission_units.py

Stage 5
Emission unit conversion utilities.

Supported conversions:

    kg/year -> kg/s
    kg/day  -> kg/s
    kg/hour -> kg/s
    g/s     -> kg/s
    kg/s    -> kg/s
"""

SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0
SECONDS_PER_DAY = 24.0 * 3600.0
SECONDS_PER_HOUR = 3600.0


def to_kg_per_second(value, unit):

    unit = unit.lower().strip()

    if unit in [
        "kg/s",
        "kg/sec",
        "kg/second"
    ]:
        return value

    if unit in [
        "g/s",
        "g/sec",
        "g/second"
    ]:
        return value / 1000.0

    if unit in [
        "kg/day",
        "kg/d"
    ]:
        return value / SECONDS_PER_DAY

    if unit in [
        "kg/hour",
        "kg/hr",
        "kg/h"
    ]:
        return value / SECONDS_PER_HOUR

    if unit in [
        "kg/year",
        "kg/yr",
        "kg/y"
    ]:
        return value / SECONDS_PER_YEAR

    raise ValueError(
        f"Unsupported emission unit: {unit}"
    )


def from_kg_per_second(value, unit):

    unit = unit.lower().strip()

    if unit == "kg/s":
        return value

    if unit == "g/s":
        return value * 1000.0

    if unit in ["kg/day", "kg/d"]:
        return value * SECONDS_PER_DAY

    if unit in ["kg/hour", "kg/hr", "kg/h"]:
        return value * SECONDS_PER_HOUR

    if unit in ["kg/year", "kg/yr", "kg/y"]:
        return value * SECONDS_PER_YEAR

    raise ValueError(
        f"Unsupported output unit: {unit}"
    )
