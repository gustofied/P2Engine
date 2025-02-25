# main.py
from systems.scenario_loader import load_system

# Load the system with the configuration
system = load_system("adaptive_scenario", "src/systems/adaptive_scenario/scenarios/scenario1.json")

# Run the system with a problem and question
result = system.run(
    problem="Team problem-solving",
    question="How can teams leverage both analytical reasoning and creative spontaneity to solve complex problems?"
)

# Print the result
print(f"Final result: {result}")