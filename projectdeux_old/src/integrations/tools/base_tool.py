from abc import ABC, abstractmethod

class Tool(ABC):
    @abstractmethod
    def execute(self, **kwargs):
        """Execute the tool's functionality."""
        pass

    @property
    def name(self):
        """Return the name of the tool."""
        return self.__class__.__name__