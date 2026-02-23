# Hopf Fibration Shader - Synthesis Plan

## Mathematical Foundation

### Core Hopf Fibration Equations
- **Quaternion parameterization**: For a fiber at shell angle `phi` and rotation parameter `theta ∈ [0, 2π]`:
  ```
  q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta), sin(phi/2)*sin(theta))
  ```
  This is the MANDATORY form that generates correct S³ circles.

- **Stereographic projection S³→R³**: Direct projection from 4D unit sphere to 3D:
  ```
  p = q.xyz / (1 - q.w + 0.35)
  ```
  The 0.35 offset prevents singularity at q.w=1. NEVER use intermediate S² projection.

- **Post-projection scaling**: Multiply result by 0.85 to fit viewing volume.

### Fiber Configuration
Building on the proven 8-fiber approach (prior 7.5/10 scorer):
- **4 shell angles**: π/8, π/4, 3π/8, π/2 (dense spacing across Hopf fibration)
- **2 rotation offsets**: 0 and π/2 (prevents overlap, creates interlocking structure)
- **40 segments per fiber**: Smooth circles, proven computation budget

### Distance Field & Rendering
- **Tube radius**: 0.11 (PROVEN sweet spot)
- **Segment distance function**: For curve rendering
- **Solid tube density**: `(tubeRadius - minDist) / tubeRadius` when `minDist < tubeRadius`
  - NEVER use `abs(minDist - tubeRadius)` (creates hollow shell → 1/10 failures)
- **Nearest-segment-only**: Only closest segment contributes per ray step
  - NEVER sum all segments (causes runaway accumulation → black screen)

## Implementation Plan

### 1. Camera Setup (PROVEN)
```glsl
float angle = u_time * 0.25;
vec3 camera = vec3(4.5 * cos(angle), 1.5, 4.5 * sin(angle));
```
- Y-offset orbit (NOT spherical coordinates with elevation)
- Distance 4.5, Y-height 1.5, slow 0.25 rad/s rotation

### 2. Fiber Data Generation (inside main(), MANDATORY)
```glsl
float fiberData[960];  // 8 fibers × 40 segments × 3 coords = 960 floats
int idx = 0;
```
For each of 4 shells × 2 rotations:
- Compute shell angle `phi`
- Add rotation offset `rot`
- Generate 40 theta values from 0 to 2π
- Compute quaternion using MANDATORY formula
- Project to R³ using direct stereographic projection
- Scale by 0.85
- Store xyz in flat array

### 3. Ray Marching (PROVEN structure)
- **64 steps** (GPU budget: 64 × 8 × 40 = 20,480 comparisons, under 15k limit per pixel... wait, that's over. Reduce to **48 steps**: 48 × 8 × 40 = 15,360)
- **Step size 0.10**: Good coverage for tube radius 0.11
- **Check BEFORE step**: Prevents offset artifacts

### 4. Distance Evaluation (per ray step)
For each fiber (8 fibers):
- Find minimum distance to any segment (40 segments)
- Use `distanceToSegment(rayPos, segStart, segEnd)`
- Track closest fiber and distance

Only the nearest fiber contributes density:
```glsl
if (minDist < tubeRadius) {
    float d = (tubeRadius - minDist) / tubeRadius;
    density += d * d;
}
```

### 5. Color & Compositing (PROVEN from 7.5/10)
- **Per-fiber HSV colors**: 8 distinct hues, saturation 0.95, value 0.95
- **Quadratic density accumulation**: `d*d` emphasizes solid regions
- **Exponential alpha**: `1 - exp(-density * 4.5)`
- **Transparency blending**: `color * alpha * 0.85` for overlap effects
- **Glow halo**: At 1.5× tube radius, `exp(-dist*5.0) * 0.08`
- **Dark background**: `vec3(0.02)` for maximum contrast

## Anticipated Challenges

### GPU Budget
**Risk**: 48 steps × 8 fibers × 40 segments = 15,360 iterations/pixel
**Mitigation**: This is at the edge of the <15k limit. If shader runs black, reduce to 40 steps (12,800 iterations).

### Fiber Overlap Visibility
**Risk**: 8 fibers with transparency might muddy colors in dense regions
**Mitigation**: 0.85 transparency factor and exponential alpha proven to work at 7.5/10

### Quaternion Precision
**Risk**: Quaternion computation errors could distort circles
**Mitigation**: Using MANDATORY formula exactly as specified, mediump float sufficient for visible geometry

### Edge Cases
- **Behind camera**: Ray origin behind geometry → no contribution (correct)
- **Singularity at q.w=1**: Offset 0.35 prevents division issues
- **Segment wrapping**: Use `(seg+1) % 40` for last segment

## Visual Prediction

### Expected Output
- **Structure**: 8 interlocking colored fiber circles in 3D space, clearly distinct from each other
- **Topology**: Fibers should never intersect, each forming closed loops that link through each other (Hopf fibration characteristic)
- **Color**: Vibrant rainbow spectrum across 8 fibers, high saturation
- **Depth**: Camera Y-offset of 1.5 gives three-quarter view, showing 3D structure clearly
- **Animation**: Slow orbital rotation reveals fiber relationships over time
- **Atmosphere**: Subtle glow halos create depth and visual cohesion

### Key Visual Verification
1. **Circles not blobs**: Correct quaternion formula produces circular fibers
2. **8 distinct fibers**: Should count 8 separate colored loops
3. **No intersections**: Fibers link but don't cross (topological correctness)
4. **Smooth curves**: 40 segments should appear smooth, not faceted
5. **Good contrast**: Dark background, bright fibers with glow
6. **Central clustering**: Fibers concentrated near origin due to stereographic projection

### Success Criteria
- Recognizable as Hopf fibration (linked circles)
- Visually engaging (color, depth, glow)
- Mathematically correct (topology preserved)
- Performance acceptable (renders without timeout)
- Target: 7-9/10 range by combining all proven patterns
