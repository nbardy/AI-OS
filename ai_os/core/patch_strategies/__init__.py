# ai_os/core/patch_strategies/__init__.py

from .strategy_full_file import run_strategy as run_full_file_strategy
# from .strategy_git_diff import run_strategy as run_git_diff_strategy # TBD
# from .strategy_step_by_step import run_strategy as run_step_by_step_strategy # TBD

# Registry of available patch strategies
# Maps strategy name to its runner function
PATCH_STRATEGIES = {
    "full_file": run_full_file_strategy,
    # "git_diff": run_git_diff_strategy, # Add when implemented
    # "step_by_step": run_step_by_step_strategy, # Add when implemented
}

# Re-export for easy access
# from .strategy_full_file import run_strategy # Example if you want direct import 