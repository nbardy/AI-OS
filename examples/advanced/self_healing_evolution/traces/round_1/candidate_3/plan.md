# Implementation Plan: Trefoil-Linked Fiber Triptych with Phase-Shifted Glow

## Mathematical Foundation

### Hopf Fibration Quaternion (MANDATORY)
```
q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta+xi1), sin(phi/2)*sin(theta+xi1))
```
- `phi`: shell angle (latitude on S2) - using 2 values: pi/4, 3pi/8
- `theta`: parameter along fiber [0, 2pi], 40 segments
- `xi1`: longitude rotation - using 3 values: 0, 2pi/3, 4pi/3

This gives 2 shells × 3 longitudes = 6 fibers total (within proven 4-8 range).

### Stereographic Projection (MANDATORY)
```
xyz = q.xyz / (1 - q.w + 0.35) * 0.85
```
- Singularity protection: +0.35
- Post-projection scale: 0.85 (proven range 0.80-0.90)

### Phase-Shifted Glow (NOVEL)
```
pulse = 0.7 + 0.3 * sin(thetaParam + fiberIndex * pi/3 + u_time * 2.0)
```
- Each fiber gets a traveling wave of brightness
- Phase offset: pi/3 between fibers creates sequential pulse pattern
- Modulates density contribution without changing geometry (experimental modification at compositing stage only)

### Triadic Color Scheme (EXPERIMENTAL)
Three hue families spaced 120° apart:
- Fibers 0,1: coral-red (hue 0.02)
- Fibers 2,3: emerald-green (hue 0.35)
- Fibers 4,5: violet-blue (hue 0.72)
All at HSV(h, 0.95, 0.95) for maximum vibrancy.

## Implementation Plan

### Step 1: Fiber Generation (in main())
1. Declare flat array: `float fiberData[720]` (6 fibers × 40 segments × 3 coords = 720 floats < 960 limit)
2. Loop over 6 fibers:
   - fiber 0,1: phi = pi/4, xi1 = {0, 2pi/3, 4pi/3}[0]
   - fiber 2,3: phi = pi/4, xi1 = {0, 2pi/3, 4pi/3}[1]
   - fiber 4,5: phi = pi/4, xi1 = {0, 2pi/3, 4pi/3}[2]
   - fiber 0,2,4: shell phi = pi/4
   - fiber 1,3,5: shell phi = 3pi/8
3. For each fiber, generate 40 segments via theta sweep
4. Apply quaternion formula, stereographic projection, post-scale 0.85

### Step 2: Camera Setup (MANDATORY Y-offset orbit)
```
angle = u_time * 0.25
camPos = vec3(4.5 * cos(angle), 1.5, 4.5 * sin(angle))
```
- Distance: 4.5 (proven safe)
- Y-offset: 1.5 (NOT spherical elevation)
- Rotation speed: 0.25 rad/s (proven slow reveal)

### Step 3: Ray Marching (CHECK-before-STEP)
1. Compute ray direction from camera through pixel
2. Initialize rayPos at camera
3. Loop 64 steps:
   - **CHECK distances at rayPos FIRST** (mandatory)
   - Accumulate density from all 40 segments of all 6 fibers
   - THEN advance rayPos by 0.12
4. For each segment check, compute theta parameter for pulse modulation

### Step 4: Distance & Density Calculation
```glsl
float distanceToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a;
    float t = clamp(dot(p - a, ab) / dot(ab, ab), 0.0, 1.0);
    return length(p - (a + t * ab));
}

// In ray march loop:
float dist = distanceToSegment(rayPos, segA, segB);
dist = abs(dist); // unsigned distance (MANDATORY)
float thetaParam = float(seg) / 40.0 * 6.2832;
float pulse = 0.7 + 0.3 * sin(thetaParam + float(fiberIdx) * 1.047 + u_time * 2.0);
float contrib = exp(-dist * dist * 50.0) * pulse;
density += contrib;
colorAccum += fiberColor * contrib;
```

### Step 5: Compositing
1. Quadratic density: already in `dist * dist`
2. Exponential alpha: `alpha = 1.0 - exp(-density * 4.5)`
3. Transparency factor: `alpha *= 0.85`
4. Add glow halo at 1.5× tube radius (0.11 × 1.5 = 0.165): `exp(-glowDist * 5.0) * 0.08`
5. Final color against dark background `vec3(0.01, 0.01, 0.02)`

