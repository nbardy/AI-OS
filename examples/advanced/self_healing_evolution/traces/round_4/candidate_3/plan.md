# Implementation Plan: Fresnel-Edged Fibers with Crossing Brightness Flare

## Mathematical Foundation

### Core Hopf Fibration Equations
- **Quaternion parameterization**: `q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ+rot), sin(φ/2)sin(θ+rot))`
- **Stereographic projection**: `R3 = q.xyz / (1.0 - q.w + 0.15)`
- **Post-projection scale**: `1.5` to spread fibers while maintaining visibility
- **Four fibers on Clifford torus**: η = π/4, rotations at {0, π/2, π, 3π/2}
- **Segments**: 40 per fiber with wrap-around

### Fresnel Edge Enhancement
- **Tangent vector**: `tangent = normalize(segmentEnd - segmentStart)`
- **View angle**: `viewAngle = abs(dot(normalize(rayDir), tangent))`
- **Fresnel factor**: `fresnel = pow(1.0 - viewAngle, 2.0)`
- **Edge brightness boost**: `mix(1.0, 2.5, fresnel)` — edges 2.5x brighter than centers

### Crossing Brightness Flare
- After accumulating all 4 fiber contributions per step
- If `totalAlpha > 0.6`, add white boost: `vec3(0.3) * (totalAlpha - 0.6)`
- Creates bright nodes where fibers overlap in screen space

## Implementation Plan

### 1. Setup and Camera (Lines 1-30)
- Standard UV calculation: `(gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y`
- Orbital camera: `vec3(3.0 * cos(u_time * 0.25), 1.5, 3.0 * sin(u_time * 0.25))`
- Ray direction: camera-to-pixel vector
- Dark background: `vec3(0.01, 0.01, 0.02)`

### 2. Geometry Generation (Lines 31-80)
- Flat array allocation inside main(): `float segments[480]` (4 fibers × 40 segments × 3 coords)
- Loop over 4 fibers with rotations: {0.0, π/2, π, 3π/2}
- For each fiber, 40 segments:
  - θ = 2π * seg / 40
  - φ = π/4 (Clifford torus)
  - Compute quaternion q
  - Stereographic projection with ε = 0.15
  - Scale by 1.5
  - Store xyz in flat array at index `fiberIdx * 120 + seg * 3 + {0,1,2}`

### 3. Ray Marching (Lines 81-150)
- 60 steps, step size 0.10
- Max distance 8.0 (accommodates scale 1.5 geometry)
- **Per-step front-to-back accumulation**:
  - For each step position p:
    - Loop over 4 fibers
    - Find nearest segment to p (check all 40 segments per fiber)
    - Compute tube density: `(0.06 - minDist) / 0.06` if minDist < 0.06
    - **Compute Fresnel term**:
      - Extract nearest segment endpoints from array
      - `tangent = normalize(b - a)`
      - `viewAngle = abs(dot(normalize(rayDir), tangent))`
      - `fresnel = pow(1.0 - viewAngle, 2.0)`
      - `edgeBoost = mix(1.0, 2.5, fresnel)`
    - Quadratic density: `d = d * d`
    - Exponential alpha: `alpha = (1.0 - exp(-d * 4.5)) * 0.85`
    - Fiber color with edge boost: `fiberColor * edgeBoost`
    - Accumulate: `color += fiberColor * edgeBoost * alpha * (1.0 - totalAlpha)`
    - `totalAlpha += alpha * (1.0 - totalAlpha)`
    - Add glow halo at 1.5x radius (0.09): `exp(-glowDist * 5.0) * 0.08 * (1.0 - totalAlpha)`
  - **After all 4 fibers processed**:
    - If `totalAlpha > 0.6`: `color += vec3(0.3) * (totalAlpha - 0.6)` (crossing flare)
  - If `totalAlpha > 0.95`, break early

### 4. Color Palette
- **Fiber 0 (rot=0)**: HSV(0.0, 0.95, 0.95) → Ruby red
- **Fiber 1 (rot=π/2)**: HSV(0.08, 0.95, 0.95) → Amber orange
- **Fiber 2 (rot=π)**: HSV(0.5, 0.95, 0.95) → Teal cyan
- **Fiber 3 (rot=3π/2)**: HSV(0.75, 0.95, 0.95) → Violet purple
- Complementary split palette for architectural neon aesthetic

### 5. HSV to RGB Conversion
- Standard formula with hue wheel mapping
- Inline function to keep code compact

## Anticipated Challenges

### Challenge 1: Array Indexing Arithmetic
- **Risk**: Off-by-one errors in flat array indexing
- **Mitigation**: Consistent pattern `fiberIdx * 120 + segIdx * 3 + {0,1,2}`
- **Verification**: Ensure wrap-around `(seg+1) % 40` doesn't break indexing

### Challenge 2: Fresnel Tangent Calculation
- **Risk**: Tangent vector undefined for degenerate segments (a ≈ b)
- **Mitigation**: Segments should never degenerate with 40 samples around a smooth curve
- **Verification**: Check if normalize() returns NaN, default to no boost (factor 1.0)

### Challenge 3: GPU Budget
- **Workload**: 60 steps × 4 fibers × 40 segments = 9,600 iterations/pixel (under 15,000 limit)
- **Risk**: Fresnel adds 1 normalize + 1 dot + 1 pow per step per fiber (240 extra ops)
- **Mitigation**: Still well under budget; modern GPUs handle this easily

### Challenge 4: Crossing Flare Tuning
- **Risk**: Threshold 0.6 may be too high (no flares) or too low (everything flares)
- **Mitigation**: 0.6 is chosen so single fiber alpha (max ~0.85) doesn't trigger it alone
- **Verification**: Only overlapping fibers (alpha ~1.0+) should exceed threshold

### Challenge 5: Step Size vs Tube Radius
- **Risk**: Step 0.10 with tube 0.06 may miss geometry between steps
- **Mitigation**: Glow halo at 1.5x (0.09) ensures 0.10 steps always sample some glow
- **Evidence**: R3C1, C4 scored 6.5 with this exact configuration

## Visual Prediction

### Expected Output
1. **Four distinct fibers** winding in a linked torus configuration
2. **Bright silhouette edges** on each fiber (Fresnel effect) — fibers appear as glowing neon tubes with brighter rims
3. **Dark centers** where viewer looks along the fiber axis
4. **White-hot crossing points** where two or more fibers overlap in screen space
5. **Color-coded structure**: Ruby, amber, teal, violet fibers on nearly black background
6. **Smooth orbital rotation** showing different views of the linking structure

### Key Visual Features to Verify Success
- ✓ Fibers are separated (not merged into blob)
- ✓ Each fiber has consistent color along its length
- ✓ Edges are visibly brighter than centers (not uniform glow)
- ✓ At least 2-3 bright white flares visible where fibers cross
- ✓ Overall "neon sculpture" aesthetic — sharp, architectural, luminous
- ✓ No dashed/segmented appearance (glow fills gaps)
- ✓ No invisible regions (scale 1.5 keeps geometry in view)

### Success Criteria
- **Breaking 7.5 → 8+**: "Sharper fiber definition" ✓ (Fresnel edges), "visible linking at crossing points" ✓ (white flares)
- **Geometry**: Exactly the proven R3C1/C4 configuration (scored 6.5)
- **Enhancement**: Pure shading improvement, no geometry changes
- **Mathematical fidelity**: Direct Hopf fibration with no shortcuts
