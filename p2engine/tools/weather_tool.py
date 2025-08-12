from pydantic import BaseModel, ConfigDict

from agents.decorators import function_tool
from infra.logging.logging_config import logger


class WeatherInput(BaseModel):
    """Schema for the get_weather tool."""

    location: str
    unit: str = "fahrenheit"
    model_config = ConfigDict(extra="forbid")


@function_tool(
    name="get_weather",
    description="Get the current weather in a given location.",
    input_schema=WeatherInput,
)
def get_weather(location: str, unit: str = "fahrenheit") -> dict:
    """
    Return fake weather data so we can test the end-to-end plumbing without
    hitting a real API.

    Parameters
    ----------
    location : str
        City name (matches the keys in `weather_data` below).
    unit : str, optional
        'fahrenheit' or 'celsius'. Default is 'fahrenheit'.

    Returns
    -------
    dict
        {
          "status": "success",
          "data": {
              "location": "<City>",
              "temperature": <float>,
              "unit": "<unit>"
          }
        }
        or an error payload if the city is unknown.
    """
    logger.info("get_weather invoked with location=%s, unit=%s", location, unit)

    weather_data = {
        "San Francisco": {"temperature": 72, "unit": "fahrenheit"},
        "Tokyo": {"temperature": 10, "unit": "celsius"},
        "Paris": {"temperature": 22, "unit": "celsius"},
    }

    if location not in weather_data:
        return {
            "status": "error",
            "message": f"Weather data for '{location}' not found.",
        }

    data = weather_data[location]
    temp = data["temperature"]
    stored_unit = data["unit"]

    if unit != stored_unit:
        if unit == "fahrenheit" and stored_unit == "celsius":
            temp = (temp * 9 / 5) + 32
        elif unit == "celsius" and stored_unit == "fahrenheit":
            temp = (temp - 32) * 5 / 9

    return {
        "status": "success",
        "data": {
            "location": location,
            "temperature": round(temp, 1),
            "unit": unit,
        },
    }
