import pytest
import os

@pytest.fixture
def config_path():
    path = os.path.join(os.path.dirname(__file__), "../src/config/scenario.yaml")
    if not os.path.exists(path):
        pytest.fail(f"Config file not found at: {path}. Please create 'scenario.yaml' in src/config/.")
    return path