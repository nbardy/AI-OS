# Shader Judge Macro Path Handling Fix Summary

## Problem Statement

The shader_judge_macro.py is failing due to path handling issues when run through AI-OS. The macro cannot find the correct project files and applies patches to the wrong directory.

## Root Causes Identified

### 1. AI-OS Working Directory Change
- AI-OS changes the working directory to the macro's location (`/Users/nicholasbardy/git/shader_experiments/macros/`) before running it
- The macro was written assuming it would be run from the project root

### 2. Duplicate Project Structure
- There are duplicate Rust project files in the macros directory:
  - `/Users/nicholasbardy/git/shader_experiments/macros/Cargo.toml`
  - `/Users/nicholasbardy/git/shader_experiments/macros/src/main.rs`
  - `/Users/nicholasbardy/git/shader_experiments/macros/src/shader.wgsl`
- These appear to be from patches that were incorrectly applied to the macros directory instead of the project root

### 3. Path Resolution Logic
- The macro uses `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` to find project root
- This fails when AI-OS changes the working directory
- File paths for prompts are constructed incorrectly

## Required Fixes

### 1. Clean Up Duplicate Files
Remove the duplicate Rust project structure from the macros directory:
```bash
rm /Users/nicholasbardy/git/shader_experiments/macros/Cargo.toml
rm -rf /Users/nicholasbardy/git/shader_experiments/macros/src/
```

### 2. Fix Path Resolution in Macro
Update the macro to handle AI-OS's working directory change:

```python
# At the start of main():
# Save the current working directory (which AI-OS sets to the macro's directory)
macro_dir = os.getcwd()

# The actual project root is the parent of the macros directory
project_root = os.path.abspath(os.path.join(macro_dir, '..'))

# Change to project root for all operations
os.chdir(project_root)

# Now all relative paths work correctly
goal_prompt_path = raw_goal_prompt_path  # No need to join with project_root
vllm_judge_prompt_path = raw_vllm_judge_prompt_path
```

### 3. Fix Patch Context
Ensure patches are generated with the correct understanding of the project structure:

```python
# When generating patch context, make sure we're in the project root
project_files = get_all_project_files('.')  # Use current directory (project root)

# In patch prompts, clarify the working directory
patch_instruction_prompt = f"""
The current working directory is the project root: {os.getcwd()}
All file paths in your patch should be relative to this directory.
..."""
```

### 4. Simplify Cargo Commands
Since we're already in the project root:

```python
# Simple cargo run without cd
command = "timeout 30 cargo run"
```

## Implementation Checklist for Engineering Agent

1. [ ] Remove duplicate Cargo.toml and src/ directory from macros/
2. [ ] Update path resolution to use os.getcwd() and handle AI-OS's directory change
3. [ ] Change to project root early in the macro execution
4. [ ] Update all file path constructions to work from project root
5. [ ] Fix patch generation context to use correct paths
6. [ ] Test the macro with the fixed paths
7. [ ] Ensure patches are applied to the correct locations

## Expected Behavior After Fix

1. Macro correctly identifies project root regardless of how it's invoked
2. Prompt files are found and read successfully
3. Cargo commands run in the correct directory
4. Patches are applied to the actual project files, not duplicates
5. The macro works consistently through AI-OS

## Key Insight

The fundamental issue is that the macro was written for direct execution but is being run through AI-OS which changes the working directory. The fix is to explicitly handle this directory change and ensure all paths are resolved relative to the actual project root, not the macro's location.