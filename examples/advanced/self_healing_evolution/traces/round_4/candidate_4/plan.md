# Dual-Latitude Fiber Families with Depth-Fog Separation

## Mathematical Foundation

### Core Hopf Fibration
Using the standard quaternion parameterization:
```
q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ+ρ), sin(φ/2)sin(θ+ρ))
```

Where:
- `φ` (phi) = latitude parameter (0 to π) — determines which fiber on S³
- `θ` (theta) = longitude on the fiber (0 to 2π) — position along the fiber
- `ρ` (rho) = rotation offset distinguishing different fibers at same latitude

### Two Fiber Families

**Family A (Inner, Warm):** η = π/6
- `cos(π/12) ≈ 0.9659`, `sin(π/12) ≈ 0.2588`
- Smaller stereographic radius after projection
- 2 fibers: rotations 0, π
- Colors: gold (HSV 0.08) and copper (HSV 0.05)

**Family B (Outer, Cool):** η = π/3
- `cos(π/6) ≈ 0.8660`, `sin(π/6) ≈ 0.5000`
- Larger stereographic radius after projection
- 2 fibers: rotations π/4, 5π/4
- Colors: cyan (HSV 0.52) and silver-blue (HSV 0.55)

### Stereographic Projection
Direct S³ → R³ projection:
```
p = q.xyz / (1.0 - q.w + epsilon)
```
Using epsilon = 0.15 to prevent singularity at q.w = 1.0

### Depth Fog
At each ray march step with parameter `t`:
```
fogFactor = exp(-t * 0.3)
color *= fogFactor
```

This darkens geometry proportionally to distance from camera, providing clear depth separation.

## Implementation Plan

### 1. Setup Phase
- Standard UV calculation with aspect correction
- Camera setup: orbital at distance 3.0, Y-offset 1.2
- Ray direction from camera through UV coordinates
- Initialize accumulation variables (color, alpha)

### 2. Fiber Data Arrays
Flat arrays inside main() to store:
- 4 latitudes (2x Family A at π/6, 2x Family B at π/3)
- 4 rotations (0, π, π/4, 5π/4)
- 4 color hues (0.08, 0.05, 0.52, 0.55)
- 4 color saturations and values

Total: ~16 floats, well under 960 limit

### 3. Fiber Generation Loop
For each fiber (4 total):
- Generate 40 segments along fiber (θ from 0 to 2π)
- For each segment:
  - Compute quaternion q using Hopf formula
  - Apply stereographic projection
  - Scale by 1.5 post-projection
  - Store segment endpoints

Total geometry: 4 fibers × 40 segments = 160 segments

### 4. Ray March Loop
64 steps at step size 0.10 → max depth 6.4
For each step:
- Compute current ray position
- Find minimum distance to ALL fiber segments (4×40=160)
- Compute tube density using closest segment only
- If density > 0:
  - Apply quadratic density: `d² * normalizer`
  - Convert to alpha: `(1 - exp(-d*4.5)) * 0.85`
  - Add glow halo at 1.5× tube radius
  - Apply depth fog based on current `t`
  - Blend color with front-to-back alpha compositing
- Advance ray

Total iterations: 64 steps × 4 fibers × 40 segments = 10,240 (under 15k limit)

### 5. Output
- Return accumulated color
- Background: vec3(0.02) dark gray

## Anticipated Challenges

### Challenge 1: Fiber Merging at Same Latitude
With 2 fibers at each latitude separated by π rotation, they may appear too close after projection.
**Mitigation:** Using proven tube radius 0.06, which has shown good separation in previous candidates.

### Challenge 2: Depth Fog Too Strong
Fog factor 0.3 might darken geometry too aggressively, making far side invisible.
**Mitigation:** This value is calibrated for viewing distance 3.0 and max ray depth 6.4. Far geometry will fade to ~15% brightness, still visible against dark background.

### Challenge 3: GPU Budget with Depth Fog
Adding `exp(-t*0.3)` per ray march step adds computational cost.
**Mitigation:** Single exp() per step is trivial compared to 160-segment distance checks. Total cost still well under limit.

### Challenge 4: Color Distinction Between Families
Warm (gold/copper) vs cool (cyan/silver) might not provide enough visual separation.
**Mitigation:** Using proven HSV approach with high saturation (0.85-0.9) and widely separated hues (0.05-0.08 vs 0.52-0.55, ~0.45 difference on color wheel).

## Visual Prediction

### Expected Appearance
- **Inner structure:** Two warm-colored (gold/copper) fiber loops forming a smaller torus shape, glowing against dark background
- **Outer structure:** Two cool-colored (cyan/silver) fiber loops forming a larger torus shape, visibly enclosing the inner fibers
- **Depth effect:** Far side of each torus noticeably darker than near side, creating clear 3D volume perception
- **Linking topology:** Outer fibers should visibly pass "through" and "around" inner fibers, demonstrating the Hopf linking number
- **Glow halos:** Soft luminous aura around each fiber tube, covering ray march sampling gaps

### Key Visual Verification Points
1. **Two distinct scales:** Inner and outer torus structures clearly separated in size
2. **Nested configuration:** Outer fibers enclose inner fibers (not overlapping randomly)
3. **Depth gradient:** Continuous darkening from front to back on each torus
4. **Color families:** Warm inner, cool outer — immediately distinguishable
5. **No dashed artifacts:** Solid tubes with smooth glow, no segmentation visible
6. **Orbital camera motion:** Gentle rotation revealing 3D structure from multiple angles

### Success Criteria
- Distinct inner/outer torus forms (proving dual-latitude works)
- Visible depth separation via fog (proving depth cues work)
- Warm/cool color encoding readable (proving visual design works)
- No geometric artifacts (proving implementation correctness)
- All mandatory constraints satisfied (proving rule compliance)
