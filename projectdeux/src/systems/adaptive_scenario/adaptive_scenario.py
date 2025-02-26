# systems/adaptive_scenario/adaptive_scenario.py
import json
import time
from agents.factory import AgentFactory  # Only import AgentFactory
from systems.base_system import BaseSystem

class AdaptiveScenarioSystem(BaseSystem):
    def __init__(self, agents, entity_manager, component_manager, config):
        super().__init__(agents, entity_manager, component_manager)
        self.config = config
        # Define configuration for the critic agent
        critic_config = {
            "name": "Supervisor",
            "model": "github/gpt-4o",
            "system_prompt": "You are a critic analyzing the conversation. Provide feedback to improve the agents' responses."
        }
        # Create the critic agent using AgentFactory
        self.critic = AgentFactory.create_agent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=critic_config
        )
        self.conversation_history = []

    def run(self, problem: str, question: str):
        rounds = self.config.get("rounds", 3)  # Default to 3 rounds if not specified
        self.log_start(problem)

        # Initial round: agents provide their responses
        responses = {}
        for agent in self.agents:
            response = agent.interact(question)
            responses[agent.name] = response
            self.logger.log_interaction(agent.name, "System", f"Round 0: {response}")
            self._record_interaction(agent.name, "Round 0", response)

        # Multiple rounds of refinement
        for r in range(1, rounds + 1):
            critic_feedback = self.critic.interact(
                f"Analyze these responses from round {r-1}: {responses}\nProvide improvements for round {r}."
            )
            self.logger.log_interaction("Supervisor", "System", f"Critique round {r}: {critic_feedback}")
            self._record_interaction("Supervisor", f"Critique round {r}", critic_feedback)

            # Dynamic spawning based on config condition
            if self.config.get("spawn_condition", "") in critic_feedback.lower():
                new_agent_config = self.config.get("new_agent_config", {})
                additional_agent = AgentFactory.create_agent(
                    entity_manager=self.entity_manager,
                    component_manager=self.component_manager,
                    config=new_agent_config
                )
                self.agents.append(additional_agent)
                self.logger.log_interaction("System", "New Agent", f"Spawned {additional_agent.name}")
                self._record_interaction("System", "New Agent", f"Spawned {additional_agent.name}")

            new_responses = {}
            for agent in self.agents:
                context = f"Previous responses: {responses}\nCritic feedback: {critic_feedback}"
                response = agent.interact(context)
                new_responses[agent.name] = response
                self.logger.log_interaction(agent.name, "System", f"Round {r}: {response}")
                self._record_interaction(agent.name, f"Round {r}", response)
            responses = new_responses

        final_answer = self.critic.interact(
            f"Based on all rounds of responses, synthesize a final comprehensive answer:\n{responses}"
        )
        self.logger.log_interaction("Supervisor", "System", f"Final synthesis: {final_answer}")
        self._record_interaction("Supervisor", "Final synthesis", final_answer)

        evaluation = {"answer_length": len(final_answer), "success": len(final_answer) > 50}
        reward = 10 if evaluation["success"] else -5
        self.log_end(final_answer, evaluation, reward)
        return final_answer

    def _record_interaction(self, agent: str, stage: str, content: str):
        entry = {
            "agent": agent,
            "stage": stage,
            "content": content,
            "timestamp": time.time()
        }
        self.conversation_history.append(entry)
        self.logger.log_interaction(agent, "System", f"{stage}: {content}")
