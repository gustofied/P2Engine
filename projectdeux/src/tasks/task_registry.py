from celery_app import app
from src.integrations.llm.llm_client import LLMClient
import datetime
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

TASK_REGISTRY = {}

def register_task(task_name: str, description: str, func):
    """Register a task in the global registry."""
    TASK_REGISTRY[task_name] = {
        "description": description,
        "function": func
    }

# Writing Tasks
@app.task
def plan_research(agent_id: str, topic: str, scenario_data):
    logger.info(f"Starting plan_research for agent {agent_id}")
    system_prompt = scenario_data["system_prompts"][scenario_data["agent_names"][agent_id]]
    agent_name = scenario_data["agent_names"][agent_id]
    llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Generate a detailed plan for an article about {topic}."}
    ]
    plan = llm_client.query(messages)
    interaction = {
        "from": agent_name,
        "to": "System",
        "message": f"Generated plan:\n{plan}",
        "timestamp": datetime.datetime.now().isoformat()
    }
    litellm_log = {
        "agent_id": agent_id,
        "model": "deepseek/deepseek-chat",
        "messages": messages,
        "response": plan,
        "timestamp": datetime.datetime.now().isoformat()
    }
    logger.info(f"Completed plan_research for agent {agent_id}")
    return plan, [interaction], scenario_data, [litellm_log]

@app.task
def create_outline(previous_output, agent_id: str):
    logger.info(f"Starting create_outline for agent {agent_id}")
    if not previous_output:
        raise ValueError("create_outline requires previous output")
    research_data, logs, scenario_data, litellm_logs = previous_output
    system_prompt = scenario_data["system_prompts"][scenario_data["agent_names"][agent_id]]
    agent_name = scenario_data["agent_names"][agent_id]
    llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Create an outline based on this research: {research_data}"}
    ]
    outline = llm_client.query(messages)
    interaction = {
        "from": agent_name,
        "to": "System",
        "message": f"Generated outline:\n{outline}",
        "timestamp": datetime.datetime.now().isoformat()
    }
    logs.append(interaction)
    litellm_log = {
        "agent_id": agent_id,
        "model": "deepseek/deepseek-chat",
        "messages": messages,
        "response": outline,
        "timestamp": datetime.datetime.now().isoformat()
    }
    litellm_logs.append(litellm_log)
    logger.info(f"Completed create_outline for agent {agent_id}")
    return outline, logs, scenario_data, litellm_logs

@app.task
def writer_task(previous_output, agent_id: str):
    logger.info(f"Starting writer_task for agent {agent_id}")
    if not previous_output:
        raise ValueError("writer_task requires previous output")
    plan, logs, scenario_data, litellm_logs = previous_output
    system_prompt = scenario_data["system_prompts"][scenario_data["agent_names"][agent_id]]
    agent_name = scenario_data["agent_names"][agent_id]
    llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Write an initial draft based on this plan: {plan}"}
    ]
    draft = llm_client.query(messages)
    interaction = {
        "from": agent_name,
        "to": "System",
        "message": f"Wrote draft:\n{draft}",
        "timestamp": datetime.datetime.now().isoformat()
    }
    logs.append(interaction)
    litellm_log = {
        "agent_id": agent_id,
        "model": "deepseek/deepseek-chat",
        "messages": messages,
        "response": draft,
        "timestamp": datetime.datetime.now().isoformat()
    }
    litellm_logs.append(litellm_log)
    logger.info(f"Completed writer_task for agent {agent_id}")
    return draft, logs, scenario_data, litellm_logs

@app.task
def editor_task(previous_output, agent_id: str):
    logger.info(f"Starting editor_task for agent {agent_id}")
    if not previous_output:
        raise ValueError("editor_task requires previous output")
    draft, logs, scenario_data, litellm_logs = previous_output
    system_prompt = scenario_data["system_prompts"][scenario_data["agent_names"][agent_id]]
    agent_name = scenario_data["agent_names"][agent_id]
    llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Refine and polish this draft: {draft}"}
    ]
    final_article = llm_client.query(messages)
    interaction = {
        "from": agent_name,
        "to": "System",
        "message": f"Refined article:\n{final_article}",
        "timestamp": datetime.datetime.now().isoformat()
    }
    logs.append(interaction)
    litellm_log = {
        "agent_id": agent_id,
        "model": "deepseek/deepseek-chat",
        "messages": messages,
        "response": final_article,
        "timestamp": datetime.datetime.now().isoformat()
    }
    litellm_logs.append(litellm_log)
    logger.info(f"Completed editor_task for agent {agent_id}")
    return final_article, logs, scenario_data, litellm_logs

@app.task
def finalize_article(previous_output, agent_id: str):
    logger.info(f"Starting finalize_article for agent {agent_id}")
    if not previous_output:
        raise ValueError("finalize_article requires previous output")
    edited_article, logs, scenario_data, litellm_logs = previous_output
    system_prompt = scenario_data["system_prompts"][scenario_data["agent_names"][agent_id]]
    agent_name = scenario_data["agent_names"][agent_id]
    llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Finalize this article for publication: {edited_article}"}
    ]
    final_article = llm_client.query(messages)
    interaction = {
        "from": agent_name,
        "to": "System",
        "message": f"Finalized article:\n{final_article}",
        "timestamp": datetime.datetime.now().isoformat()
    }
    logs.append(interaction)
    litellm_log = {
        "agent_id": agent_id,
        "model": "deepseek/deepseek-chat",
        "messages": messages,
        "response": final_article,
        "timestamp": datetime.datetime.now().isoformat()
    }
    litellm_logs.append(litellm_log)
    logger.info(f"Completed finalize_article for agent {agent_id}")
    return final_article, logs, scenario_data, litellm_logs

