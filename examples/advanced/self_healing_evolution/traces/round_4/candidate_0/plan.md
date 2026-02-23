# Plan: Minimal Refinement of Best Shader (Score 6.5)

## Strategy
PRESERVE the working shader almost entirely. Only tweak 1-2 parameters to potentially improve visual quality without breaking what works.

## Changes from Best Shader
1. **Tube radius: 0.06 → 0.065** - Slightly thicker tubes to reduce any remaining dashed artifacts while staying well below the 0.08-0.11 danger zone
2. **Camera Y: 1.5 → 1.3** - Slightly lower viewing angle for better perspective on the fiber linking structure

## Mathematical Foundation
**Preserved exactly from best shader:**
- Hopf fibration quaternion: `q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ+rot), sin(φ/2)sin(θ+rot))`
- Stereographic projection: `q.xyz / (1.0 - q.w + 0.15)`
- 3 shell angles: π/6, π/3, π/2 (proven to avoid vertical streaks)
- 2 rotations per shell: 0, π/2
- Post-projection scale: 1.5 (proven sweet spot)

## Implementation Plan
1. Copy best shader structure verbatim
2. Change `TUBE_RADIUS` constant from 0.06 to 0.065
3. Change `CAMERA_Y` constant from 1.5 to 1.3
4. Keep all other constants, formulas, and logic identical

## Anticipated Challenges
**None** - This is a minimal parameter tweak of a proven 6.5-scoring shader. The changes are:
- Tube radius increase: 0.065 is still thin (< 0.08 threshold), safe from merging
- Camera Y decrease: 1.3 is within proven 1.0-2.0 range, just slightly lower perspective

## Visual Prediction
**Expected output:** Nearly identical to the 6.5-scoring best shader, with:
- Slightly more solid fiber tubes (less dashing) from 0.065 radius
- Slightly better perspective view of linking structure from lower camera
- Same vibrant colors, clean structure, proper alpha blending
- Same 6 distinct fibers in interlinked toroidal arrangement

**Key features to verify:**
- 6 distinct colored fiber tubes visible
- Toroidal/interlinked structure clear
- No merging, no collapse, no invisibility
- Smooth orbital camera motion
- Dark background with vibrant HSV colors
