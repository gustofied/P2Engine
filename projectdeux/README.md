## Adam Dybwad Sioud

cd /path/to/projectdeux
export PYTHONPATH=$(pwd)/src

### Scenario Configuration

- **Supervisor-Driven Scenario**: Define only a `SupervisorAgent`. It will decide agents and sequence.
  Example: `collaborative_writing.yaml`
- **User-Defined Scenario**: List all agents with `name`, `role`, `task`, `queue`, `system_prompt`, and a `task_sequence`.
  Example: `user_defined_writing.yaml`

python main.py --scenarios src/scenarios --scenario "collaborative_writing"

#TODO LÆR DEG CELERY BUILD SÅ ALLE WORKERS KAN BLI HØRT PÅ

celery -A celery_app worker --loglevel=info
