# Goal 0: Spread Clifford Torus Implementation Plan

## Mathematical Foundation

### Core Hopf Fibration Equations
The Hopf map from S³ to S² uses quaternion coordinates:
```
q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ+ξ), sin(φ/2)sin(θ+ξ))
```
where:
- φ ∈ {π/6, π/3, π/2} (shell latitude angles)
- θ ∈ [0, 2π] (fiber parameter, 40 segments)
- ξ ∈ {0, π/2} (rotation offsets for linking)

### Stereographic Projection
Direct S³ → R³ projection (NOT via S²):
```
p = q.xyz / (1 - q.w + ε) × scale
```
where:
- ε = 0.15 (singularity protection, reduced from 0.35 to allow natural spread)
- scale = 1.5 (increased from 0.85 to spread fibers apart)

### Why These Shell Angles
The stereographic projection maps circles at latitude φ to circles of radius r = cos(φ/2)/sin(φ/2):
- φ = π/6 → r ≈ 3.73 (wide outer red ring)
- φ = π/3 → r ≈ 1.73 (medium golden ring)
- φ = π/2 → r = 1.00 (tight inner cyan ring)

These ratios ensure clearly separated, non-overlapping projected radii.

### Color Mapping
Latitude to hue via:
```
hue = mix(0.0, 0.55, (φ - π/6) / (π/2 - π/6))
```
Giving:
- Shell 0 (φ=π/6): hue ≈ 0.0 → red
- Shell 1 (φ=π/3): hue ≈ 0.275 → green-gold
- Shell 2 (φ=π/2): hue ≈ 0.55 → cyan

### Depth Cue
Gentle brightness falloff without invisibility:
```
brightness = mix(0.85, 1.0, exp(-0.03 × rayDepth))
```

## Implementation Plan

### Step 1: Generate 6 Fiber Geometries
Inside `main()`, create flat float arrays:
```glsl
float f0[120]; // Shell π/6, rotation 0
float f1[120]; // Shell π/6, rotation π/2
float f2[120]; // Shell π/3, rotation 0
float f3[120]; // Shell π/3, rotation π/2
float f4[120]; // Shell π/2, rotation 0
float f5[120]; // Shell π/2, rotation π/2
```

Each fiber: 40 segments × 3 floats (x,y,z) = 120 floats
Total: 6 × 120 = 720 floats < 960 limit ✓

### Step 2: Compute Fiber Points
For each fiber:
1. Compute quaternion q at 40 values of θ
2. Apply stereographic projection
3. Apply post-projection scale of 1.5
4. Store xyz in flat array

### Step 3: Setup Camera
Orbital camera:
- Distance: 3.0 (closer than R2's 4.5, to fill frame with spread geometry)
- Y-offset: 1.5 (proven working height)
- Angle: 0.25 × u_time (slow rotation)
- Position: `(dist×cos(angle), Y_OFFSET, dist×sin(angle))`
- LookAt: origin

### Step 4: Ray March
- 48 steps (under GPU budget)
- Step size: 0.10
- Check distances BEFORE stepping
- Maximum depth: 4.8 units

### Step 5: Distance Computation
For each ray sample:
1. Find minimum segment distance across all 6 fibers
2. Track which fiber/shell is nearest
3. Only nearest fiber contributes to density

### Step 6: Density and Alpha
Solid tube density:
```glsl
float density = max(0.0, (TUBE_RADIUS - minDist) / TUBE_RADIUS);
density = density * density; // Quadratic
```

Alpha accumulation:
```glsl
alpha += (1.0 - alpha) * (1.0 - exp(-density × 4.5));
```

### Step 7: Color Composition
1. Map nearest shell index to hue (0.0 → 0.55)
2. Convert HSV(hue, 0.95, 0.95) to RGB
3. Apply depth brightness falloff
4. Blend with dark background (0.02)

## Anticipated Challenges

### Challenge 1: Fiber Merging
**Risk**: Even with spread geometry, adjacent fibers might visually merge if tube radius is too large.

**Mitigation**:
- Use thin tubes (0.06, not 0.11)
- Nearest-only density prevents overlap accumulation
- Camera distance 3.0 fills frame without over-magnification

### Challenge 2: Singularity Protection Balance
**Risk**: ε=0.15 allows more extreme projection, might create very large geometry near poles.

**Solution**:
- Shell angles π/6, π/3, π/2 avoid extreme latitudes
- Ray march max depth 4.8 clips overly distant geometry
- Alpha saturation prevents overexposure

### Challenge 3: GPU Budget
**Risk**: 48 steps × 6 fibers × 40 segments = 11,520 operations/pixel

**Verification**: 11,520 < 15,000 limit ✓

**Optimization**: Check-before-step early exit when alpha > 0.99

### Challenge 4: Color Distinction
**Risk**: Three colors might not be visually distinct enough.

**Solution**:
- Wide hue spread (0.0 → 0.55 covers red → cyan)
- High saturation (0.95) maximizes vividness
- Dark background (0.02) maximizes contrast

## Visual Prediction

### Expected Output
Three concentric luminous rings against near-black space:

1. **Outer Red Ring** (φ=π/6)
   - Largest diameter (~3.7 × scale = 5.6 units)
   - Warm red glow
   - Two linked circles offset 90°

2. **Middle Golden Ring** (φ=π/3)
   - Medium diameter (~1.7 × scale = 2.6 units)
   - Green-gold transition color
   - Weaves through outer ring

3. **Inner Cyan Ring** (φ=π/2)
   - Smallest diameter (~1.0 × scale = 1.5 units)
   - Cool cyan glow
   - Nested at center

### Key Visual Features
✓ **Individual Visibility**: Each of 6 fibers is a distinct thin tube, not merged blob
✓ **Nested Structure**: Three clearly different-sized rings, not compressed into one form
✓ **Color Gradation**: Red (outer) → gold (middle) → cyan (inner) creates thermal depth cue
✓ **Linking Topology**: Where circles cross, color layering shows which fiber is in front
✓ **Spatial Fill**: Geometry spreads across most of frame, not "small form in void"

### Verification Criteria
- **Geometry Spread**: Outer ring touches edges of frame
- **No Merging**: Can count 6 distinct fiber loops
- **Color Distinct**: Three shell colors are clearly different
- **Depth Legible**: Can distinguish near vs far crossings by brightness
- **No Compression**: Fibers are circular loops, not elliptical/kidney-bean

## Implementation Strategy Summary

This is a **ROOT CAUSE FIX** for the R2 "kidney bean blob" failure:

| Parameter | R2 Value | This Value | Rationale |
|-----------|----------|------------|-----------|
| Scale | 0.85 | 1.5 | Spread fibers apart |
| Epsilon | 0.35 | 0.15 | Natural projection |
| Tube radius | 0.11 | 0.06 | Thin, non-merging |
| Camera dist | 4.5 | 3.0 | Fill spread geometry |
| Shell angles | π/8..π/2 | π/6, π/3, π/2 | Distinct radii |

Every change targets geometry visibility and spatial separation. No GPU budget wasted on invisible features (Fresnel, animation phase, crossing detection). This follows ALL Tier 1 mandatory rules and ALL Tier 2 proven techniques.
