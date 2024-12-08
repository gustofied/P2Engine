import os
import json
import pickle
from embedding_generator import generate_embeddings_batch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '../data/utterances.json')
EMBEDDINGS_PATH = os.path.join(BASE_DIR, '../embeddings/intent_embeddings.pkl')

def main():
    with open(DATA_PATH, 'r') as f:
        utterances = json.load(f)
    
    intent_embeddings = {}
    for intent, utterance_examples in utterances.items():
        embeddings = generate_embeddings_batch(utterance_examples)
        intent_embeddings[intent] = embeddings
    
    with open(EMBEDDINGS_PATH, 'wb') as f:
        pickle.dump(intent_embeddings, f)

if __name__ == '__main__':
    main()
