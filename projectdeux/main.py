# File: multi_agent_system/main.py

from src.systems.configurable_system import ConfigurableSystem

if __name__ == "__main__":
    config_path = "configs/customer_support.json"
    system = ConfigurableSystem(config_path)
    system.run()