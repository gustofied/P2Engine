# File: multi_agent_system/systems/customer_support_system.py

from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from custom_logging.central_logger import central_logger

class CustomerSupportSystem:
    def __init__(self, agents, entity_manager: EntityManager, component_manager: ComponentManager):
        self.agents = agents
        self.entity_manager = entity_manager
        self.component_manager = component_manager

    def run(self, initial_message=""):
        responses = []
        customer = next(agent for agent in self.agents if "Customer" in agent.name)
        support = next(agent for agent in self.agents if "Support" in agent.name)
        
        customer_response = customer.interact(initial_message)
        central_logger.log_interaction(customer.name, "Support", f"Customer says: {customer_response}")
        responses.append(f"Customer: {customer_response}")
        
        support_response = support.interact(customer_response)
        central_logger.log_interaction(support.name, "Customer", f"Support says: {support_response}")
        responses.append(f"Support: {support_response}")
        
        return "\n".join(responses)