import os
import json
import datetime
import atexit

SIMPLE_LOG_DATA = {
    "messages": []
}

def log_message(sender: str, receiver: str, text: str):
    log_entry = {
        "from": sender,
        "to": receiver,
        "text": text,
        "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    }
    SIMPLE_LOG_DATA["messages"].append(log_entry)

def flush_simple_logs():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, f"simple_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(log_file, "w") as f:
        json.dump(SIMPLE_LOG_DATA, f, indent=2)
    print(f"Flushed simple logs to {log_file}")

atexit.register(flush_simple_logs)
