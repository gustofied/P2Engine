from tasks.task import Task
from .base_system import BaseSystem

class WebScrapingSystem(BaseSystem):
    def run(self, problem: str = "Web scraping task", **kwargs):
        self.log_start(problem)
        results = {}

        # Get run parameters from kwargs or config
        run_params = self.config.get("run_params", {})
        urls = kwargs.get("urls", run_params.get("urls", []))
        target = kwargs.get("target", run_params.get("target", "p"))
        goal = kwargs.get("goal", run_params.get("goal", "Summarize the content"))

        if isinstance(urls, str):
            urls = [urls]

        for url in urls:
            try:
                # Execute the "analyze" task, which depends on "scrape"
                analysis_result = self.task_manager.execute_task(
                    "analyze",
                    url=url,
                    target=target,
                    goal=goal,
                    problem=problem
                )
                results[url] = analysis_result
            except KeyError as ke:
                results[url] = f"KeyError processing {url}: missing key {str(ke)}"
            except ValueError as ve:
                results[url] = f"ValueError processing {url}: {str(ve)}"
            except Exception as e:
                results[url] = f"Unexpected error processing {url}: {str(e)}"

        # Format the result in Markdown
        final_result_md = f"# Scraping Results for {problem}\n\n"
        for url, result in results.items():
            final_result_md += f"## {url}\n\n{result}\n\n"
        self.log_end(final_result_md, {"success": True}, 10)
        return final_result_md