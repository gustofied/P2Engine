import os

# Global cap on how many consecutive rounds we’ll allow in a single session tick.
MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", 3))
