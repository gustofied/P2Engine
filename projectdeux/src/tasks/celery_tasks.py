# celery_tasks.py
from src.tasks.task_registry import (
    plan_research, create_outline, writer_task, editor_task, finalize_article,
    collect_data, analyze_data, TASK_REGISTRY
)

# No need to redefine tasks here; import them from task_registry.py
# Optionally, keep placeholder tasks if they’re unique
from celery_app import app

@app.task
def scrape_task(url: str, target: str = "p", scenario_data=None):
    """Placeholder task for scraping a URL."""
    return f"Scraped {url} with target {target}"

@app.task
def summarize_task(text: str, scenario_data=None):
    """Placeholder task for summarizing text."""
    return f"Summarized text: {text[:50]}..."