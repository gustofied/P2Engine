#!/usr/bin/env python3
"""
Adaptive Scenario System

This system runs a collaborative multi-agent scenario in multiple rounds.
Agents provide initial responses to a question.
Then, over several rounds, a Critic agent analyzes previous responses,
provides feedback, and agents update their answers accordingly.
If the feedback suggests diversification, a new agent is dynamically spawned.
Finally, the Critic synthesizes a final answer.
"""

import time
import logging
from typing import List
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from custom_logging.central_logger import central_logger
from single_agents.simple_agent import SimpleAgent
from single_agents.chaos_agent import ChaosAgent
from single_agents.critic_agent import CriticAgent

# Import the new factory for composable agents.
from single_agents.composable_agent import AgentFactory, default_llm_client_factory

class AdaptiveScenarioSystem:
    def __init__(
        self,
        agents: List,
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
        self.problem = problem
        self.goal = f"Adaptively answer: {question}"
        central_logger.log_system_start("AdaptiveScenarioSystem", self.entity_manager.entities, problem, self.goal)
        self.logger.info(f"Adaptive scenario started: {self.goal}")

        # Initial round: agents provide their responses.
        responses = {}
        for agent in self.agents:
            response = agent.interact(question)
            responses[agent.name] = response
            central_logger.log_interaction(agent.name, "System", f"Round 0: {response}")
            self._record_interaction(agent.name, "Round 0", response)
            time.sleep(1)

        # Multiple rounds of refinement.
        for r in range(1, rounds + 1):
            self.logger.info(f"Starting round {r}")
            critic_feedback = self.critic.interact(
                f"Analyze these responses from round {r-1}: {responses}\nProvide improvements for round {r}."
            )
            central_logger.log_interaction("Supervisor", "System", f"Critique round {r}: {critic_feedback}")
            self._record_interaction("Supervisor", f"Critique round {r}", critic_feedback)

            # Use the composable-agent factory for dynamic spawning.
            if "diversify" in critic_feedback.lower():
                factory = AgentFactory(default_llm_client_factory)
                new_agent_config = {
                    "name": f"AdditionalAgent_R{r}",
                    "model": "gpt-4",
                    "api_key": None,  # Uses environment variables if not provided.
                    "behaviors": {
                        "format_messages": lambda msg: [
                            {"role": "system", "content": "Provide a fresh perspective on the topic."},
                            {"role": "user", "content": msg}
                        ]
                    },
                    "tools": []
                }
                additional_agent = factory.spawn_agent_from_config(new_agent_config)
                self.agents.append(additional_agent)
                central_logger.log_interaction("System", "New Agent", f"Spawned {additional_agent.name}")
                self._record_interaction("System", "New Agent", f"Spawned {additional_agent.name}")

            new_responses = {}
            for agent in self.agents:
                context = f"Previous responses: {responses}\nCritic feedback: {critic_feedback}"
                response = agent.interact(context)
                new_responses[agent.name] = response
                central_logger.log_interaction(agent.name, "System", f"Round {r}: {response}")
                self._record_interaction(agent.name, f"Round {r}", response)
                time.sleep(1)
            responses = new_responses

        final_answer = self.critic.interact(
            f"Based on all rounds of responses, synthesize a final comprehensive answer:\n{responses}"
        )
        central_logger.log_interaction("Supervisor", "System", f"Final synthesis: {final_answer}")
        self._record_interaction("Supervisor", "Final synthesis", final_answer)

        evaluation = {"answer_length": len(final_answer), "success": len(final_answer) > 50}
        reward = 10 if evaluation["success"] else -5
        central_logger.log_system_end(final_answer, evaluation, reward)
        central_logger.flush_logs()
        return final_answer

    def _record_interaction(self, agent: str, stage: str, content: str):
        entry = {
            "agent": agent,
            "stage": stage,
            "content": content,
            "timestamp": time.time()
        }
        self.conversation_history.append(entry)
        central_logger.log_interaction(agent, "System", f"{stage}: {content}")

def run_adaptive_scenario():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    from dotenv import load_dotenv
    load_dotenv()

    entity_manager = EntityManager()
    component_manager = ComponentManager()

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
