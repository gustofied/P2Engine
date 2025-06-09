REQUIRED_TOOLS = {
    "weather_expert": {"get_weather"},
    # Add more personas here
}


def get_required_tools(persona: str) -> set:
    return REQUIRED_TOOLS.get(persona, set())
