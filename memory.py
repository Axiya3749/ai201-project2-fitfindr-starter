"""
memory.py
Saves and loads user style preferences between sessions.
"""

import json
import os

MEMORY_FILE = "style_memory.json"


def save_style_profile(wardrobe: dict, last_query: str):
    """Save the user's wardrobe and last query to disk."""
    memory = {
        "wardrobe": wardrobe,
        "last_query": last_query,
    }
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f)


def load_style_profile() -> dict | None:
    """Load saved style profile from disk. Returns None if no profile exists."""
    if not os.path.exists(MEMORY_FILE):
        return None
    with open(MEMORY_FILE) as f:
        return json.load(f)


def clear_style_profile():
    """Delete the saved style profile."""
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)