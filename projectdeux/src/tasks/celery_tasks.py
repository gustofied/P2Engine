from celery_app import app
from src.integrations.llm.llm_client import LLMClient
import datetime
import os
import logging
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

logger = logging.getLogger(__name__)

# Task Registry: Maps task names to their functions and descriptions
TASK_REGISTRY = {}

# Existing tasks with added logging and error handling
@app.task
def plan_research(agent_id: str, domain: str, scenario_data):
    """Task for generating an article plan."""
    try:
        logger.info(f"Starting plan_research for agent {agent_id}")
        system_prompt = scenario_data["system_prompts"][agent_id]
        agent_name = scenario_data["agent_names"][agent_id]
        llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate a detailed plan for an article about {domain}."}
        ]
        plan = llm_client.query(messages)
        print(f"Plan length: {len(plan)} characters")
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
        logger.debug(f"Plan task: Message length = {len(interaction['message'])} characters")
        logger.info(f"Completed plan_research for agent {agent_id}")
        return plan, [interaction], scenario_data, [litellm_log]
    except Exception as e:
        logger.error(f"Error in plan_research for agent {agent_id}: {e}")
        raise e

@app.task
def create_outline(previous_output, agent_id: str):
    """Task for creating an article outline based on research data."""
    try:
        logger.info(f"Starting create_outline for agent {agent_id}")
        research_data, logs, scenario_data, litellm_logs = previous_output
        system_prompt = scenario_data["system_prompts"][agent_id]
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
    except Exception as e:
        logger.error(f"Error in create_outline for agent {agent_id}: {e}")
        raise e

@app.task
def writer_task(previous_output, agent_id: str):
    """Task for drafting an article based on the plan."""
    try:
        logger.info(f"Starting writer_task for agent {agent_id}")
        plan, logs, scenario_data, litellm_logs = previous_output
        system_prompt = scenario_data["system_prompts"][agent_id]
        agent_name = scenario_data["agent_names"][agent_id]
        llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Write an initial draft based on this plan: {plan}"}
        ]
        draft = llm_client.query(messages)
        print(f"Draft length: {len(draft)} characters")
        interaction = {
            "from": agent_name,
            "to": "System",
            "message": f"Wrote draft:\n{draft}",
            "timestamp": datetime.datetime.now().isoformat()
        }
        logs.append(interaction)
        writer_litellm_log = {
            "agent_id": agent_id,
            "model": "deepseek/deepseek-chat",
            "messages": messages,
            "response": draft,
            "timestamp": datetime.datetime.now().isoformat()
        }
        litellm_logs.append(writer_litellm_log)
        logger.debug(f"Writer task: Message length = {len(interaction['message'])} characters")
        logger.info(f"Completed writer_task for agent {agent_id}")
        return draft, logs, scenario_data, litellm_logs
    except Exception as e:
        logger.error(f"Error in writer_task for agent {agent_id}: {e}")
        raise e

@app.task
def editor_task(previous_output, agent_id: str):
    """Task for refining the draft."""
    try:
        logger.info(f"Starting editor_task for agent {agent_id}")
        draft, logs, scenario_data, litellm_logs = previous_output
        system_prompt = scenario_data["system_prompts"][agent_id]
        agent_name = scenario_data["agent_names"][agent_id]
        llm_client = LLMClient(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"))
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Refine and polish this draft: {draft}"}
        ]
        final_article = llm_client.query(messages)
        print(f"Final article length: {len(final_article)} characters")
        interaction = {
            "from": agent_name,
            "to": "System",
            "message": f"Refined article:\n{final_article}",
            "timestamp": datetime.datetime.now().isoformat()
        }
        logs.append(interaction)
        editor_litellm_log = {
            "agent_id": agent_id,
            "model": "deepseek/deepseek-chat",
            "messages": messages,
            "response": final_article,
            "timestamp": datetime.datetime.now().isoformat()
        }
        litellm_logs.append(editor_litellm_log)
        logger.debug(f"Editor task: Message length = {len(interaction['message'])} characters")
        logger.info(f"Completed editor_task for agent {agent_id}")
        return final_article, logs, scenario_data, litellm_logs
    except Exception as e:
        logger.error(f"Error in editor_task for agent {agent_id}: {e}")
        raise e

@app.task
def finalize_article(previous_output, agent_id: str):
    """Task for finalizing the article with final touches."""
    try:
        logger.info(f"Starting finalize_article for agent {agent_id}")
        edited_article, logs, scenario_data, litellm_logs = previous_output
        system_prompt = scenario_data["system_prompts"][agent_id]
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
    except Exception as e:
        logger.error(f"Error in finalize_article for agent {agent_id}: {e}")
        raise e

# Register all tasks in the TASK_REGISTRY
TASK_REGISTRY["plan_research"] = {
    "description": "Generate an article plan based on the topic",
    "function": plan_research
}
TASK_REGISTRY["create_outline"] = {
    "description": "Create an article outline based on research",
    "function": create_outline
}
TASK_REGISTRY["writer_task"] = {
    "description": "Draft the article based on the outline",
    "function": writer_task
}
TASK_REGISTRY["editor_task"] = {
    "description": "Edit and refine the draft article",
    "function": editor_task
}
TASK_REGISTRY["finalize_article"] = {
    "description": "Finalize the article with final touches",
    "function": finalize_article
}

# Placeholder tasks (unchanged)
@app.task
def scrape_task(url: str, target: str = "p", scenario_data=None):
    """Placeholder task for scraping a URL."""
    return f"Scraped {url} with target {target}"

@app.task
def summarize_task(text: str, scenario_data=None):
    """Placeholder task for summarizing text."""
    return f"Summarized text: {text[:50]}..."