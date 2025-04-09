#!/usr/bin/env python
import json
import os
import glob
import re
from pathlib import Path
from collections import defaultdict


def find_config_files():
    """Find all JSON config files in the project."""
    base_dir = Path(__file__).resolve().parent.parent.parent  # voice_diary directory
    config_files = []
    
    # New dedicated config directory
    project_modules_configs_dir = base_dir / "voice_diary" / "project_modules_configs"
    
    # Search patterns for config files
    patterns = [
        str(project_modules_configs_dir / "**" / "*.json"),
        "**/config/**/*.json",
        "**/*config*.json",
    ]
    
    for pattern in patterns:
        if pattern.startswith(str(project_modules_configs_dir)):
            # Use Path.glob for absolute paths
            config_files.extend(list(Path(pattern[:pattern.index("**")]).glob(pattern[pattern.index("**"):])))
        else:
            # Use base_dir.glob for relative patterns
            config_files.extend(list(base_dir.glob(pattern)))
    
    # Remove duplicates
    return list(set(config_files))


def is_valid_file_path(value, key=""):
    """Check if a string is likely to be a file path and not an API endpoint, database URL, or date."""
    if not isinstance(value, str):
        return False
    
    # Skip specific keys
    if key.endswith('.message') or key == 'message' or key.endswith('.email.message'):
        return False
    
    # Path must contain separators
    if '/' not in value and '\\' not in value:
        return False
    
    # Skip API endpoints
    if value.startswith(('http://', 'https://', 'ftp://')):
        return False
    
    # Skip database connection strings
    if re.search(r'(postgres|mysql|sqlite|mongodb|jdbc|odbc):', value, re.IGNORECASE):
        return False
    
    # Skip dates or timestamps
    if re.match(r'\d{4}-\d{2}-\d{2}T', value):
        return False
    
    # Skip long text/email content
    if len(value) > 100 and '\n' in value:
        return False
    
    # Must contain a directory or filename pattern
    file_path_pattern = re.compile(r'([A-Za-z]:\\|/|\\\\|\.\.?/).*\.(json|txt|py|log|csv|[a-z]{2,4})$', re.IGNORECASE)
    directory_pattern = re.compile(r'([A-Za-z]:\\|/|\\\\|\.\.?/).*(/|\\)$', re.IGNORECASE)
    
    # Check if it looks like a file or directory path
    if file_path_pattern.search(value) or directory_pattern.search(value) or ':\\' in value:
        return True
    
    # For paths that don't have extensions but have a proper structure
    if ('/' in value or '\\' in value) and not value.startswith(('http', 'ftp', 'ws:')):
        parts = re.split(r'[/\\]', value)
        # Valid paths should have reasonable component lengths
        if len(parts) >= 2 and all(1 <= len(part) <= 64 for part in parts if part):
            return True
    
    return False


def extract_path_fields(config_data, parent_key="", path_fields=None):
    """Recursively extract all path fields from config data."""
    if path_fields is None:
        path_fields = {}
    
    if isinstance(config_data, dict):
        for key, value in config_data.items():
            current_key = f"{parent_key}.{key}" if parent_key else key
            
            # Check if value is a likely file or directory path
            if is_valid_file_path(value, current_key):
                path_fields[current_key] = value
            
            # Recursively process dictionaries
            if isinstance(value, (dict, list)):
                extract_path_fields(value, current_key, path_fields)
    
    elif isinstance(config_data, list):
        for i, item in enumerate(config_data):
            current_key = f"{parent_key}[{i}]"
            if isinstance(item, (dict, list)):
                extract_path_fields(item, current_key, path_fields)
    
    return path_fields


def update_config_value(config_data, key_path, new_value):
    """Update a specific value in nested config data."""
    if "." not in key_path and "[" not in key_path:
        config_data[key_path] = new_value
        return
    
    # Handle array notation like "key[0]"
    if "[" in key_path:
        key_parts = key_path.split("[", 1)
        main_key = key_parts[0]
        index_part = key_parts[1].split("]")[0]
        
        # Convert to zero-based index
        try:
            index = int(index_part)
            remaining_path = key_path.split("]", 1)[1].lstrip(".")
            
            if not remaining_path:
                config_data[main_key][index] = new_value
            else:
                update_config_value(config_data[main_key][index], remaining_path, new_value)
        except (ValueError, IndexError):
            print(f"Error: Invalid index in key path: {key_path}")
        return
    
    # Handle dot notation like "key1.key2.key3"
    key_parts = key_path.split(".", 1)
    if len(key_parts) == 1:
        config_data[key_parts[0]] = new_value
    else:
        main_key, remaining_path = key_parts
        if main_key in config_data:
            if isinstance(config_data[main_key], dict):
                update_config_value(config_data[main_key], remaining_path, new_value)
        else:
            print(f"Error: Key not found: {main_key}")


