import argparse
import os
import json
import numpy as np
from datetime import datetime
from modules.data_handler import load_utterances, load_embeddings
from modules.embedding_generator import generate_embeddings_batch
from modules.similarity_search import find_closest_intent_dynamic
from modules.fallback_handler import handle_fallback
from modules.response_processor import handle_response

def flatten_embeddings(intent_embeddings):
    """Flatten the embeddings and extract intents."""
    embeddings = []
    intents = []
    for intent, emb_list in intent_embeddings.items():
        for emb in emb_list:
            embeddings.append(emb)
            intents.append(intent)
    return np.array(embeddings), intents

import poc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'utterances.json')
EMBEDDINGS_PATH = os.path.join(BASE_DIR, 'embeddings', 'intent_embeddings.pkl')
LOG_FILE = os.path.join(BASE_DIR, 'output.log')


def log_to_file(message):
    """Appends the message to the log file with a timestamp."""
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")


def log_intent_and_response(intent, raw_response, summary):
    """Log the intent, raw response, and summarized response."""
    log_message = f"\nIntent: {intent}\n"
    log_message += f"Raw Response: {json.dumps(raw_response, indent=2)}\n"
    log_message += f"Summary: {summary}\n"
    log_to_file(log_message)


def main():
    parser = argparse.ArgumentParser(description='Semantic Router for DAML POC')
    parser.add_argument('-i', '--intent', required=True, help='User intent phrase (use quotes for multi-word intents)')
    args = parser.parse_args()

    log_to_file(f"User Intent: {args.intent}")

    try:
        utterances = load_utterances(DATA_PATH)
        intent_embeddings = load_embeddings(EMBEDDINGS_PATH)
    except FileNotFoundError:
        error_message = f"Error: Required files {DATA_PATH} or {EMBEDDINGS_PATH} are missing."
        print(error_message)
        log_to_file(error_message)
        return
    except Exception as e:
        error_message = f"Error loading data: {e}"
        print(error_message)
        log_to_file(error_message)
        return

    embeddings, intents = flatten_embeddings(intent_embeddings)

    try:
        user_embedding = generate_embeddings_batch([args.intent])[0]
    except Exception as e:
        error_message = f"Error generating embedding for intent: {e}"
        print(error_message)
        log_to_file(error_message)
        return

    closest_intent, fallback_message = find_closest_intent_dynamic(user_embedding, embeddings, intents)

    if closest_intent:
        if closest_intent == 'allocate_party':
            print("Allocating a new party...")
            raw_response = poc.allocate_new_party(poc.alice_party_id, 'Charlie')
        elif closest_intent == 'list_parties':
            print("Listing known parties...")
            raw_response = poc.list_known_parties(poc.alice_party_id)
        elif closest_intent == 'list_packages':
            print("Listing known packages...")
            raw_response = poc.list_known_packages()
        else:
            print(f"No handling for intent '{closest_intent}'")
            raw_response = {"status": 400, "data": {"error": f"Unhandled intent: {closest_intent}"}}

        summary = handle_response(args.intent, raw_response)
        log_intent_and_response(closest_intent, raw_response, summary)
        print("\nSummary:", summary)
    else:
        suggested_intents = ['allocate_party', 'list_parties', 'list_packages']
        chosen_intent = handle_fallback(args.intent, suggested_intents)

        if chosen_intent == 'allocate_party':
            raw_response = poc.allocate_new_party(poc.alice_party_id, 'Charlie')
        elif chosen_intent == 'list_parties':
            raw_response = poc.list_known_parties(poc.alice_party_id)
        elif chosen_intent == 'list_packages':
            raw_response = poc.list_known_packages()
        else:
            raw_response = {"status": 400, "data": {"error": "Could not process your request."}}

        summary = handle_response(args.intent, raw_response)
        log_intent_and_response(chosen_intent, raw_response, summary)
        print("\nSummary:", summary)


if __name__ == '__main__':
    main()