## Anticipated Challenges

### Challenge 1: Phase Calculation Precision
The theta parameter must accurately track position along the fiber curve for the pulse to appear as a coherent traveling wave.

**Mitigation**: Use exact formula `float(seg) / 40.0 * 6.2832` to ensure theta ∈ [0, 2pi]. The segment index already encodes fiber position.

### Challenge 2: Array Size Limits
720 floats is close to the 960 limit. Must ensure tight packing.

**Mitigation**: Store only xyz per segment (not quaternion). 6 × 40 × 3 = 720 exactly. Verified under limit.

### Challenge 3: Fiber Overlap Legibility
Three pairs of rings threading through each other could blur into chaos.

**Mitigation**:
- Triadic color scheme provides maximum hue separation (120° apart)
- Phase-shifted glow creates temporal separation (different fibers brighten at different times)
- Camera Y-offset of 1.5 provides oblique view that shows depth layering

### Challenge 4: Glow Pulse Visibility
If pulse amplitude is too subtle, the novel feature won't be apparent.

**Mitigation**:
- Pulse range 0.7-1.0 (30% modulation) is significant without flickering
- u_time multiplier of 2.0 creates visible motion in static frame
- Each fiber phase-shifted by pi/3 → visible sequential pattern

## Visual Prediction

### Expected Output
A tight braid-like arrangement of six glowing rings:
- Three distinct color families (coral-red, emerald-green, violet-blue)
- Each color appears twice (two rings per color from two shells)
- Rings thread through each other in a pretzel/knot-like pattern
- Bright spots pulse along each ring, creating a "chasing lights" effect
- Dark background makes the fibers pop with high contrast

### Key Visual Features to Verify

1. **Linking Structure**: At oblique camera angle (Y=1.5), should see rings passing over/under each other, not just parallel circles
2. **Color Separation**: Three distinct color zones, each appearing twice (one brighter/larger, one dimmer/smaller from depth)
3. **Pulse Animation**: Bright spots traveling along rings, offset between fibers → sequential "wave" pattern
4. **Depth Perception**: Camera orbit should reveal 3D structure, with fibers at different depths becoming visible as camera rotates
5. **Halo Glow**: Soft glow around each fiber tube makes them appear luminous, not just solid

### Failure Modes to Watch For
- **Blob**: If quaternion breaks → check cos(phi/2) terms
- **Overhead view**: If camera uses spherical elevation → verify Y-offset formula
- **Invisible fibers**: If distance field unsigned conversion missing → check abs()
- **Flat circles**: If rotation parameters identical → verify xi1 spacing
- **Static appearance**: If pulse too subtle → check pulse amplitude and u_time factor

## Why This Should Work

### Novel Elements Within Proven Framework
- **Longitude grouping**: Three fibers at 120° longitude intervals is a structural novelty not yet tried, but fiber count (6) stays within proven 4-8 range
- **Phase-shifted glow**: Compositing-stage modification only (per methodology critique guidance), doesn't touch proven geometry/distance field pipeline
- **Triadic palette**: Extends proven "complementary pair" principle to three families, maximizing perceptual separation

### All MANDATORY Rules Preserved
✓ Correct Hopf quaternion with proper angle parameters
✓ Y-offset orbit camera (NOT spherical elevation)
✓ Camera distance 4.5
✓ Flat array in main(), 720 < 960 floats
✓ Post-projection scale 0.85
✓ Check-before-step ray march
✓ Segment distance function
✓ Unsigned distance conversion
✓ Tube radius 0.11
✓ 40 segments per fiber
✓ Stereographic singularity protection 0.35

### Evidence-Based Parameter Choices
- Shell angles pi/4, 3pi/8: Dense spacing from proven tier 2 guidance
- HSV(h, 0.95, 0.95): Proven in prior 7.5/10 candidate
- Dark background vec3(0.01, 0.01, 0.02): All high scorers use ~0.02
- Orbital speed 0.25 rad/s: Proven slow reveal
- Quadratic density + exponential alpha: Prior 7.5/10 formula
- Transparency 0.85: Proven for overlap visibility
- Glow at 1.5× radius: Prior 7.5/10 specification

The combination of structural novelty (longitude-grouped fiber family) with proven rendering pipeline and a compositing-stage animation feature should produce both visual interest and technical stability.
