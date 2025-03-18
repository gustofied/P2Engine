from src.utils.llm_client import LLMClient

client = LLMClient()
response = client.query([{"role": "user", "content": "Hello, how are you?"}])
print(f"LLM Response: {response}")