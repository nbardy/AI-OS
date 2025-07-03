# Path Handling Analysis for AI-OS and shader_judge_macro

## Executive Summary

After thoroughly exploring the AI-OS codebase and the shader_judge_macro, I've identified key path handling patterns and issues that need to be addressed.

## Key Findings

### 1. Macro Runner Path Handling (AI-OS)

In `/Users/nicholasbardy/git/AI-OS/ai_os/core/macro_runner.py`:

- **Line 39**: `module_path = Path(module_path_str).resolve()` - Resolves macro path relative to CWD
- **Line 227**: Stores original CWD before execution
- **Line 236**: Changes to macro's parent directory: `os.chdir(macro_path_resolved.parent)`
- **Line 238**: Imports macro using only filename after changing directory
- **Line 298**: Restores original CWD after execution

**Key Pattern**: AI-OS changes the working directory to the macro's location during execution, allowing macros to use relative paths for their resources.

### 2. shader_judge_macro Path Issues

In `/Users/nicholasbardy/git/shader_experiments/macros/shader_judge_macro.py`:

**Current Path Handling:**
- **Line 75-76**: Infers project root by going one level up from macro location
- **Lines 87-88**: Constructs full paths for prompt files relative to project root
- **Lines 116-118**: Hardcodes paths for shader files and output image
- **Line 128**: Uses `cd` command in shell to change directory before running cargo

**Problems Identified:**
1. The macro assumes it's in a `macros/` subdirectory and goes one level up
2. When AI-OS changes CWD to the macro's directory, relative paths break
3. The project has an unusual structure with a Cargo.toml inside the macros directory
4. Path construction doesn't account for AI-OS's CWD change

### 3. Patch Application Path Handling

In `/Users/nicholasbardy/git/AI-OS/ai_os/core/patch.py`:

- **Line 82**: `p = Path(file_path_str)` - Uses paths as provided by the patch
- **Line 91**: Creates parent directories as needed
- No path resolution or normalization is performed

**Key Pattern**: Patches expect file paths relative to the current working directory at the time of application.

### 4. Other Macro Examples

**chart_judge_macro.py** (AI-OS example):
- Doesn't use file paths, works entirely in memory
- No path handling issues

**tdd_macro.py** (AI-OS example):
- **Line 88**: `test_command = f"pytest {test_file.path}"`
- Uses paths returned by patch operation directly
- Relies on CWD being set correctly by macro runner

## Root Cause Analysis

The shader_judge_macro was written assuming it would be run from the project root directory, but AI-OS changes the CWD to the macro's directory during execution. This causes:

1. Incorrect project root inference
2. Failed file path resolution for prompt files
3. Confusion about where patches should be applied

## Recommendations for Engineering Agent

### 1. Immediate Fix for shader_judge_macro

The macro needs to be rewritten to handle AI-OS's CWD change properly:

```python
# Instead of:
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_script_dir)

# Use:
# When AI-OS runs the macro, CWD is already the macro's directory
# The project root is the parent of the current directory
project_root = os.path.abspath('..')
```

### 2. Path Resolution Strategy

All paths should be resolved relative to the determined project root:

```python
# For reading prompt files (which are provided as relative paths)
goal_prompt_path = os.path.join(project_root, raw_goal_prompt_path)

# For patch operations, ensure we're in the right directory
os.chdir(project_root)  # Change to project root before patching
```

### 3. Remove Hardcoded Paths

Replace hardcoded paths with dynamic resolution:

```python
# Instead of hardcoding:
shader_wgsl_full_path = os.path.join(rust_project_path, "src", "shader.wgsl")

# Find the actual location:
shader_files = glob.glob(os.path.join(rust_project_path, "**", "*.wgsl"), recursive=True)
```

### 4. Cargo Run Command

Simplify the cargo run command since we'll already be in the right directory:

```python
# Instead of:
command = f"cd \"{rust_project_path}\" && timeout 30 cargo run"

# Use:
os.chdir(rust_project_path)  # Change once at the start
command = "timeout 30 cargo run"
```

### 5. CRITICAL DISCOVERY: Duplicate Cargo.toml Files

There are TWO Cargo.toml files in the project:
- `/Users/nicholasbardy/git/shader_experiments/Cargo.toml` (root project)
- `/Users/nicholasbardy/git/shader_experiments/macros/Cargo.toml` (duplicate in macros directory)

This appears to be from a patch that was incorrectly applied to the macros directory instead of the project root. The macro's path inference logic (`os.path.dirname(current_script_dir)`) would make it think the project root is the macros directory when there's a Cargo.toml there.

**This needs to be fixed by:**
1. Removing the duplicate Cargo.toml from the macros directory
2. Ensuring the macro correctly identifies the actual project root
3. Making sure patches are applied relative to the correct directory

## Testing Recommendations

1. Test the macro from different working directories
2. Verify it works with the unusual directory structure (Cargo.toml in macros/)
3. Ensure patches are applied to the correct locations
4. Test with both absolute and relative prompt file paths

## Conclusion

The main issue is a mismatch between how the macro expects to be run (from project root) and how AI-OS actually runs it (from the macro's directory). The fix involves properly handling the CWD change and using consistent path resolution throughout the macro.