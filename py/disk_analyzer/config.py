"""Configuration management for disk analyzer."""

import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


DEFAULT_CONFIG = {
    'alert': {
        'warning_threshold': 80.0,
        'critical_threshold': 90.0
    },
    'filter': {
        'exclude_fstypes': ['tmpfs', 'proc', 'devtmpfs', 'sysfs'],
        'exclude_dirs': [],
        'min_size': 0
    },
    'output': {
        'format': 'table',
        'color': True
    },
    'scheduler': {
        'interval': 3600
    }
}


class Config:
    """Configuration manager."""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        self.config = DEFAULT_CONFIG.copy()
        if config_dict:
            self._merge(config_dict)
    
    def _merge(self, overrides: Dict[str, Any]):
        """Merge overrides into config."""
        for key, value in overrides.items():
            if key in self.config and isinstance(self.config[key], dict) and isinstance(value, dict):
                self.config[key].update(value)
            else:
                self.config[key] = value
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """Set a config value."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'Config':
        """Load config from JSON file."""
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return cls()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            logger.info(f"Config loaded from: {config_path}")
            return cls(config_dict)
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return cls()
    
    def save_to_file(self, config_path: str):
        """Save config to JSON file."""
        try:
            os.makedirs(os.path.dirname(config_path) if os.path.dirname(config_path) else '.', exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Config saved to: {config_path}")
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")
    
    def apply_to_args(self, args):
        """Apply config to argparse args (config values as defaults)."""
        if not hasattr(args, 'threshold') or args.threshold is None:
            args.threshold = self.get('alert', 'warning_threshold', 80.0)
        
        if not hasattr(args, 'format') or args.format is None:
            args.format = self.get('output', 'format', 'table')
        
        if not hasattr(args, 'no_color'):
            args.no_color = not self.get('output', 'color', True)
        
        return args
