# Implementation Plan: Nested Tori with Parallax Depth and Fresnel Edges

## Mathematical Foundation

### Core Equations
1. **Clifford Torus Parameterization** (two shells at different η values):
   - Outer torus: `η₁ = π/4` (standard equal-radii torus)
   - Inner torus: `η₂ = π/6` (thinner torus, more compressed)
   - For each η, generate quaternions: `q = (cos(η)cos(ξ₁), cos(η)sin(ξ₁), sin(η)cos(ξ₂), sin(η)sin(ξ₂))`
   - ξ₁ varies 0→2π (fiber parameter), ξ₂ is the shell rotation angle

2. **Stereographic Projection** (direct S³→R³):
   ```
   p = q.xyz / (1 - q.w + 0.35) * 0.85
   ```
   - Singularity protection: 0.35
   - Post-projection scale: 0.85

3. **Fresnel Edge Term**:
   ```
   fresnel = pow(1.0 - abs(dot(rayDir, fiberTangent)), 3.0)
   ```
   - Brightens fibers when viewed edge-on
   - Tangent computed as `normalize(nextPoint - currentPoint)`

4. **Density Function** (solid tube):
   ```
   if (minDist < tubeRadius) {
       density = (tubeRadius - minDist) / tubeRadius
       density *= mix(1.0, 2.0, fresnel)
   }
   ```

### Coordinate Mapping
- **Camera**: Y-offset orbit at `(4.5*cos(angle), 1.5, 4.5*sin(angle))` with angle = 0.25*u_time
- **UV**: Standard aspect-correct `(gl_FragCoord.xy - 0.5*u_resolution.xy) / u_resolution.y`
- **Ray origin**: camera position
- **Ray direction**: normalize(target - camera) where target is scene center (0,0,0)

### Configuration
- **Outer torus**: 4 fibers, tube radius 0.11, colors warm (gold→coral, hues 30°→15°)
- **Inner torus**: 4 fibers, tube radius 0.08, colors cool (cyan→violet, hues 180°→270°)
- **Total**: 8 fibers × 40 segments = 320 segments
- **Ray march**: 46 steps × 0.10 step size = 4.6 units (enough to traverse scene)
- **GPU budget**: 46 steps × 8 fibers × 40 segments = 14,720 iterations (safely under 15,000)

## Implementation Plan

### Step 1: Generate Fiber Geometry Data (inside main())
```c
float fiberData[960];  // 8 fibers × 40 segments × 3 coords = 960 floats
```
- Loop over 2 torus shells (η = π/4 for outer, π/6 for inner)
- For each shell, generate 4 fibers at rotations ξ₂ = 0°, 45°, 90°, 135°
- For each fiber, compute 40 points by varying ξ₁ from 0→2π
- Store as flat array: [x₀, y₀, z₀, x₁, y₁, z₁, ...]

### Step 2: Ray Marching Loop
- March ray from camera through each pixel
- For each step (46 steps):
  - Check distance to ALL 8 fibers (loop over fibers)
  - For each fiber, check distance to all 40 segments
  - Track global minimum distance and which segment it came from
  - If within tube radius, compute density with Fresnel enhancement
  - Accumulate color using `1 - exp(-density² * 4.5)` for alpha

### Step 3: Density Computation with Fresnel
- Find nearest segment index and compute segment endpoints
- Calculate fiber tangent: `normalize(nextPoint - currentPoint)`
- Compute Fresnel term: `pow(1.0 - abs(dot(normalize(rayDir), tangent)), 3.0)`
- Base density: `(tubeRadius - minDist) / tubeRadius`
- Enhanced density: `baseDensity * mix(1.0, 2.0, fresnel)`
- Square for steeper falloff: `density²`

### Step 4: Color Assignment
- Outer 4 fibers: HSV hues 30°, 22.5°, 15°, 7.5° (gold→coral gradient)
- Inner 4 fibers: HSV hues 180°, 210°, 240°, 270° (cyan→violet gradient)
- All fibers: saturation 0.95, value 0.95
- Use nearest fiber's color only (no blending across fibers)

### Step 5: Compositing
- Alpha blending: `color = mix(color, fiberColor, alpha * 0.85)`
- Transparency factor 0.85 allows overlap visibility
- Background: vec3(0.02, 0.02, 0.03) (near-black with subtle blue)

## Anticipated Challenges

### Challenge 1: GPU Budget Management
- **Risk**: 46 steps × 8 fibers × 40 segments = 14,720 iterations per pixel
- **Mitigation**: This is just under the 15,000 limit. If timeout occurs, reduce to 44 steps.
- **Fallback**: Could reduce segments to 32 (saves 20% inner loop work)

### Challenge 2: Fresnel Term Stability
- **Risk**: Division by zero if tangent or rayDir is zero-length
- **Mitigation**: Use `abs(dot())` to handle both-sided viewing, normalize both vectors
- **Validation**: Clamp Fresnel term to [0, 1] after pow()

### Challenge 3: Nested Visibility
- **Risk**: Outer torus may completely occlude inner torus
- **Mitigation**: Use transparency (0.85 factor) and ensure inner fibers are bright enough (V=0.95)
- **Visual check**: Inner cyan/violet should peek through gaps between outer gold fibers

### Challenge 4: Tangent Computation at Segment Boundaries
- **Risk**: At segment 39, need to wrap to segment 0 for tangent
- **Mitigation**: Use modulo: `nextIdx = (segIdx + 1) % 40`
- **Edge case**: Ensure wrap happens correctly in array indexing

## Visual Prediction

### Expected Appearance
1. **Structure**: Two nested rings of glowing fiber bundles
   - Outer ring: 4 thick golden-amber fibers forming a braided torus
   - Inner ring: 4 thinner cyan-violet fibers visible through gaps

2. **Depth Cues**:
   - Fibers brighten at edges (Fresnel effect) creating rim-lit silhouettes
   - When inner fibers align with outer fiber gaps, they appear brighter
   - Top-down camera angle (Y=1.5) reveals layering clearly

3. **Color Palette**:
   - Warm outer shell: gold (30°) → coral (7.5°) in HSV
   - Cool inner shell: cyan (180°) → violet (270°) in HSV
   - Strong warm/cool contrast for depth perception

4. **Animation**:
   - Slow 0.25 rad/s orbit reveals different viewing angles
   - At some angles, inner torus emerges clearly; at others, it's mostly hidden
   - Parallax between near and far fibers as camera moves

### Verification Checkpoints
- ✓ Can see 8 distinct fiber colors (4 warm + 4 cool)
- ✓ Inner fibers visible through outer gaps (transparency working)
- ✓ Fibers appear brighter at edges than face-on (Fresnel working)
- ✓ Smooth continuous curves, no faceting (40 segments sufficient)
- ✓ No black screen (GPU budget within limits)
- ✓ Structure appears 3D with depth (not flat blob)

### Success Criteria (targeting 8+/10)
- Sharp fiber definition (tube radius 0.08-0.11, segment distance used)
- Clear depth cues (Fresnel edge enhancement, nested layers visible)
- Rich interlocking structure (8 fibers at complementary angles)
- Smooth rendering (no artifacts, proper alpha blending)
- Visually distinct from previous 7.5/10 (nested tori + Fresnel is new)
