#!/usr/bin/env python3
"""
Example script demonstrating how to use the Voice Diary Summarize Day module
with OpenAI Assistants API.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add the parent directory to sys.path to make the module importable
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir.parent.parent.parent))

# Import the module
from voice_diary.agent_summarize_day.agent_summarize_day import summarize_day

def main():
    """Example usage of the summarize_day function."""
    
    # Set your OpenAI API key if not in config
    # os.environ["OPENAI_API_KEY"] = "your-api-key-here"
    
    # Optional: Modify thread settings
    # This example shows how to force creation of a new thread
    modify_thread_settings(force_new_thread=False, retention_days=30)
    
    # Optional: Set a specific date range
    # set_date_range_to_yesterday()
    
    # Run the summarize function
    result = summarize_day()
    
    if result:
        print("Successfully summarized diary entries!")
    else:
        print("Failed to summarize diary entries. Check the logs for details.")

def modify_thread_settings(force_new_thread=False, retention_days=30):
    """
    Optionally modify thread settings before running the summarizer.
    
    Args:
        force_new_thread (bool): If True, clear the thread_id to force creation of a new thread
        retention_days (int): Number of days to keep using the same thread
    """
    config_path = Path(__file__).parent / "summarize_day_config" / "openai_config.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update thread retention setting
        config["openai_config"]["thread_retention_days"] = retention_days
        
        # Force new thread if requested
        if force_new_thread:
            config["openai_config"]["thread_id"] = ""
            config["openai_config"]["thread_created_at"] = ""
            print("Settings modified: Will create a new thread")
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        print(f"Thread retention period set to {retention_days} days")
        
    except Exception as e:
        print(f"Error modifying thread settings: {e}")

def set_date_range_to_yesterday():
    """Set the date range in the config to yesterday."""
    config_path = Path(__file__).parent / "summarize_day_config" / "summarize_day_config.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Set date range to yesterday
        yesterday = datetime.now() - timedelta(days=1)
        date_int = int(yesterday.strftime("%Y%m%d"))
        config["date_range"] = [date_int, date_int]
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        print(f"Date range set to yesterday: {date_int}")
        
    except Exception as e:
        print(f"Error setting date range: {e}")

if __name__ == "__main__":
    main() 