# Research Tasks
@app.task
def collect_data(previous_output, agent_id: str):
    # Unpack previous output
    plan, logs, scenario_data, litellm_logs = previous_output
    
    # Use plan and scenario_data for data collection
    agent_name = scenario_data["agent_names"][agent_id]
    system_prompt = scenario_data["system_prompts"][agent_name]
    
    # Collect data (e.g., via LLM)
    llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Collect data based on this research plan: {plan}"}
    ]
    data = llm_client.query(messages)
    
    # Update logs and return
    logs.append({"from": agent_name, "message": f"Collected data: {data}", "timestamp": datetime.datetime.now().isoformat()})
    litellm_logs.append({"agent_id": agent_id, "response": data, "timestamp": datetime.datetime.now().isoformat()})
    return data, logs, scenario_data, litellm_logs

@app.task
def analyze_data(previous_output, agent_id: str):
    logger.info(f"Starting analyze_data for agent {agent_id}")
    if not previous_output:
        raise ValueError("analyze_data requires previous output")
    data, logs, scenario_data, litellm_logs = previous_output
    system_prompt = scenario_data["system_prompts"][scenario_data["agent_names"][agent_id]]
    agent_name = scenario_data["agent_names"][agent_id]
    llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analyze this data: {data}"}
    ]
    analysis = llm_client.query(messages)
    interaction = {
        "from": agent_name,
        "to": "System",
        "message": f"Analyzed data:\n{analysis}",
        "timestamp": datetime.datetime.now().isoformat()
    }
    logs.append(interaction)
    litellm_log = {
        "agent_id": agent_id,
        "model": "deepseek/deepseek-chat",
        "messages": messages,
        "response": analysis,
        "timestamp": datetime.datetime.now().isoformat()
    }
    litellm_logs.append(litellm_log)
    logger.info(f"Completed analyze_data for agent {agent_id}")
    return analysis, logs, scenario_data, litellm_logs

@app.task
def generate_statement(*args):
    """Generate a discussion statement, either initial or in response to the previous one."""
    if len(args) == 4 and args[0] is None:
        # Initial call: None, agent_id, task_description, scenario_data
        _, agent_id, task_description, scenario_data = args
        discussion_history = []
        logs = []
        litellm_logs = []
        prompt = f"Discuss the following task in no more than 3 sentences: {task_description}"
    elif len(args) == 2:
        # Subsequent calls: previous_output, agent_id
        previous_output, agent_id = args
        discussion_history, logs, scenario_data, litellm_logs = previous_output
        last_statement = discussion_history[-1]
        prompt = f"Respond to the following statement in no more than 3 sentences: {last_statement}"
    else:
        raise ValueError("Invalid arguments for generate_statement")

    # Generate the statement
    agent_name = scenario_data["agent_names"][agent_id]
    system_prompt = scenario_data["system_prompts"][agent_name]
    llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    response = llm_client.query(messages)
    new_statement = response.strip()
    discussion_history.append(f"{agent_name}: {new_statement}")

    # Log the interaction
    interaction = {
        "from": agent_name,
        "to": "Discussion",
        "message": new_statement,
        "timestamp": datetime.datetime.now().isoformat()
    }
    logs.append(interaction)
    litellm_log = {
        "agent_id": agent_id,
        "model": "deepseek/deepseek-chat",
        "messages": messages,
        "response": new_statement,
        "timestamp": datetime.datetime.now().isoformat()
    }
    litellm_logs.append(litellm_log)

    return discussion_history, logs, scenario_data, litellm_logs

@app.task
def summarize_discussion(previous_output, agent_id: str):
    """Summarize the entire discussion."""
    discussion_history, logs, scenario_data, litellm_logs = previous_output
    agent_name = scenario_data["agent_names"][agent_id]
    system_prompt = scenario_data["system_prompts"][agent_name]
    llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
    discussion_text = "\n".join(discussion_history)
    prompt = f"Summarize the following discussion in a concise manner:\n{discussion_text}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    summary = llm_client.query(messages).strip()

    # Log the summary
    interaction = {
        "from": agent_name,
        "to": "System",
        "message": f"Summary: {summary}",
        "timestamp": datetime.datetime.now().isoformat()
    }
    logs.append(interaction)
    litellm_log = {
        "agent_id": agent_id,
        "model": "deepseek/deepseek-chat",
        "messages": messages,
        "response": summary,
        "timestamp": datetime.datetime.now().isoformat()
    }
    litellm_logs.append(litellm_log)

    return summary, logs, scenario_data, litellm_logs

# Register the new tasks
register_task("generate_statement", "Generate a statement in the discussion", generate_statement)
register_task("summarize_discussion", "Summarize the discussion", summarize_discussion)
# Register all tasks
register_task("plan_research", "Generate an article plan", plan_research)
register_task("create_outline", "Create an article outline", create_outline)
register_task("writer_task", "Draft the article", writer_task)
register_task("editor_task", "Edit and refine the draft", editor_task)
register_task("finalize_article", "Finalize the article", finalize_article)
register_task("collect_data", "Collect research data", collect_data)
register_task("analyze_data", "Analyze collected data", analyze_data)