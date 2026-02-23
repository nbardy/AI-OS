# Hopf Fibration Shader - Synthesis Plan

## Mathematical Foundation

### Core Hopf Map (MANDATORY)
- **S³ Quaternion**: `q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ), sin(φ/2)sin(θ))`
  - φ = shell angle (π/6, π/3, π/2 for wide spacing)
  - θ = fiber parameter [0, 2π]
- **Direct Stereographic Projection**: `p = q.xyz / (1 - q.w + ε)` where ε = 0.12
  - NEVER use two-step S³→S²→R³
  - Lower epsilon (0.12 vs 0.35) for more natural spread
- **Post-Projection Scale**: 1.8× to maximize screen fill
  - Previous 0.85 caused "kidney bean blob"
  - 1.8 should spread fibers without pushing them off-screen

### Fiber Configuration (PROVEN)
- **6 fibers total**: 3 shells × 2 rotations
  - Shells: π/6, π/3, π/2 (wider spacing than π/8 progression)
  - Rotations: 0, π/2 (proven to avoid overlap)
- **40 segments per fiber** with wraparound: `next = (seg + 1) % 40`

### Camera Setup (MANDATORY)
- **Y-offset orbit camera**: `vec3(dist·cos(angle), 1.5, dist·sin(angle))`
  - Distance: 3.0 (closer than 4.5 to match larger post-scale)
  - Y-offset: 1.5 (proven sweet spot)
  - NEVER use spherical coordinates with elevation

## Implementation Plan

### 1. Data Generation (inside main())
```glsl
float fiberData[960]; // 6 fibers × 40 segments × 4 coords (xyz + hue)
int idx = 0;
for each shell angle phi in {π/6, π/3, π/2}:
  for each rotation rot in {0, π/2}:
    float hue = idx / 6.0  // Per-fiber color
    for each segment s in [0..39]:
      θ = 2π · s/40 + rot
      q = hopfQuaternion(phi, θ)
      p = stereographicProject(q, epsilon=0.12) × 1.8  // Key change
      fiberData[idx++..] = (p.xyz, hue)
```

### 2. Ray Marching
- **Setup**: Standard UV, ray from camera through pixel
- **Step size**: 0.10 (balance between quality and 48-step limit)
- **Max steps**: 48 (total work = 48 × 6 × 40 = 11,520 iterations < 15k limit)
- **Distance check BEFORE step**: Check hit at rayPos, then advance

### 3. Volume Rendering (PROVEN)
- **Tube radius**: 0.05 (thin to prevent merging)
- **Solid tube density**: `(0.05 - minDist) / 0.05` for nearest segment only
- **Quadratic accumulation**: `density² × stepSize`
- **Exponential alpha**: `1 - exp(-accum × 4.5)`
- **Glow halo**: `exp(-dist × 5.0) × 0.08` at 1.5× tube radius

### 4. Color & Transparency (PROVEN)
- **Per-fiber HSV**: `hsv2rgb(vec3(hue, 0.95, 0.95))`
- **Transparency factor**: 0.85 for fiber overlap visibility
- **Dark background**: `vec3(0.02)` for maximum contrast

## Anticipated Challenges

### Challenge 1: Singularity at q.w = 1
- **Solution**: Epsilon = 0.12 in denominator
- **Risk**: Lower than 0.35 (which over-compressed) but still safe
- **Validation**: Check no fibers escape view frustum

### Challenge 2: Fibers merging into blob
- **Root causes**: Scale too small (0.85), tubes too thick (0.11), shells too close
- **Solutions**:
  - Scale 1.8× (not 0.85×)
  - Tube radius 0.05 (not 0.11)
  - Shell spacing π/6, π/3, π/2 (wide jumps)

### Challenge 3: GPU budget
- **Limit**: 15,000 iterations/pixel
- **Current**: 48 steps × 6 fibers × 40 segments = 11,520 ✓
- **Margin**: 23% headroom for overhead

### Challenge 4: Camera distance vs scale balance
- **Previous failure**: dist=4.5 with scale=0.85 → "small form in void"
- **New balance**: dist=3.0 with scale=1.8
- **Validation**: Fibers should fill ~60% of screen height

## Visual Prediction

### Expected Output
- **Structure**: 6 distinct circular fiber loops in 3D space
  - 3 concentric "shells" visible from offset viewpoint
  - Each shell appears as 2 linked circles (from 2 rotations)
- **Color**: Smooth rainbow gradient across fibers
  - High saturation (0.95) vibrant hues
  - Each fiber maintains solid color identity
- **Linking**: Clear topological linking between fiber pairs
  - 0 and π/2 rotations should show orthogonal crossings
- **Depth**: Gentle brightness variation (farther = slightly dimmer)
- **Glow**: Soft halos around tubes for volume presence

### Key Verification Points
1. **No blob**: Individual fibers clearly separated
2. **Screen fill**: Structure occupies 50-70% of frame
3. **Distinct shells**: Can count 3 different radial scales
4. **Smooth curves**: No jagged/faceted segments
5. **Color variety**: 6 different vibrant hues visible

### What Success Looks Like
A mathematically accurate Hopf fibration where the geometric beauty is immediately visible: nested circular fibers linking in elegant 3D patterns, with enough spread to see the structure clearly but not so much that it fragments.

### Improvement Over Previous Rounds
- **vs R2 (3/10)**: 2.1× larger scale eliminates "kidney bean blob"
- **vs R1 (1-3/10)**: Correct solid tube density + direct projection
- **vs R0 (1-7.5/10)**: Y-offset camera ensures good viewing angle
- **vs Prior 7.5/10**: Same proven foundations, refined for R3 learnings
