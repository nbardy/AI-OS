"""Initial tiered guidance — the format template that the methodology critic maintains.

This provides the starting constraints before any learning has occurred.
The critic updates this file each round, preserving the tier structure.
Executors receive this as their concise technical rule set (~40 lines).
"""

INITIAL_GUIDANCE = """
# Tiered Guidance

## TIER 1: MANDATORY (violating guarantees failure)
- **Segment distance for curves**: Use distanceToSegment(p, a, b), NOT point distance | Evidence: R0 winners
- **External camera**: Camera outside geometry looking in | Evidence: Interior camera = invisible (R1)
- **No 2D arrays**: GLSL ES doesn't support vec3 arr[N][M] | Evidence: R3 compile failures
- **Contribution >= 0.08**: Lower values produce invisible output | Evidence: R1 visibility failures
- **Tube radius >= 0.12**: Smaller is barely visible | Evidence: R1

## TIER 2: PROVEN (used by high scorers)
- **32+ segments per fiber**: Smooth curves
- **High saturation colors**: HSV with S >= 0.9
- **Dark background**: vec3 < 0.05 for contrast
- **4-8 fiber elements**: Balance of structure and clarity
- **Orbital camera**: Slow rotation reveals 3D structure

## TIER 3: EXPERIMENTAL (worth trying)
- **Chromatic aberration**: RGB at offset distances
- **Fire/flame aesthetic**: FBM displacement + temperature colors

## DEPRECATED (don't retry)
- **Interior camera**: Produces murky fog, not structure
- **Point distance for curves**: Renders spheres, not curves
- **Thin-film interference**: Hard to tune, usually muddy
"""


def get_initial_guidance() -> str:
    """Get starting guidance when no prior runs exist."""
    return INITIAL_GUIDANCE