# Add colored terminal output support
def colorize(text, color_code):
    """Add color to terminal output."""
    # Only use colors if we're not in a CI environment and terminal supports it
    if os.isatty(1):  # Check if stdout is a terminal
        return f"\033[{color_code}m{text}\033[0m"
    return text


def normalize_path(path):
    """Normalize path for display and checking existence."""
    # Convert to forward slashes for display consistency
    normalized = path.replace("\\", "/")
    return normalized


def get_module_name(config_file):
    """Extract module name from config file path."""
    path_parts = config_file.parts
    
    # Extract from the new config directory structure
    if 'project_modules_configs' in path_parts:
        config_dir_index = path_parts.index('project_modules_configs')
        # Check if the directory starts with 'config_' followed by the module name
        if len(path_parts) > config_dir_index + 1:
            module_dir = path_parts[config_dir_index + 1]
            if module_dir.startswith('config_'):
                return module_dir[7:]  # Remove 'config_' prefix
            return module_dir
    
    # Legacy method: Find 'voice_diary' in the path
    if 'voice_diary' in path_parts:
        voice_diary_index = path_parts.index('voice_diary')
        # Get the next part after voice_diary as the module name
        if len(path_parts) > voice_diary_index + 1:
            return path_parts[voice_diary_index + 1]
    
    # Fallback: use the parent directory name
    return config_file.parent.name


def truncate_path(path, max_length=80):
    """Truncate path for display if it's too long."""
    if len(path) <= max_length:
        return path
    
    # Keep the first part of the path
    first_part = path[:40]
    
    # Keep the last part of the path
    last_part = path[-(max_length - 43):]
    
    return f"{first_part}...{last_part}"


def get_ordered_modules(module_configs):
    """Return modules in the specified processing order."""
    # Define the order of modules based on the workflow
    module_order = [
        "dwnload_files",     # 1. Download from Gmail
        "transcribe_raw_audio", # 2. Transcribe
        "file_utils",        # 3. Move to target paths
        "agent_summarize_day", # 4. Summarize
        "send_email",        # 5. Send email
        # Any remaining modules will be appended at the end
    ]
    
    # First add modules in the defined order
    ordered_modules = []
    for module in module_order:
        if module.lower() in module_configs:
            ordered_modules.append(module.lower())
    
    # Then add any remaining modules alphabetically
    for module in sorted(module_configs.keys()):
        if module.lower() not in ordered_modules:
            ordered_modules.append(module.lower())
    
    return ordered_modules


def summarize_configurations():
    """Generate a summary of all config paths grouped by module."""
    config_files = find_config_files()
    
    # Skip test configuration files
    config_files = [file for file in config_files if "test" not in str(file).lower()]
    
    if not config_files:
        print(colorize("No configuration files found.", "31"))  # Red
        return None
    
    # Group configs by module
    module_configs = defaultdict(list)
    all_paths = []
    path_exists_count = 0
    path_not_found_count = 0
    
    for config_file in config_files:
        try:
            module_name = get_module_name(config_file)
            
            # Get relative path in a way that works for both old and new structures
            try:
                relative_path = config_file.relative_to(config_file.parent.parent.parent.parent)
            except ValueError:
                # For the new config structure
                base_dir = Path(__file__).resolve().parent.parent.parent
                relative_path = config_file.relative_to(base_dir)
            
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            path_fields = extract_path_fields(config_data)
            
            if path_fields:
                module_configs[module_name.lower()].append({
                    'file': str(relative_path),
                    'paths': path_fields
                })
                
                for path in path_fields.values():
                    all_paths.append(path)
                    # Check if path exists
                    display_path = normalize_path(path)
                    exists = os.path.exists(path) or os.path.exists(Path(display_path))
                    if exists:
                        path_exists_count += 1
                    else:
                        path_not_found_count += 1
        except Exception as e:
            print(colorize(f"Error processing {config_file}: {e}", "31"))  # Red
    
    # Print summary
    print(colorize("\n===== CONFIGURATION PATHS SUMMARY =====", "1;36"))  # Bold Cyan
    print(colorize(f"Found {len(config_files)} configuration files with {len(all_paths)} path settings", "1;37"))
    print(colorize(f"Paths status: {path_exists_count} exist, {path_not_found_count} not found", "1;37"))
    
    # Get modules in defined order
    ordered_modules = get_ordered_modules(module_configs)
    
    # Create summary sections by module in the defined order
    for module_name in ordered_modules:
        configs = module_configs[module_name]
        print(colorize(f"\n[{module_name.upper()}]", "1;33"))  # Bold Yellow
        
        for config in configs:
            print(colorize(f"  {config['file']}", "1;36"))  # Bold Cyan
            
            for key, path in config['paths'].items():
                # Check if path exists
                display_path = normalize_path(path)
                display_path = truncate_path(display_path, 80)
                
                exists = os.path.exists(path) or os.path.exists(Path(normalize_path(path)))
                existence_marker = colorize("[✓]", "32") if exists else colorize("[✗]", "31")
                
                print(f"    {colorize(key, '36')}: {display_path} {existence_marker}")
    
    print(colorize("\n===== END OF SUMMARY =====\n", "1;36"))  # Bold Cyan
    
    return module_configs


