import json
import re
from typing import Dict
from .base_agent import BaseAgent

class SupervisorAgent(BaseAgent):
    def __init__(self, system_type: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.system_type = system_type

    def decide_agents(self, prompt: str) -> Dict:
        """
        Decide which agents to spawn and the sequence of tasks based on the provided prompt.
        Returns a dictionary with 'agents' (list of agent configurations) and 'task_sequence' (list of role names).
        
        Args:
            prompt (str): The complete prompt specifying the task and constraints, provided by the system.
        
        Returns:
            Dict: A dictionary containing 'agents' (list of agent configs) and 'task_sequence' (list of role names).
        
        Raises:
            ValueError: If the response cannot be parsed into the expected JSON format.
        """
        response = self.llm_client.query([{"role": "user", "content": prompt}])
        print(f"Supervisor response: {response}")  # For debugging
        try:
            decision = json.loads(response)
            if not isinstance(decision, dict) or "agents" not in decision or "task_sequence" not in decision:
                raise ValueError("Expected a dictionary with 'agents' and 'task_sequence' keys.")
            return decision
        except json.JSONDecodeError:
            match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    decision = json.loads(json_str)
                    if not isinstance(decision, dict) or "agents" not in decision or "task_sequence" not in decision:
                        raise ValueError("Expected a dictionary with 'agents' and 'task_sequence' keys.")
                    return decision
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse extracted JSON: {str(e)}")
            else:
                raise ValueError("No JSON block found in the response")