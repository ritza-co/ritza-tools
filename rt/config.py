"""Configuration for rt CLI, loaded from ~/.rt/config.json"""

import json
from pathlib import Path

RT_DIR = Path.home() / '.rt'
CONFIG_FILE = RT_DIR / 'config.json'


def get_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def get_domain():
    """Return the configured Google Workspace domain, or None."""
    return get_config().get('domain') or None
