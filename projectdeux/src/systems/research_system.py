from .base_system import BaseSystem

# In src/systems/research_system.py
class ResearchSystem(BaseSystem):
    def run(self, problem: str = "Research task", **kwargs):
        self.log_start(problem)
        results = {}
        topics = kwargs.get("topics", self.config.get("run_params", {}).get("topics", []))
        
        for topic in topics:
            research_result = self.task_manager.execute_task(
                "compile_report",
                topic=topic,
                problem=problem
            )
            results[topic] = research_result
            print(f"Task 'compile_report' state: {self.get_task_state('compile_report')}")

        final_result_md = f"# Research Results for {problem}\n\n"
        for topic, result in results.items():
            final_result_md += f"## {topic}\n\n{result}\n\n"
        self.log_end(final_result_md, {"success": True}, 10)
        print(f"All task states: {self.list_task_states()}")
        return final_result_md