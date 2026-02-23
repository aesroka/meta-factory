"""Cost and time prediction before running (Phase 15)."""

from typing import Dict

# Historical averages (will improve with real data)
COST_ESTIMATES = {
    "standard": {
        "greenfield": {"min_usd": 0.8, "max_usd": 3.0, "min_duration_s": 120, "max_duration_s": 300},
        "brownfield": {"min_usd": 1.0, "max_usd": 4.0, "min_duration_s": 150, "max_duration_s": 360},
        "greyfield": {"min_usd": 1.5, "max_usd": 5.0, "min_duration_s": 200, "max_duration_s": 480},
    },
    "premium": {
        "greenfield": {"min_usd": 15.0, "max_usd": 45.0, "min_duration_s": 600, "max_duration_s": 1800},
        "brownfield": {"min_usd": 20.0, "max_usd": 50.0, "min_duration_s": 800, "max_duration_s": 2400},
        "greyfield": {"min_usd": 25.0, "max_usd": 60.0, "min_duration_s": 1000, "max_duration_s": 3000},
    },
}


def estimate_cost_and_time(
    input_size: int,
    mode: str,
    quality: str,
) -> Dict[str, float]:
    """Estimate cost and duration based on input size and settings.

    Args:
        input_size: Character count of input
        mode: greenfield, brownfield, greyfield
        quality: standard, premium

    Returns:
        Dict with min_cost_usd, max_cost_usd, min_duration_min, max_duration_min
    """
    base = COST_ESTIMATES.get(quality, {}).get(mode, COST_ESTIMATES["standard"]["greenfield"])
    size_multiplier = 1.0
    if input_size > 100_000:
        size_multiplier = 2.0
    elif input_size > 50_000:
        size_multiplier = 1.5
    return {
        "min_cost_usd": base["min_usd"] * size_multiplier,
        "max_cost_usd": base["max_usd"] * size_multiplier,
        "min_duration_min": base["min_duration_s"] / 60,
        "max_duration_min": base["max_duration_s"] / 60,
    }
