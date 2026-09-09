"""
Custom Commands Manager
=======================
Load, save, and manage user-defined custom voice commands.
Persists to config.json.
"""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def _load_config() -> dict:
    """Load the full config from config.json."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"intents": {}, "custom_commands": {}}


def _save_config(config: dict):
    """Save the full config to config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def add_custom_command(trigger: str, response: str, action: str = "response") -> bool:
    """
    Add a new custom command.
    
    Args:
        trigger: The trigger phrase
        response: The response text
        action: Optional action type
        
    Returns:
        bool: True if saved successfully
    """
    try:
        config = _load_config()
        if "custom_commands" not in config:
            config["custom_commands"] = {}
        config["custom_commands"][trigger.lower().strip()] = response
        _save_config(config)
        return True
    except Exception as e:
        print(f"Error saving custom command: {e}")
        return False


def remove_custom_command(trigger: str) -> bool:
    """
    Remove a custom command.
    
    Args:
        trigger: The trigger phrase to remove
        
    Returns:
        bool: True if removed successfully
    """
    try:
        config = _load_config()
        commands = config.get("custom_commands", {})
        trigger_lower = trigger.lower().strip()
        if trigger_lower in commands:
            del commands[trigger_lower]
            config["custom_commands"] = commands
            _save_config(config)
            return True
        return False
    except Exception as e:
        print(f"Error removing custom command: {e}")
        return False


def get_custom_commands() -> dict:
    """
    Get all custom commands.
    
    Returns:
        dict: Mapping of trigger phrases to responses
    """
    config = _load_config()
    return config.get("custom_commands", {})


def update_custom_command(trigger: str, new_response: str) -> bool:
    """
    Update an existing custom command's response.
    
    Args:
        trigger: The trigger phrase
        new_response: The new response text
        
    Returns:
        bool: True if updated successfully
    """
    config = _load_config()
    commands = config.get("custom_commands", {})
    trigger_lower = trigger.lower().strip()
    if trigger_lower in commands:
        commands[trigger_lower] = new_response
        config["custom_commands"] = commands
        _save_config(config)
        return True
    return False
