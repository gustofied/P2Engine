# projectdeux/src/systems/collaborative_scenario.py

import time
import logging
from typing import List
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from custom_logging.central_logger import central_logger
from single_agents.base_agent import BaseAgent
from single_agents.simple_agent import SimpleAgent
from single_agents.chaos_agent import ChaosAgent
from single_agents.critic_agent import CriticAgent

class CollaborativeScenarioSystem:
    """
    A new scenario system that runs a collaborative multi-agent scenario.
    Agents provide initial responses to a question, the critic analyzes them,
    and then a final synthesis is generated.
    """
    def __init__(
        self,
        agents: List[BaseAgent],
        entity_manager: EntityManager,
        component_manager: ComponentManager
    ):
        self.agents = agents
        self.entity_manager = entity_manager
        self.component_manager = component_manager
        self.critic = CriticAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="Supervisor",
            model="gpt-4"
        )
        self.logger = logging.getLogger(__name__)
        self.problem = None
        self.goal = None

    def run(self, problem: str, question: str) -> str:
        """
        Run the collaborative scenario.
        
        Args:
            problem: The problem statement.
            question: The question to answer.
        Returns:
            A final synthesized answer.
        """
        self.problem = problem
        self.goal = f"Collaboratively answer: {question}"
        central_logger.log_system_start("CollaborativeScenarioSystem", self.entity_manager.entities, problem, self.goal)
        self.logger.info(f"Scenario started: {self.goal}")

        # Initial agent responses.
        responses = {}
        for agent in self.agents:
            response = agent.interact(question)
            responses[agent.name] = response
            central_logger.log_interaction(agent.name, "System", f"Initial: {response}")
            time.sleep(1)  # simulate delay between responses

        # Critic analyzes the initial responses.
        critic_response = self.critic.interact(f"Analyze these responses and suggest improvements:\n{responses}")
        central_logger.log_interaction("Supervisor", "System", f"Critique: {critic_response}")
        
        # Optionally, if the critique suggests additional analysis, spawn an extra agent.
        if "suggest" in critic_response.lower():
            additional_agent = SimpleAgent(
                entity_manager=self.entity_manager,
                component_manager=self.component_manager,
                name="Analyst",
                model="gpt-4",
                system_prompt="Provide detailed and structured analysis."
            )
            self.agents.append(additional_agent)
            central_logger.log_interaction("System", "New Agent", f"Spawned additional agent: {additional_agent.name}")
            additional_response = additional_agent.interact(question)
            responses[additional_agent.name] = additional_response
            central_logger.log_interaction(additional_agent.name, "System", f"Additional: {additional_response}")
            time.sleep(1)
        
        # Final synthesis using the critic.
        final_answer = self.critic.interact(f"Based on these responses, synthesize a final answer:\n{responses}")
        central_logger.log_interaction("Supervisor", "System", f"Final synthesis: {final_answer}")

        # Simple evaluation and reward.
        evaluation = {"answer_length": len(final_answer), "success": len(final_answer) > 50}
        reward = 10 if evaluation["success"] else -5
        central_logger.log_system_end(final_answer, evaluation, reward)
        central_logger.flush_logs()

        return final_answer

def run_collaborative_scenario():
    """
    Set up the entity and component managers, create initial agents, and run the scenario.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    entity_manager = EntityManager()
    component_manager = ComponentManager()
    
    # Create initial agents.
    agents = [
        SimpleAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="LogicBot",
            tools=["calculator"]  # add tool if needed
        ),
        ChaosAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="ChaosMind"
        )
    ]
    
    # Instantiate and run the scenario.
    scenario = CollaborativeScenarioSystem(agents, entity_manager, component_manager)
    problem = "Enhance creativity and clarity in collaborative communication."
    question = "How can we balance structured logic and creative chaos in team problem-solving?"
    result = scenario.run(problem, question)
    
    print("\n=== FINAL ANSWER ===")
    print(result)
    return result

if __name__ == "__main__":
    run_collaborative_scenario()
