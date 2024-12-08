from openai import OpenAI
import logging
import json

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Set your OpenAI API key
client = OpenAI(api_key='KEY')

def generate_default_summary(api_response):
    """
    Generate a default summary in case the LLM fails or for specific empty responses.
    """
    if not api_response:
        return "The API returned an empty response."
    
    if isinstance(api_response, dict):
        keys = list(api_response.keys())
        return f"The API returned a response with the following keys: {', '.join(keys)}."
    
    if isinstance(api_response, list):
        if not api_response:
            return "The API returned an empty list."
        return f"The API returned a list containing {len(api_response)} items."
    
    return "The API returned a response, but it could not be summarized effectively."

def summarize_response(user_query, api_response):
    """
    Use OpenAI's LLM to summarize the API response with enhanced debugging and fallback.
    """
    logger.debug(f"Preparing to summarize the response. User query: {user_query}")
    logger.debug(f"API Response: {json.dumps(api_response, indent=2)}")
    
    prompt = (
        f"The user asked: '{user_query}'.\n"
        f"The API responded with: {json.dumps(api_response, indent=2)}\n\n"
        "Provide a concise and clear summary of the response for the user:"
    )
    
    try:
        logger.debug("Sending prompt to OpenAI LLM...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        summary = response.choices[0].message.content.strip()
        if summary:
            logger.debug(f"LLM Summary: {summary}")
            return summary
        else:
            logger.debug("LLM returned an empty summary.")
            return generate_default_summary(api_response)
    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        fallback_summary = generate_default_summary(api_response)
        logger.debug(f"Fallback summary: {fallback_summary}")
        return fallback_summary

def handle_response(user_query, api_response):
    """
    Process the API response: log raw response and generate a robust summary.
    """
    logger.info(f"Raw API response: {json.dumps(api_response, indent=2)}")
    summary = summarize_response(user_query, api_response)
    logger.info(f"Generated summary: {summary}")
    return summary
