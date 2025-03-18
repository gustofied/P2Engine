class StateComponent:
    def __init__(self, state="Idle"):
        self.state = state

class ContextComponent:
    def __init__(self, context=None):
        self.context = context or {}

class ModelComponent:
    def __init__(self, model=None):
        self.model = model or "openrouter/qwen/qwq-32b:free"  # Default model