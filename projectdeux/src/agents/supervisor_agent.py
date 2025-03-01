# src/agents/supervisor_agent.py
import json
import re
from typing import Dict
from .base_agent import BaseAgent

class SupervisorAgent(BaseAgent):
    def decide_agents(self, task: str) -> Dict:
        """
        Decide which agents to spawn and the sequence of tasks based on the task by querying the LLM.
        Returns a dictionary with 'agents' (list of agent configurations including task names) and 'task_sequence' (list of role names).
        """
        prompt = (
            "You are an AI assistant helping to plan a collaborative project. "
            f"The task is: '{task}'. "
            "Determine which specialized AI agents are needed (e.g., 'researcher', 'outliner', 'writer', 'editor', 'finalizer'). "
            "Each agent should have a 'name', 'role', 'task' (from available tasks: plan_research, create_outline, writer_task, editor_task, finalize_article), "
            "'queue', and 'system_prompt'. Also, specify the sequence of roles to execute their tasks in order. "
            "Return a JSON object with 'agents' (array of agent configs) and 'task_sequence' (array of role names)."
            "\n\nExample response:\n```json\n"
            "{\n  \"agents\": [\n    {\"name\": \"ResearchBot\", \"role\": \"researcher\", \"task\": \"plan_research\", \"queue\": \"research_queue\", \"system_prompt\": \"Research thoroughly.\"},\n"
            "    {\"name\": \"OutlineBot\", \"role\": \"outliner\", \"task\": \"create_outline\", \"queue\": \"outlining_queue\", \"system_prompt\": \"Create an outline.\"},\n"
            "    {\"name\": \"WriteBot\", \"role\": \"writer\", \"task\": \"writer_task\", \"queue\": \"writing_queue\", \"system_prompt\": \"Write a draft.\"},\n"
            "    {\"name\": \"EditBot\", \"role\": \"editor\", \"task\": \"editor_task\", \"queue\": \"editing_queue\", \"system_prompt\": \"Edit for clarity.\"},\n"
            "    {\"name\": \"FinalizeBot\", \"role\": \"finalizer\", \"task\": \"finalize_article\", \"queue\": \"finalizing_queue\", \"system_prompt\": \"Finalize article.\"}\n  ],\n"
            "  \"task_sequence\": [\"researcher\", \"outliner\", \"writer\", \"editor\", \"finalizer\"]\n}\n```"
        )
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