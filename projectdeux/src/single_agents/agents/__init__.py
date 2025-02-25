# File: multi_agent_system/agents/__init__.py

from .customer_agent import CustomerAgent
from .support_agent import SupportAgent

agent_types = {
    "CustomerAgent": CustomerAgent,
    "SupportAgent": SupportAgent
}