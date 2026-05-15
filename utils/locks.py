"""
Shared lock objects for thread-safe config file access.

Both ConfigManager and PathsConfig use these locks to prevent race conditions
when accessing the same configuration files.
"""

import threading

# Shared lock for gui_config.json access across all config modules
config_lock = threading.RLock()