def confirm_and_update_paths():
    """Find all config files, confirm paths with user, and update if needed."""
    # First, generate and display the summary
    module_configs = summarize_configurations()
    
    # Ask user if they want to proceed with updates
    proceed = input(colorize("Do you want to proceed with updating paths? [Y/n]: ", "1;33")).strip().lower()
    if proceed and proceed.startswith("n"):
        print(colorize("Update cancelled by user.", "33"))
        return
    
    config_files = find_config_files()
    
    # Skip test configuration files
    config_files = [file for file in config_files if "test" not in str(file).lower()]
    
    if not config_files:
        return  # Already showed message in summary
    
    total_changes = 0
    
    # Group configs by module for ordered processing
    file_modules = {}
    for config_file in config_files:
        module_name = get_module_name(config_file).lower()
        file_modules[config_file] = module_name
    
    # Get modules in defined order
    module_order = []
    for module in ["dwnload_files", "transcribe_raw_audio", "file_utils", "agent_summarize_day", "send_email"]:
        for config_file, module_name in file_modules.items():
            if module_name == module:
                module_order.append(config_file)
    
    # Add any remaining files
    ordered_files = module_order.copy()
    for config_file in config_files:
        if config_file not in ordered_files:
            ordered_files.append(config_file)
    
    # Process files in the defined order
    for config_file in ordered_files:
        # Get relative path in a way that works for both old and new structures
        try:
            rel_path = config_file.relative_to(config_file.parent.parent.parent.parent)
        except ValueError:
            # For the new config structure
            base_dir = Path(__file__).resolve().parent.parent.parent
            rel_path = config_file.relative_to(base_dir)
            
        print(f"\n{colorize('Checking', '34')} {colorize(str(rel_path), '36')}...")  # Blue, Cyan
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            path_fields = extract_path_fields(config_data)
            changes_made = False
            
            if not path_fields:
                print(colorize("  No path fields found in this config file.", "33"))  # Yellow
                continue
            
            for key, path in path_fields.items():
                # Normalize path for display and checking
                display_path = normalize_path(path)
                display_path = truncate_path(display_path, 80)
                
                # Check if path exists (try both normalized and original)
                exists = os.path.exists(path) or os.path.exists(Path(normalize_path(path)))
                existence_marker = colorize(" [EXISTS]", "32") if exists else colorize(" [NOT FOUND]", "31")
                
                prompt = f"  Path for {colorize(key, '36')} is:\n  {colorize(display_path, '37')}{existence_marker}\n  Is this correct? [Y/n]: "
                response = input(prompt).strip().lower()
                
                if response == "" or response.startswith("y"):
                    # User confirms the path is correct
                    continue
                
                # Get new path from user
                new_path = input(f"  Enter new path [{display_path}]: ").strip()
                if not new_path:
                    # User didn't enter anything, keep existing path
                    continue
                    
                # Normalize the new path for consistency
                new_path = normalize_path(new_path)
                
                # Update the path in the config data
                update_config_value(config_data, key, new_path)
                changes_made = True
                total_changes += 1
                print(colorize(f"  Updated path for '{key}'", "32"))  # Green
            
            if changes_made:
                # Save the updated config file with pretty formatting
                with open(config_file, 'w') as f:
                    json.dump(config_data, f, indent=2)
                print(colorize(f"  Updated {config_file}", "32"))  # Green
        
        except Exception as e:
            print(colorize(f"  Error processing {config_file}: {e}", "31"))  # Red
    
    if total_changes > 0:
        print(f"\n{colorize(f'Path confirmation complete. Updated {total_changes} paths.', '32')}")  # Green
    else:
        print(f"\n{colorize('Path confirmation complete. No changes were made.', '32')}")  # Green


if __name__ == "__main__":
    confirm_and_update_paths()
