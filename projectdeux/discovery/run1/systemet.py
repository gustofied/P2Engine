import os
import re
from typing import Dict, List, Optional
from src.systems.base_system import BaseSystem
from src.custom_logging.central_logger import CentralLogger
import datetime

central_logger = CentralLogger()

class MetaSystemInventor(BaseSystem):  # Changed from DiscoverySystem
    def __init__(self, agents, entity_manager, component_manager, config: Dict, run_id: str):
        super().__init__(agents, entity_manager, component_manager, config)
        self.run_id = run_id
        self.history: List[Dict] = []
        self.best_architecture: Optional[Dict] = None
        self.best_score: float = -1

    def define_workflow(self) -> List[Dict]:
        """
        Placeholder for define_workflow. Not used in MetaSystemInventor as the run method directly calls run_discovery_loop.
        """
        return []

    def get_valid_proposal(self, architect, prompt, max_retries=3) -> Optional[Dict]:
        for _ in range(max_retries):
            response = architect.interact(prompt)
            if "EXPLANATION:" in response and "CODE:" in response:
                parts = response.split("EXPLANATION:", 1)[1].split("CODE:", 1)
                explanation = parts[0].strip()
                code = parts[1].strip()
                return {"explanation": explanation, "code": code}
            central_logger.log_interaction("System", "Debug", f"Invalid format: {response}")
        return None

    def run_discovery_loop(self, problem: str, iterations: int) -> Dict:
        architect = self.agents[0]  # Architect
        evaluator = self.agents[1]  # Evaluator
        refiner = self.agents[2]    # Refiner

        previous_proposal = None
        previous_evaluation = None
        previous_suggestions = None

        for i in range(iterations):
            if previous_proposal is None:
                prompt = f"Propose a multi-agent architecture for solving {problem}."
            else:
                prompt = (
                    f"Here is the previous proposal:\n{previous_proposal}\n\n"
                    f"Evaluation:\n{previous_evaluation}\n\n"
                    f"Suggestions for improvement:\n{previous_suggestions}\n\n"
                    f"Based on this, propose an improved multi-agent architecture."
                )
            proposal = self.get_valid_proposal(architect, prompt)
            if not proposal:
                central_logger.log_interaction("System", "Warning", "No valid proposal received.")
                continue

            evaluation_prompt = (
                f"Evaluate this architecture:\n\n"
                f"Explanation:\n{proposal['explanation']}\n\n"
                f"Python Code:\n{proposal['code']}"
            )
            feedback = evaluator.interact(evaluation_prompt)
            score_match = re.search(r"Score:\s*(\d{1,2})/10", feedback)
            if score_match:
                score = int(score_match.group(1))
            else:
                central_logger.log_interaction("System", "Debug", f"Invalid feedback format: {feedback}")
                continue

            refinement_prompt = (
                f"Here is the proposal:\n{proposal['explanation']}\n\n"
                f"Python Code:\n{proposal['code']}\n\n"
                f"Evaluation:\n{feedback}\n\n"
                f"Suggest specific improvements to this architecture."
            )
            suggestions = refiner.interact(refinement_prompt)

            entry = {
                "iteration": i + 1,
                "explanation": proposal["explanation"],
                "code": proposal["code"],
                "feedback": feedback,
                "score": score,
                "suggestions": suggestions,
                "timestamp": datetime.datetime.now().isoformat()
            }
            self.history.append(entry)

            if score > self.best_score:
                self.best_score = score
                self.best_architecture = proposal

            previous_proposal = f"{proposal['explanation']}\n\n{proposal['code']}"
            previous_evaluation = feedback
            previous_suggestions = suggestions

        return self.best_architecture

    def generate_compendium(self, output_dir="discovery"):
        os.makedirs(output_dir, exist_ok=True)
        run_id = central_logger.global_log_data["run_id"]
        output_file = os.path.join(output_dir, f"architectures_{run_id}.md")
        
        with open(output_file, "w") as f:
            f.write(f"# Architecture Compendium for Run {run_id}\n\n")
            for entry in self.history:
                f.write(f"## Iteration {entry['iteration']} (Proposed at: {entry['timestamp']})\n")
                f.write(f"### Explanation\n{entry['explanation']}\n\n")
                f.write(f"### Python Code\n```python\n{entry['code']}\n```\n\n")
                f.write(f"### Feedback\n{entry['feedback']}\n\n")
                f.write(f"### Suggestions\n{entry['suggestions']}\n\n")
            
            if self.best_architecture:
                f.write("## Best Architecture\n")
                f.write(f"### Explanation\n{self.best_architecture['explanation']}\n\n")
                f.write(f"### Python Code\n```python\n{self.best_architecture['code']}\n```\n")
                f.write(f"**Best Score:** {self.best_score}/10\n")
            
            if self.history:
                total_iterations = len(self.history)
                time_spent = central_logger.scenario_logs[-1]["time_spent"] if central_logger.scenario_logs else 0
                f.write("\n## Summary\n")
                f.write(f"- Total iterations: {total_iterations}\n")
                f.write(f"- Time spent: {time_spent:.2f} seconds\n")
                f.write(f"- Best score: {self.best_score}/10\n")

    def run(self, **kwargs) -> Dict:
        problem = self.config.get("problem", "Unnamed problem")
        iterations = self.config.get("iterations", 15)
        self.log_start(problem)
        best_architecture = self.run_discovery_loop(problem, iterations)
        self.log_end(
            result=str(best_architecture),
            metadata={"iterations": iterations, "history_size": len(self.history)},
            score=self.best_score
        )
        self.generate_compendium()
        return {"best_architecture": best_architecture, "history": self.history}