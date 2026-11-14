"""Component Database and IEC 60063 E-Series Value Snapping.

Provides exact logarithmic decade snapping for standard resistor and capacitor
values across E12 (10%), E24 (5%), and E96 (1%) tolerance tiers.
"""

from __future__ import annotations
import math
from enum import Enum
from typing import Dict, List, Tuple


class ESeries(str, Enum):
    E12 = "E12"
    E24 = "E24"
    E96 = "E96"


# Standard base mantissas defined by IEC 60063
E12_BASE: List[float] = [
    1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2
]

E24_BASE: List[float] = [
    1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
    3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1
]

E96_BASE: List[float] = [
    1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24,
    1.27, 1.30, 1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58,
    1.62, 1.65, 1.69, 1.74, 1.78, 1.82, 1.87, 1.91, 1.96, 2.00,
    2.05, 2.10, 2.15, 2.21, 2.26, 2.32, 2.37, 2.43, 2.49, 2.55,
    2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09, 3.16, 3.24,
    3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
    4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23,
    5.36, 5.49, 5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65,
    6.81, 6.98, 7.15, 7.32, 7.50, 7.68, 7.87, 8.06, 8.25, 8.45,
    8.66, 8.87, 9.09, 9.31, 9.53, 9.76
]

_SERIES_MAP = {
    ESeries.E12: E12_BASE,
    ESeries.E24: E24_BASE,
    ESeries.E96: E96_BASE,
}


def snap_component_value(
    value: float,
    series: ESeries | str = ESeries.E24,
    component_type: str = "resistor"
) -> Dict[str, float | str]:
    """Snap an ideal component value to the nearest IEC standard E-series value.

    Args:
        value: The calculated ideal component value (in Ohms, Farads, or Henries).
        series: IEC series tier ('E12', 'E24', or 'E96').
        component_type: 'resistor', 'capacitor', or 'inductor'.

    Returns:
        Dictionary containing:
            - ideal_value: Original floating point input
            - standard_value: Snapped standard commercial value
            - error_percent: Relative deviation percentage ((snapped - ideal)/ideal * 100)
            - series: The series used
            - formatted: Human-readable engineering string (e.g., '4.7 kΩ', '100 nF')
    """
    if value <= 0:
        raise ValueError("Component values must be strictly positive (> 0).")

    if isinstance(series, str):
        series = ESeries(series.upper())

    base_table = _SERIES_MAP[series]

    # Decompose into decade exponent and mantissa: value = mantissa * 10^decade
    decade = math.floor(math.log10(value))
    mantissa = value / (10 ** decade)

    # Find the nearest mantissa using minimum absolute distance
    best_base = min(base_table, key=lambda b: abs(b - mantissa))

    # Check decade wrap-around (e.g., when snapping 9.8 in E24 -> 10.0)
    snapped_value = best_base * (10 ** decade)

    # Re-verify if next decade start is closer
    next_decade_val = base_table[0] * (10 ** (decade + 1))
    if abs(next_decade_val - value) < abs(snapped_value - value):
        snapped_value = next_decade_val

    error_pct = ((snapped_value - value) / value) * 100.0

    return {
        "ideal_value": value,
        "standard_value": float(f"{snapped_value:.6g}"),
        "error_percent": round(error_pct, 2),
        "series": series.value,
        "formatted": format_engineering_unit(snapped_value, component_type),
    }


def format_engineering_unit(val: float, comp_type: str) -> str:
    """Format floating point electrical value into SI unit representation."""
    comp_type = comp_type.lower()

    if "res" in comp_type:
        unit = "Ω"
        if val >= 1e6:
            return f"{val / 1e6:.3g} M{unit}"
        elif val >= 1e3:
            return f"{val / 1e3:.3g} k{unit}"
        elif val < 1.0:
            return f"{val * 1e3:.3g} m{unit}"
        return f"{val:.3g} {unit}"

    elif "cap" in comp_type:
        unit = "F"
        if val >= 1e-3:
            return f"{val * 1e3:.3g} m{unit}"
        elif val >= 1e-6:
            return f"{val * 1e6:.3g} µ{unit}"
        elif val >= 1e-9:
            return f"{val * 1e9:.3g} n{unit}"
        elif val >= 1e-12:
            return f"{val * 1e12:.3g} p{unit}"
        return f"{val:.3g} {unit}"

    elif "ind" in comp_type:
        unit = "H"
        if val >= 1.0:
            return f"{val:.3g} {unit}"
        elif val >= 1e-3:
            return f"{val * 1e3:.3g} m{unit}"
        elif val >= 1e-6:
            return f"{val * 1e6:.3g} µ{unit}"
        return f"{val:.3g} {unit}"

    return f"{val:.3g}"

