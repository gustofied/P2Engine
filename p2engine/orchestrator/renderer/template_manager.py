from jinja2.sandbox import SandboxedEnvironment


class TemplateManager:
    def __init__(self, env: SandboxedEnvironment):
        self.env = env
        self.cache = {}

    def get_template(self, template_name: str):
        if template_name not in self.cache:
            self.cache[template_name] = self.env.get_template(template_name)
        return self.cache[template_name]
