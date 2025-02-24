import time
import logging
from dotenv import load_dotenv
from typing import List
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from custom_logging.central_logger import central_logger

load_dotenv()

from single_agents.base_agent import BaseAgent
from single_agents.simple_agent.agent import SimpleAgent
from single_agents.chaos_agent.agent import ChaosAgent
from single_agents.critic_agent.agent import CriticAgent

class GoalOrientedSystem:
    def __init__(self, initial_agents: List[BaseAgent], entity_manager: EntityManager, component_manager: ComponentManager):
        self.agents = initial_agents
        self.entity_manager = entity_manager
        self.component_manager = component_manager
        self.conversation_history = []
        self.critic = CriticAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="Supervisor",
            model="gpt-4"
        )
        self.logger = logging.getLogger(__name__)
        self.goal = None

    def _log_system_event(self, message: str):
        """Log system-level events to CentralLogger"""
        central_logger.log_interaction("System", "System", message)
        self.logger.info(message)

    def run_scenario(self, problem: str, question: str) -> str:
        """Run the scenario with a problem and goal"""
        self.goal = f"Comprehensively answer: {question}"
        central_logger.log_system_start("GoalOrientedSystem", self.entity_manager.entities, problem, self.goal)
        self._log_system_event(f"Starting system with goal: {self.goal}")

        initial_answers = self._get_initial_answers(question)
        self._expand_agents_based_on_critique(initial_answers)
        refined_answers = self._refine_answers(initial_answers)
        final_answer = self._final_synthesis(refined_answers)

        # Evaluate the result (simple heuristic for now: length of answer)
        evaluation = {"answer_length": len(final_answer), "success": len(final_answer) > 50}
        central_logger.log_system_end(final_answer, evaluation)
        central_logger.flush_logs()

        return final_answer

    def _get_initial_answers(self, question: str) -> dict:
        self._log_system_event("=== Initial Responses ===")
        answers = {}
        for agent in self.agents:
            response = agent.interact(question)
            answers[agent.name] = response
            self._record_interaction(agent.name, "initial", response)
            time.sleep(1)
        return answers

    def _expand_agents_based_on_critique(self, answers: dict):
        self._log_system_event("=== Critic Analysis ===")
        critique = self.critic.interact(
            f"Current answers: {answers}\nWhat type of new agents do we need to improve this?"
        )
        self._record_interaction("Critic", "analysis", critique)
        
        if "analytical" in critique.lower():
            new_agent = SimpleAgent(
                entity_manager=self.entity_manager,
                component_manager=self.component_manager,
                name="Analyst",
                model="gpt-4",
                system_prompt="Provide structured analysis with pros/cons lists"
            )
            self.agents.append(new_agent)
            central_logger.log_interaction("System", "New Agent", f"Spawned {new_agent.name}")

    def _refine_answers(self, initial_answers: dict) -> dict:
        self._log_system_event("=== Refinement Phase ===")
        refined = initial_answers.copy()
        
        for agent in self.agents:
            if agent.name not in initial_answers:
                context = f"Question: {self.goal}\nExisting Answers: {initial_answers}"
                response = agent.interact(context)
                refined[agent.name] = response
                self._record_interaction(agent.name, "refinement", response)
                time.sleep(1)
        
        return refined

    def _final_synthesis(self, all_answers: dict) -> str:
        self._log_system_event("=== Final Synthesis ===")
        synthesis_prompt = f"""Synthesize these responses into a final answer:
        {all_answers}
        
        Requirements:
        - Address all aspects of the original question
        - Resolve contradictions
        - Maintain key insights from each perspective
        """
        final_answer = self.critic.interact(synthesis_prompt)
        self._record_interaction("Critic", "synthesis", final_answer)
        return final_answer

    def _record_interaction(self, agent: str, stage: str, content: str):
        """Record structured interaction data"""
        entry = {
            "agent": agent,
            "stage": stage,
            "content": content,
            "timestamp": time.time()
        }
        self.conversation_history.append(entry)
        central_logger.log_interaction(agent, "System", f"{stage}: {content}")

def run_enhanced_scenario():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    entity_manager = EntityManager()
    component_manager = ComponentManager()
    initial_agents = [
        SimpleAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="LogicBot"
        ),
        ChaosAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="ChaosMind"
        )
    ]

    system = GoalOrientedSystem(initial_agents, entity_manager, component_manager)
    problem = "Determine the optimal city in Norway for tourism"
    question = "What is the best city in Norway?"
    
    result = system.run_scenario(problem, question)
    
    print("\n=== FINAL ANSWER ===")
    print(result)
    return result

if __name__ == "__main__":
    run_enhanced_scenario()