import numpy as np

def cosine_similarity(vec1, vec2):
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        raise ValueError("Input vectors must not be zero vectors.")
    return np.dot(vec1, vec2) / (norm1 * norm2)

def find_closest_intent_dynamic(user_embedding, embeddings, intents, top_k=1):
    similarities = np.dot(embeddings, user_embedding)
    top_indices = similarities.argsort()[-top_k:][::-1]
    top_scores = similarities[top_indices]
    top_intents = [intents[i] for i in top_indices]

    if len(top_scores) > 1 and abs(top_scores[0] - top_scores[1]) < 0.05:
        return None, "Ambiguous intent. Please clarify your request."
    
    if top_scores[0] > 0.5:
        return top_intents[0], None
    else:
        return None, "No matching intent found."
