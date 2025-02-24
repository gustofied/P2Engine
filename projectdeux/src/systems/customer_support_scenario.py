#!/usr/bin/env python3
"""
Customer Support Scenario System

This multi-agent system simulates a customer support process. The following agents participate:
  - CustomerAgent: Initiates the support request.
  - SupportAgent: Provides an initial solution.
  - EscalationAgent: Steps in for advanced troubleshooting if needed.
  - ComplianceAgent: Ensures the support process complies with policies.
  - FeedbackAgent: Collects feedback from the customer.
  - Supervisor (CriticAgent): Oversees the conversation and synthesizes the final resolution.

All interactions are logged for full visibility.
"""

import time
import logging
from typing import List
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from custom_logging.central_logger import central_logger
from single_agents.simple_agent import SimpleAgent
from single_agents.critic_agent import CriticAgent

class CustomerSupportSystem:
    def __init__(self, entity_manager: EntityManager, component_manager: ComponentManager):
        self.entity_manager = entity_manager
        self.component_manager = component_manager
        self.logger = logging.getLogger(__name__)
        
        # Create specialized agents with distinct system prompts.
        self.customer = SimpleAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="CustomerAgent",
            system_prompt="You are a customer experiencing a login issue. Describe your problem in detail."
        )
        self.support = SimpleAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="SupportAgent",
            system_prompt="You are a support agent. Provide a clear, concise solution for the customer's login issue."
        )
        self.escalation = SimpleAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="EscalationAgent",
            system_prompt="You are an escalation agent. Provide advanced troubleshooting if the issue persists."
        )
        self.compliance = SimpleAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="ComplianceAgent",
            system_prompt="You are a compliance agent. Ensure the support process follows company policies."
        )
        self.feedback = SimpleAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="FeedbackAgent",
            system_prompt="You are a feedback agent. Ask the customer for feedback on the support experience."
        )
        self.supervisor = CriticAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="Supervisor",
            model="gpt-4"
        )
    
    def run(self) -> str:
        # Log system start.
        problem = "Customer support process for a login issue."
        goal = "Resolve the customer's login issue and gather feedback."
        central_logger.log_system_start("CustomerSupportSystem", self.entity_manager.entities, problem, goal)
        self.logger.info("Customer Support System started.")
        
        # Step 1: Customer initiates the support request.
        customer_message = self.customer.interact("I can't log in to my account. I keep receiving an authentication error.")
        central_logger.log_interaction("CustomerAgent", "System", f"Request: {customer_message}")
        time.sleep(1)
        
        # Step 2: Support agent provides an initial response.
        support_message = self.support.interact(customer_message)
        central_logger.log_interaction("SupportAgent", "CustomerAgent", f"Initial Response: {support_message}")
        time.sleep(1)
        
        # Step 3: Supervisor reviews the exchange and decides if escalation is needed.
        critique = self.supervisor.interact(
            f"Customer said: {customer_message}\nSupport replied: {support_message}\nIs escalation needed? If yes, say 'escalate'."
        )
        central_logger.log_interaction("Supervisor", "System", f"Critique: {critique}")
        time.sleep(1)
        
        if "escalate" in critique.lower():
            escalation_message = self.escalation.interact(customer_message)
            central_logger.log_interaction("EscalationAgent", "CustomerAgent", f"Escalated Response: {escalation_message}")
        else:
            escalation_message = ""
        time.sleep(1)
        
        # Step 4: Compliance agent reviews the process.
        compliance_message = self.compliance.interact(f"Review the support responses: {support_message} {escalation_message}")
        central_logger.log_interaction("ComplianceAgent", "System", f"Compliance Check: {compliance_message}")
        time.sleep(1)
        
        # Step 5: Feedback agent collects customer feedback.
        feedback_message = self.feedback.interact("Please provide feedback on your support experience.")
        central_logger.log_interaction("FeedbackAgent", "CustomerAgent", f"Feedback: {feedback_message}")
        time.sleep(1)
        
        # Step 6: Supervisor synthesizes a final resolution.
        final_resolution = self.supervisor.interact(
            f"Based on the following conversation:\n"
            f"Customer: {customer_message}\n"
            f"Support: {support_message}\n"
            f"Escalation: {escalation_message}\n"
            f"Compliance: {compliance_message}\n"
            f"Feedback: {feedback_message}\n"
            f"Provide a final resolution and next steps."
        )
        central_logger.log_interaction("Supervisor", "System", f"Final Resolution: {final_resolution}")
        
        # Evaluate and log the final resolution.
        evaluation = {"answer_length": len(final_resolution), "success": len(final_resolution) > 50}
        reward = 10 if evaluation["success"] else -5
        central_logger.log_system_end(final_resolution, evaluation, reward)
        central_logger.flush_logs()
        
        return final_resolution

def run_customer_support_scenario():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    # Ensure environment variables are loaded.
    from dotenv import load_dotenv
    load_dotenv()
    
    entity_manager = EntityManager()
    component_manager = ComponentManager()
    
    support_system = CustomerSupportSystem(entity_manager, component_manager)
    result = support_system.run()
    
    print("\n=== FINAL RESOLUTION ===")
    print(result)
    return result

if __name__ == "__main__":
    run_customer_support_scenario()
