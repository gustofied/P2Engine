from abc import ABC, abstractmethod


class BaseAgent(ABC):
    @abstractmethod
    def interact(self, user_input: str) -> str:
        """
        Process the user input and return a response.
        """
        pass
