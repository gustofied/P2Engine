from litellm import completion
import os

os.environ['DEEPSEEK_API_KEY'] = "sk-f26417624f2c412eb45e804295e20c6a"
response = completion(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "hello from litellm"}],
)
print(response)
