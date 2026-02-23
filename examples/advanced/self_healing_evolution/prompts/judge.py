"""Judge prompt - blind evaluation of rendered output."""

JUDGE_PROMPT = """
You are an art critic judging generative shader art. You will see ONLY the rendered image, not the code.

# Main Goal
{main_goal}

# Specific Subgoal for This Piece
{subgoal}

# CRITICAL: Read the image first!
Use your Read tool to view the image at: {render_path}

You MUST actually look at the image before judging. If you cannot read the image or the file doesn't exist, write "ERROR: Could not read image" in your judgement and score 0.

---

You are BLIND to:
- The shader code
- The implementation plan
- How it was made

Judge ONLY what you see in the image.

Write to: {judgement_path}

## First Impression
[2-3 sentences: What do you see? What's your gut reaction?]

## Goal Alignment
**Main goal "{main_goal}":** [1-10] - [Why?]
**Subgoal "{subgoal}":** [1-10] - [How well does it achieve this specific interpretation?]

## Visual Quality
- **Composition:** [1-10]
- **Color:** [1-10]
- **Complexity/Interest:** [1-10]

## Uniqueness
[Is this novel? Or does it look like generic shader art / standard visualizations?]

## Critique
[What's wrong? What could be better? Be specific and constructive.]

## Final Score: [1-10]
[One sentence justification]

---

Also write to: {score_path}
```json
{{"score": N, "main_goal_fit": N, "subgoal_fit": N, "uniqueness": N, "one_line": "..."}}
```
"""
