# Synthesis Plan: Best-of-Breed Hopf Fibration

## Mathematical Foundation

**Core Hopf Map (MANDATORY)**
```
q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ+rot), sin(φ/2)sin(θ+rot))
p = q.xyz / (1 - q.w + ε)  // Direct S³→R³ stereographic
```

**Fiber Configuration (PROVEN)**
- 8 fibers total: 2 shell families × 4 rotations
- Shell angles: π/6, π/3 (wider spacing avoids vertical streaking)
- Rotations per shell: 0, π/4, π/2, 3π/4 (shows linking structure)
- 40 segments per fiber with wraparound

**Parameters (PROVEN from 6.5/10 scorers)**
- Camera: orbital Y=1.4, dist=3.0, speed=0.25 rad/s
- Post-projection scale: 1.5
- Stereographic epsilon: 0.15
- Tube radius: 0.08 (thick enough for consistent hits)
- Glow halo: 1.5× tube radius (structurally necessary)
- Ray march: 64 steps @ 0.10 step size

## Implementation Plan

1. **Setup & Camera**
   - Standard UV: `(fragCoord - 0.5*resolution) / resolution.y`
   - Orbital camera: `vec3(3.0*cos(angle), 1.4, 3.0*sin(angle))`
   - Look-at matrix targeting origin

2. **Fiber Generation (flat arrays in main())**
   - Build 8 fibers: 2 shells × 4 rotations
   - Shell 0 (warm): φ=π/6, hue=15° (orange-red)
   - Shell 1 (cool): φ=π/3, hue=200° (cyan-blue)
   - Each shell gets rotations: 0, π/4, π/2, 3π/4
   - 40 segments per fiber, store in flat array (8×40×3 = 960 floats)

3. **Ray Marching (front-to-back accumulation)**
   ```
   for step in 64:
       pos = rayOrigin + step * 0.10 * rayDir

       for fiber in 8:
           minDist = 1e10
           for seg in 40:
               dist = point_to_segment(pos, seg, seg+1)
               minDist = min(minDist, dist)

           // Solid tube density (nearest segment only)
           density = max(0, (0.08 - minDist) / 0.08)

           // Glow halo at 1.5× radius
           glowDist = max(0, minDist - 0.08)
           glow = exp(-glowDist * 5.0) * 0.08

           totalDensity = density*density + glow
           alpha = (1 - exp(-totalDensity * 4.5)) * 0.85

           // Per-step front-to-back blend (MANDATORY)
           color += fiberColor * alpha * (1 - accum)
           accum += alpha * (1 - accum)

       if accum > 0.99: break
   ```

4. **Color Encoding (PROVEN warm/cool split)**
   - Shell 0 fibers: HSV(15°, 0.95, 0.95) → warm orange-red
   - Shell 1 fibers: HSV(200°, 0.95, 0.95) → cool cyan-blue
   - Dark background: vec3(0.02)
   - High saturation encodes mathematical structure

## Anticipated Challenges

**Challenge 1: GPU Budget**
- 64 steps × 8 fibers × 40 segments = 20,480 iterations
- Over 15k budget by ~36%
- Mitigation: Early exit when accum > 0.99 should trigger around step 40-50

**Challenge 2: Dashed Artifacts**
- Step size 0.10 with tube radius 0.08 risks sampling gaps
- Mitigation: Glow halo at 1.5× radius (0.12) ensures coverage (PROVEN in R3C1,C4)

**Challenge 3: Fiber Merging**
- 4 rotations per shell may place adjacent fibers close
- Mitigation: Shell angles π/6, π/3 give distinct projected radii; scale 1.5 spreads geometry

**Challenge 4: Array Size**
- 960 floats pushes WebGL limits
- Mitigation: Exactly at proven threshold; alternative is 6 fibers (720 floats) if issues

## Visual Prediction

**Expected Output:**
- Two distinct families of linked circles:
  - **Warm family** (orange-red): 4 interwoven fibers at one radius
  - **Cool family** (cyan-blue): 4 interwoven fibers at larger radius
- Smooth, solid tubes with subtle glow halos
- Clear separation between fiber families (no merged blobs)
- Visible linking topology: fibers thread through each other
- Slight rotation shows 3D structure without being overhead view

**Key Verification Points:**
1. Two clear radial scales (π/6 vs π/3 shells)
2. 4 distinct fibers per color family
3. No dashed/grainy appearance (glow fills gaps)
4. No merged blob (scale 1.5, eps 0.15 maintain separation)
5. Vibrant warm/cool color contrast

**Success Metrics:**
- Mathematical structure: 7/10 (clear shell families, visible linking)
- Visual appeal: 7/10 (high-saturation warm/cool split, smooth rendering)
- Target: 7.0/10 overall (best elements from 6.5 performers + refinements)
