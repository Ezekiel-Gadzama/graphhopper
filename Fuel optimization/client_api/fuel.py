def estimate_fuel_saved(distance1: float, distance2: float, efficiency_l_per_km: float = 0.07) -> float:
    """Estimate fuel saved between two distances (meters)."""
    km1, km2 = distance1 / 1000.0, distance2 / 1000.0
    fuel1 = km1 * efficiency_l_per_km
    fuel2 = km2 * efficiency_l_per_km
    return max(0.0, fuel1 - fuel2)