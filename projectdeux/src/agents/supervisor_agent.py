# src/agents/supervisor_agent.py
import json
import re
from typing import Dict
from .base_agent import BaseAgent

class SupervisorAgent(BaseAgent):
    def decide_agents(self, task: str, current_agents: Dict[str, "BaseAgent"] = None, context: str = "") -> Dict:
        """
        Decide agents and task sequence, optionally adapting existing agents.
        
        Args:
            task (str): The task to analyze.
            current_agents (Dict[str, BaseAgent], optional): Existing agents in the system.
            context (str, optional): Additional context to guide the decision.
            
        Returns:
            Dict: Contains 'agents' (list of configs) and 'task_sequence' (list of role names).
        """
        current_agents = current_agents or {}
        current_agent_info = {a.name: a.role for a in current_agents.values()}
        prompt = (
            "You are an AI assistant planning a collaborative project. "
            f"The task is: '{task}'. "
            f"Current agents: {current_agent_info}. "
            f"{context} "  # Include the context here
            "Determine which specialized AI agents are needed (e.g., 'researcher', 'writer', 'editor'). "
            "For each agent, provide 'name', 'role', 'task' (from available tasks: plan_research, writer_task, editor_task), "
            "'queue', and 'system_prompt'. If an existing agent's role should change, include it with the updated 'role'. "
            "Also, specify the sequence of roles to execute tasks. "
            "Return a JSON object with 'agents' (array of configs) and 'task_sequence' (array of role names)."
        )
        response = self.llm_client.query([{"role": "user", "content": prompt}])
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

    def adapt_agents(self, task: str, system: "CollaborativeWritingSystem") -> list:
        """
        Adapt agents mid-run based on task progress.

        Args:
            task (str): The updated task or context.
            system (CollaborativeWritingSystem): The system instance to adapt agents within.

        Returns:
            list: Updated task sequence.
        """
        # Add explicit instruction to avoid research tasks in the adaptive phase
        context = "The initial research task has been completed. Focus on tasks like writing, editing, and finalizing the article. Do not include research tasks."
        decision = self.decide_agents(task, system.agents, context=context)
        agent_configs = decision["agents"]
        task_sequence = decision["task_sequence"]

        # Update or spawn agents based on the decision
        for config in agent_configs:
            agent_name = config["name"]
            if agent_name in system.agents:
                # Update existing agent's role if it has changed
                agent = system.agents[agent_name]
                if agent.role != config["role"]:
                    agent.role = config["role"]
                    system.task_manager.agent_queues[agent_name] = config["queue"]
            else:
                # Spawn a new agent if it doesn’t exist
                system.spawn_agent(config)

        return task_sequence