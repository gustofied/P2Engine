import json
import pickle

def load_utterances(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def save_embeddings(embeddings, file_path):
    with open(file_path, 'wb') as f:
        pickle.dump(embeddings, f)

def load_embeddings(file_path):
    with open(file_path, 'rb') as f:
        return pickle.load(f)
