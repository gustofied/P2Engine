# Load model for semantic routing
model = SentenceTransformer('all-MiniLM-L6-v2')

# Define agent/tool intents
intents = {
    "x_analysis": model.encode("analyze X posts or trends"),
    "web_search": model.encode("search the web for info"),
    "chat": model.encode("general conversation or questions")
}

# Dummy agents/tools (replace with real ones)
class XAgent:
    def fetch_trends(self, input): return f"Trends for {input}: AI, space"

class WebTool:
    def search(self, query): return f"Web results for {query}"

agents = {"x_analysis": XAgent(), "web_search": WebTool(), "chat": None}

def route_request(user_input):
    # Embed user input
    input_embedding = model.encode(user_input)
    
    # Find best match
    best_score = -1
    best_intent = None
    for intent, embedding in intents.items():
        score = util.cos_sim(input_embedding, embedding).item()
        if score > best_score:
            best_score = score
            best_intent = intent
    
    # Route to agent/tool
    if best_intent == "x_analysis":
        return agents["x_analysis"].fetch_trends(user_input)
    elif best_intent == "web_search":
        return agents["web_search"].search(user_input)
    else:
        return "Let’s chat about that!"

# Test it
print(route_request("What’s trending on X?"))  # "Trends for What’s trending on X?: AI, space"
print(route_request("Search for AI news"))     # "Web results for Search for AI news"