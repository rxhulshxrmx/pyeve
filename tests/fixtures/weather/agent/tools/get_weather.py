async def execute(city: str) -> dict:
    """Return mock weather data for a city."""
    return {"city": city, "condition": "Sunny", "temp_f": 72}
