import logging

class CentralLogger:
    def __init__(self):
        self.logger = logging.getLogger("CentralLogger")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_interaction(self, source, component, message, run_id):
        self.logger.info(f"[{run_id}] {source}.{component}: {message}")

    def log_error(self, source, message, run_id, context=None):
        context_str = f" Context: {context}" if context else ""
        self.logger.error(f"[{run_id}] {source}: {message}{context_str}")

central_logger = CentralLogger()