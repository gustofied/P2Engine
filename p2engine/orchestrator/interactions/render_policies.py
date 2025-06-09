from typing import Dict, List

RENDER_POLICIES = {}


def register_policy(name):
    def decorator(func):
        RENDER_POLICIES[name] = func
        return func

    return decorator


@register_policy("default")
def default_policy(messages: List[Dict], **kwargs) -> List[Dict]:
    return messages
