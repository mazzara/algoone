# utils/config_watcher.py
import os
import json
from src.logger_config import logger

class ConfigWatcher:
    def __init__(self, filepath):
        self.filepath = filepath
        self.last_mtime = 0
        self.config = {}

    def load_if_changed(self):
        try:
            current_mtime = os.path.getmtime(self.filepath)
            if current_mtime != self.last_mtime:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.last_mtime = current_mtime
                    logger.info(f"[ConfigWatcher] Reloaded config: {self.filepath}")
        except Exception as e:
            logger.error(f"[ConfigWatcher] Failed to load config: {e}")
            self.config = {}

    def get(self, key, default=None):
        return self.config.get(key, default)

    def get_param(self, symbol, param, fallback=None):
        self.load_if_changed()  # ensure latest config is always loaded
        return self.config.get(symbol, {}).get(param, self.config.get("defaults", {}).get(param, fallback))
