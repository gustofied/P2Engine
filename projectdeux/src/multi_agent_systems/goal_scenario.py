import time
import logging
from dotenv import load_dotenv
from typing import List
from custom_logging.litellm_logger import my_custom_logging_fn
from custom_logging.simple_logger import log_message, flush_simple_logs

load_dotenv()

from single_agents.base_agent import BaseAgent
from single_agents.simple_agent.agent import SimpleAgent
from single_agents.chaos_agent.agent import ChaosAgent
from single_agents.critic_agent.agent import CriticAgent

class GoalOrientedSystem:
    def __init__(self, initial_agents: List[BaseAgent]):
        self.agents = initial_agents
        self.conversation_history = []
        self.critic = CriticAgent(
            name="Supervisor", 
            model="gpt-4",
        )
        self.logger = logging.getLogger(__name__)
        self.goal = None

    def _log_system_event(self, message: str):
        """Log system-level events to both logging systems"""
        log_message("System", "System", message)
        self.logger.info(message)

    def run_scenario(self, question: str) -> str:
        self.goal = f"Comprehensively answer: {question}"
        self._log_system_event(f"Starting scenario with goal: {self.goal}")
        
        # Initial response phase
        initial_answers = self._get_initial_answers(question)
        
        # Analysis and expansion phase
        self._expand_agents_based_on_critique(initial_answers)
        
        # Collaborative refinement phase
        refined_answers = self._refine_answers(initial_answers)
        
        # Final synthesis
        final_answer = self._final_synthesis(refined_answers)
        
        # Explicitly flush logs at end of scenario
        flush_simple_logs()
        return final_answer

    def _get_initial_answers(self, question: str) -> dict:
        self._log_system_event("=== Initial Responses ===")
        answers = {}
        for agent in self.agents:
            response = agent.interact(question)
            answers[agent.name] = response
            log_message(agent.name, "System", response)
            self._record_interaction(agent.name, "initial", response)
            time.sleep(1)
        return answers

    def _expand_agents_based_on_critique(self, answers: dict):
        self._log_system_event("=== Critic Analysis ===")
        critique = self.critic.interact(
            f"Current answers: {answers}\nWhat type of new agents do we need to improve this?"
        )
        log_message("Critic", "System", critique)
        self._record_interaction("Critic", "analysis", critique)
        
        # Spawn new agents based on critique
        if "analytical" in critique.lower():
            new_agent = SimpleAgent(
                name="Analyst", 
                model="gpt-4",
                system_prompt="Provide structured analysis with pros/cons lists"
            )
            self.agents.append(new_agent)
            log_message("System", "New Agent", f"Spawned {new_agent.name}")

    def _refine_answers(self, initial_answers: dict) -> dict:
        self._log_system_event("=== Refinement Phase ===")
        refined = initial_answers.copy()
        
        for agent in self.agents:
            if agent.name not in initial_answers:
                context = f"Question: {self.goal}\nExisting Answers: {initial_answers}"
                response = agent.interact(context)
                refined[agent.name] = response
                log_message(agent.name, "System", response)
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
        log_message("Critic", "Final Answer", final_answer)
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

def run_enhanced_scenario():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    # Initialize core agents
    initial_agents = [
        SimpleAgent(name="LogicBot"),
        ChaosAgent(name="ChaosMind")
    ]

    system = GoalOrientedSystem(initial_agents)
    question = "What is thr best city in Norway?"
    
    result = system.run_scenario(question)
    
    print("\n=== FINAL ANSWER ===")
    print(result)
    return result

if __name__ == "__main__":
    run_enhanced_scenario()