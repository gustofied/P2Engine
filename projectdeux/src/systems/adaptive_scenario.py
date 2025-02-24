#!/usr/bin/env python3
"""
Adaptive Scenario System

This system runs a collaborative multi-agent scenario in multiple rounds.
Agents (e.g. LogicBot and ChaosMind) provide initial responses to a question.
Then, over several rounds, a Critic agent (Supervisor) analyzes previous responses,
provides feedback, and agents update their answers accordingly.
Optionally, if the feedback suggests diversification, an additional agent is spawned.
Finally, the Critic synthesizes a final answer.
"""

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

class AdaptiveScenarioSystem:
    """
    Adaptive multi-agent scenario system.

    The system runs for a given number of rounds. In each round, agents update their responses
    based on previous answers and critic feedback. At the end, a final synthesis is generated.
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
        self.conversation_history = []
        self.problem = None
        self.goal = None

    def run(self, problem: str, question: str, rounds: int = 3) -> str:
        """
        Run the adaptive scenario system.

        Args:
            problem: The problem statement.
            question: The question to answer.
            rounds: Number of interactive rounds.
        Returns:
            The final synthesized answer.
        """
        self.problem = problem
        self.goal = f"Adaptively answer: {question}"
        central_logger.log_system_start("AdaptiveScenarioSystem", self.entity_manager.entities, problem, self.goal)
        self.logger.info(f"Adaptive scenario started: {self.goal}")

        # Initial round: agents provide their responses to the question.
        responses = {}
        for agent in self.agents:
            response = agent.interact(question)
            responses[agent.name] = response
            central_logger.log_interaction(agent.name, "System", f"Round 0: {response}")
            self._record_interaction(agent.name, "Round 0", response)
            time.sleep(1)

        # Run multiple rounds of refinement.
        for r in range(1, rounds + 1):
            self.logger.info(f"Starting round {r}")
            # Critic analyzes previous round responses and provides feedback.
            critic_feedback = self.critic.interact(
                f"Analyze these responses from round {r-1}: {responses}\n"
                f"Provide improvements for round {r}."
            )
            central_logger.log_interaction("Supervisor", "System", f"Critique round {r}: {critic_feedback}")
            self._record_interaction("Supervisor", f"Critique round {r}", critic_feedback)

            # If the feedback suggests diversification, spawn an additional agent.
            if "diversify" in critic_feedback.lower():
                additional_agent = SimpleAgent(
                    entity_manager=self.entity_manager,
                    component_manager=self.component_manager,
                    name=f"AdditionalAgent_R{r}",
                    model="gpt-4",
                    system_prompt="Provide a fresh perspective on the topic."
                )
                self.agents.append(additional_agent)
                central_logger.log_interaction("System", "New Agent", f"Spawned {additional_agent.name}")
                self._record_interaction("System", "New Agent", f"Spawned {additional_agent.name}")

            # Agents update their responses using previous responses and critic feedback as context.
            new_responses = {}
            for agent in self.agents:
                context = f"Previous responses: {responses}\nCritic feedback: {critic_feedback}"
                response = agent.interact(context)
                new_responses[agent.name] = response
                central_logger.log_interaction(agent.name, "System", f"Round {r}: {response}")
                self._record_interaction(agent.name, f"Round {r}", response)
                time.sleep(1)
            responses = new_responses

        # Final synthesis by the critic.
        final_answer = self.critic.interact(
            f"Based on all rounds of responses, synthesize a final comprehensive answer:\n{responses}"
        )
        central_logger.log_interaction("Supervisor", "System", f"Final synthesis: {final_answer}")
        self._record_interaction("Supervisor", "Final synthesis", final_answer)

        # Evaluate the final answer.
        evaluation = {"answer_length": len(final_answer), "success": len(final_answer) > 50}
        reward = 10 if evaluation["success"] else -5
        central_logger.log_system_end(final_answer, evaluation, reward)
        central_logger.flush_logs()

        return final_answer

    def _record_interaction(self, agent: str, stage: str, content: str):
        """Record an interaction in the conversation history and log it."""
        entry = {
            "agent": agent,
            "stage": stage,
            "content": content,
            "timestamp": time.time()
        }
        self.conversation_history.append(entry)
        central_logger.log_interaction(agent, "System", f"{stage}: {content}")

def run_adaptive_scenario():
    """
    Set up managers, create initial agents, and run the adaptive scenario.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    # Ensure your .env file is loaded (if using dotenv in other modules)
    from dotenv import load_dotenv
    load_dotenv()

    entity_manager = EntityManager()
    component_manager = ComponentManager()

    # Create initial agents.
    agents = [
        SimpleAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="LogicBot",
            tools=["calculator"]
        ),
        ChaosAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="ChaosMind"
        )
    ]

    system = AdaptiveScenarioSystem(agents, entity_manager, component_manager)
    problem = "Optimize team dynamics in innovative problem-solving."
    question = "How can teams leverage both analytical reasoning and creative spontaneity to solve complex problems?"
    result = system.run(problem, question, rounds=3)

    print("\n=== FINAL ANSWER ===")
    print(result)
    return result

if __name__ == "__main__":
    run_adaptive_scenario()
