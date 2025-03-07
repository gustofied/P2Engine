import os
import re
import random
from typing import Dict, List, Optional
from src.systems.base_system import BaseSystem
from src.custom_logging.central_logger import CentralLogger
import datetime
from sklearn.linear_model import LinearRegression
import time

central_logger = CentralLogger()

class MetaSystemInventor(BaseSystem):
    def __init__(self, agents, entity_manager, component_manager, config: Dict, run_id: str):
        super().__init__(agents, entity_manager, component_manager, config)
        self.run_id = run_id
        self.history: List[Dict] = []  # Archive of proposals and evaluations
        self.best_architecture: Optional[Dict] = None
        self.best_score: float = -1
        self.exploration_rate = config.get("exploration_rate", 0.3)  # 30% chance for new ideas
        self.world_model = None  # World Model for prediction
        self.world_model_data = []  # Data for training World Model

    def define_workflow(self) -> List[Dict]:
        """
        Define the workflow for MetaSystemInventor. Since this system uses run_discovery_loop
        directly in the run method, this remains a placeholder to satisfy the abstract method.
        """
        return []

    def extract_features(self, proposal: Dict) -> List[float]:
        """
        Extract numerical features from the proposal for World Model training.
        """
        code = proposal["code"]
        explanation = proposal["explanation"]
        num_agents = code.lower().count("agent")
        has_communication = 1 if "communicate" in code.lower() else 0
        explanation_length = len(explanation)
        return [num_agents, has_communication, explanation_length]

    def get_valid_proposal(self, architect, prompt: str, max_retries: int = 3) -> Optional[Dict]:
        for _ in range(max_retries):
            response = architect.interact(prompt)
            if "EXPLANATION:" in response and "CODE:" in response:
                parts = response.split("EXPLANATION:", 1)[1].split("CODE:", 1)
                explanation = parts[0].strip()
                code_parts = parts[1].split("META:", 1)
                code = code_parts[0].strip()
                meta = code_parts[1].strip() if len(code_parts) > 1 else ""
                return {"explanation": explanation, "code": code, "meta": meta}
            central_logger.log_interaction("System", "Debug", f"Invalid format: {response}")
        return None

    def run_discovery_loop(self, problem: str, iterations: int) -> Dict:
        architect = self.agents[0]  # Architect
        evaluator = self.agents[1]  # Evaluator
        manager = self.agents[2]    # Manager

        # Pseudo-code representation of the system for self-understanding
        system_pseudo_code = """
class MetaSystemInventor:
    def __init__(self):
        self.agents = [Architect(), Evaluator(), Manager()]
        self.history = []
        self.world_model = WorldModel()

    def run_discovery(self, problem, iterations):
        for i in range(iterations):
            proposal = self.agents[0].propose(problem, self.history)
            prediction = self.world_model.predict(proposal)
            evaluation = self.agents[1].evaluate(proposal, self.history, prediction)
            decision = self.agents[2].decide(proposal, evaluation, self.history)
            self.history.append((proposal, evaluation, decision))
            self.world_model.train(proposal, evaluation)
            if decision.improves_system:
                self.update_structure(decision.meta_suggestion)
"""

        for i in range(iterations):
            # Prepare history summary for context
            history_summary = "\n".join(
                f"Iteration {e['iteration']}: Overall Score {e['scores']['overall']}/10 - {e['explanation'][:50]}..."
                for e in self.history
            ) if self.history else "No previous proposals."

            # Calculate recent average simplicity score (last 3 iterations)
            recent_simplicity = [e['scores']['simplicity'] for e in self.history[-3:]] if self.history else []
            avg_simplicity = sum(recent_simplicity) / len(recent_simplicity) if recent_simplicity else 0

            # Decide: refine, generate new, or improve system
            if i == 0 or random.random() < self.exploration_rate or not self.best_architecture:
                prompt = (
                    f"You are part of a system defined as:\n{system_pseudo_code}\n"
                    f"Propose a multi-agent architecture for solving {problem}. "
                    f"Push beyond conventional thinking. History:\n{history_summary}"
                )
                if avg_simplicity < 5:
                    prompt += "\nFocus on proposing simpler architectures with fewer agents or clearer interactions."
                proposal_type = "new"
            else:
                refinement_instructions = (
                    "Refine the architecture to improve its performance while maintaining simplicity."
                    if avg_simplicity >= 5 else
                    "Refine the architecture by simplifying it, perhaps by reducing the number of agents or streamlining their roles."
                )
                prompt = (
                    f"You are part of a system defined as:\n{system_pseudo_code}\n"
                    f"Refine this architecture:\n"
                    f"Explanation: {self.best_architecture['explanation']}\n"
                    f"Code: {self.best_architecture['code']}\n"
                    f"Evaluation: {self.history[-1]['feedback']}\n"
                    f"Instructions: {refinement_instructions}\n"
                    f"History:\n{history_summary}"
                )
                proposal_type = "refinement"

            # Generate proposal
            proposal = self.get_valid_proposal(architect, prompt)
            if not proposal:
                central_logger.log_interaction("System", "Warning", "No valid proposal received.")
                continue

            # Extract features for World Model
            features = self.extract_features(proposal)

            # Predict with World Model if trained
            world_prediction = "World Model not yet trained."
            if self.world_model is not None and len(self.world_model_data) >= 10:
                predicted_score = self.world_model.predict([features])[0]
                world_prediction = f"World Model predicts overall score: {predicted_score:.1f}/10"

            # Evaluate proposal with timing
            evaluation_prompt = (
                f"You are part of a system defined as:\n{system_pseudo_code}\n"
                f"Evaluate this architecture:\n"
                f"Explanation: {proposal['explanation']}\n"
                f"Code: {proposal['code']}\n"
                f"{world_prediction}\n"
                f"Provide sub-scores for novelty, feasibility, simplicity, and discovery potential (each out of 10), "
                f"followed by an overall score and a critique. If the actual overall score differs from the World Model's "
                f"prediction by more than 2 points, investigate potential anomalies in your critique. "
                f"Format as: 'Scores: novelty (X/10), feasibility (Y/10), simplicity (Z/10), discovery potential (W/10), overall score (V/10)'. "
                f"History:\n{history_summary}"
            )
            start_time = time.time()
            feedback = evaluator.interact(evaluation_prompt)
            eval_time = time.time() - start_time
            if eval_time > 1:  # Threshold in seconds
                central_logger.log_interaction("System", "Warning", f"Evaluation took {eval_time:.2f}s—consider optimizing.")

            # Parse sub-scores from feedback
            score_pattern = r"Scores: novelty \((\d{1,2})/10\), feasibility \((\d{1,2})/10\), simplicity \((\d{1,2})/10\), discovery potential \((\d{1,2})/10\), overall score \((\d{1,2})/10\)"
            match = re.search(score_pattern, feedback)
            if match:
                novelty = int(match.group(1))
                feasibility = int(match.group(2))
                simplicity = int(match.group(3))
                discovery = int(match.group(4))
                overall = int(match.group(5))
            else:
                central_logger.log_interaction("System", "Warning", "Could not parse scores from feedback.")
                novelty = feasibility = simplicity = discovery = overall = 0

            # Store data for World Model training
            self.world_model_data.append({
                "features": features,
                "target": overall
            })

            # Train World Model periodically
            if len(self.world_model_data) >= 10 and (i + 1) % 5 == 0:
                X = [d["features"] for d in self.world_model_data]
                y = [d["target"] for d in self.world_model_data]
                self.world_model = LinearRegression()
                self.world_model.fit(X, y)
                central_logger.log_interaction("System", "Info", "World Model updated.")

            # Manager decides next step
            manager_prompt = (
                f"You are the coordinator of a self-improving discovery system, defined as:\n{system_pseudo_code}\n"
                f"Given the latest proposal, its evaluation with sub-scores (novelty, feasibility, simplicity, discovery potential), "
                f"and the history, decide to:\n"
                f"1. Refine the current best architecture (instructions for Architect),\n"
                f"2. Generate a new one (focus areas, e.g., simplicity if avg_simplicity < 5),\n"
                f"3. Improve the system itself (e.g., add/modify agents, adjust processes).\n"
                f"Output 'DECISION: refine/new/system', 'INSTRUCTIONS:', and 'META:' if system-level changes are proposed.\n"
                f"Proposal:\n{proposal['explanation']}\n"
                f"Code: {proposal['code']}\n"
                f"Evaluation: {feedback}\n"
                f"Scores: novelty {novelty}/10, feasibility {feasibility}/10, simplicity {simplicity}/10, "
                f"discovery potential {discovery}/10, overall {overall}/10\n"
                f"Recent average simplicity score: {avg_simplicity:.1f}/10\n"
                f"History:\n{history_summary}"
            )
            decision = manager.interact(manager_prompt)
            decision_match = re.search(r"DECISION:\s*(refine|new|system)", decision)
            instructions_match = re.search(r"INSTRUCTIONS:\s*(.*)", decision, re.DOTALL)
            meta_match = re.search(r"META:\s*(.*)", decision, re.DOTALL)
            decision_type = decision_match.group(1) if decision_match else "refine"
            instructions = instructions_match.group(1).strip() if instructions_match else ""
            meta = meta_match.group(1).strip() if meta_match else ""

            # Log the iteration
            entry = {
                "iteration": i + 1,
                "type": proposal_type,
                "explanation": proposal["explanation"],
                "code": proposal["code"],
                "meta": proposal["meta"],
                "feedback": feedback,
                "scores": {
                    "novelty": novelty,
                    "feasibility": feasibility,
                    "simplicity": simplicity,
                    "discovery": discovery,
                    "overall": overall
                },
                "manager_decision": decision_type,
                "manager_instructions": instructions,
                "manager_meta": meta,
                "timestamp": datetime.datetime.now().isoformat()
            }
            self.history.append(entry)

            # Apply system-level improvements if suggested
            if decision_type == "system" and meta:
                self.apply_system_improvement(meta)

            # Update best architecture
            if overall > self.best_score:
                self.best_score = overall
                self.best_architecture = proposal

        return self.best_architecture

    def apply_system_improvement(self, meta: str):
        """
        Apply system-level improvements suggested by the Manager (e.g., adding an agent).
        This is a placeholder for dynamic updates to the system structure.
        """
        central_logger.log_interaction("System", "Info", f"Applying system improvement: {meta}")

    def generate_compendium(self, output_dir: str = "discovery"):
        os.makedirs(output_dir, exist_ok=True)
        run_id = central_logger.global_log_data["run_id"]
        output_file = os.path.join(output_dir, f"architectures_{run_id}.md")
        with open(output_file, "w") as f:
            f.write(f"# Architecture Compendium for Run {run_id}\n\n")
            for entry in self.history:
                f.write(f"## Iteration {entry['iteration']} ({entry['type']})\n")
                f.write(f"### Explanation\n{entry['explanation']}\n\n")
                f.write(f"### Code\n```python\n{entry['code']}\n```\n\n")
                if entry["meta"]:
                    f.write(f"### Meta-Improvement\n{entry['meta']}\n\n")
                f.write(f"### Feedback\n{entry['feedback']}\n\n")
                f.write(f"### Scores\n- Novelty: {entry['scores']['novelty']}/10\n- Feasibility: {entry['scores']['feasibility']}/10\n"
                        f"- Simplicity: {entry['scores']['simplicity']}/10\n- Discovery Potential: {entry['scores']['discovery']}/10\n"
                        f"- Overall: {entry['scores']['overall']}/10\n\n")
                f.write(f"### Manager Decision\n{entry['manager_decision']} - {entry['manager_instructions']}\n")
                if entry["manager_meta"]:
                    f.write(f"### Manager Meta\n{entry['manager_meta']}\n\n")
            if self.best_architecture:
                f.write("## Best Architecture\n")
                f.write(f"### Explanation\n{self.best_architecture['explanation']}\n\n")
                f.write(f"### Code\n```python\n{self.best_architecture['code']}\n```\n")
                f.write(f"**Best Score:** {self.best_score}/10\n")

    def run(self, **kwargs) -> Dict:
        problem = self.config.get("problem", "Invent a self-improving MAS for discovery.")
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