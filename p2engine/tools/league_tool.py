from pydantic import BaseModel, ConfigDict

from agents.decorators import function_tool
from infra.logging.logging_config import logger


class LeagueInput(BaseModel):
    league: str
    model_config = ConfigDict(extra="forbid")


@function_tool(
    name="get_league_leader",
    description="Get the current leader of a football league.",
    input_schema=LeagueInput,
)
def get_league_leader(league: str) -> dict:
    logger.info(f"get_league_leader invoked with league={league}")
    league_data = {
        "Ligue 1": ["Paris Saint-Germain", "Lyon", "Marseille"],
        "Premier League": ["Manchester City", "Liverpool", "Chelsea"],
        "La Liga": ["Real Madrid", "Barcelona", "Atletico Madrid"],
    }
    if league in league_data:
        leader = league_data[league][0]
        return {
            "status": "success",
            "data": {"league": league, "leader": leader},
        }
    else:
        return {"status": "error", "message": f"League '{league}' not found."}
