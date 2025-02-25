import json
import pytest
from unittest.mock import patch, Mock, mock_open
from systems.goal_scenario import GoalOrientedSystem
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from custom_logging.central_logger import central_logger
from agents.simple_agent.agent import SimpleAgent    

def test_dynamic_component_loading():
    # Test loading default components
    component_manager = ComponentManager()
    assert "tool" in component_manager.component_types
    assert "connection" in component_manager.component_types
    assert "memory" in component_manager.component_types

    # Test loading from a mock config file
    mock_config = {
        "components": {
            "mock_tool": "entities.component_manager.ToolComponent"  # Use an existing class for simplicity
        }
    }
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_config))):
        component_manager = ComponentManager("fake_config.json")
        assert "mock_tool" in component_manager.component_types
        assert component_manager.component_types["mock_tool"] == component_manager.component_types["tool"]

def test_tool_usage():
    entity_manager = EntityManager()
    component_manager = ComponentManager()
    agent = SimpleAgent(
        entity_manager=entity_manager,
        component_manager=component_manager,
        name="TestAgent",
        tools=["calculator"]
    )
    
    # Test calculator tool usage
    response = agent.interact("Calculate 2 + 2")
    assert response == "4"

    # Test non-tool input with mocked LLM response
    with patch.object(agent.llm, "query", return_value="Hello"):
        response = agent.interact("Say hello")
        assert response == "Hello"

def test_goal_oriented_system():
    entity_manager = EntityManager()
    component_manager = ComponentManager()
    initial_agents = [
        SimpleAgent(entity_manager=entity_manager, component_manager=component_manager, name="TestBot")
    ]
    system = GoalOrientedSystem(initial_agents, entity_manager, component_manager)
    
    with patch.object(system.critic.llm, "query", return_value="Mock Answer"):
        result = system.run_scenario("Test problem", "Test question")
        assert result == "Mock Answer"
        assert len(central_logger.scenario_logs) > 0
        assert central_logger.scenario_logs[-1]["reward"] is not None
        assert "tool" not in central_logger.scenario_logs[-1]["entities"][initial_agents[0].id]["components"]  # No tools in this test

if __name__ == "__main__":
    pytest.main(["-v"])