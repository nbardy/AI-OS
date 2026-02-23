# Round Analysis

## What Worked (and WHY)

### Nothing Scored Above 1/10

This is a total wipeout. All 5 candidates scored 1/10. No candidate produced visible, recognizable Hopf fibration geometry. This is a catastrophic regression from R0 (best 5/10) and prior rounds (best 7.5/10).

The fact that ALL candidates failed — including the baseline (Candidate 0) that reuses the prior 7.5/10 template nearly verbatim — strongly suggests a **systemic rendering pipeline failure** rather than shader logic errors. The shaders themselves may be mathematically correct but are not producing visible output due to an execution environment issue.

## What Failed (and WHY)

### Candidate 0 (Baseline) — 1/10: Black Screen

**Shader analysis:** This candidate is structurally almost identical to the prior 7.5/10 winner:
- Correct Hopf quaternion form
- 8 fibers (4 shells x 2 rotations) with shells at pi/8, pi/4, 3pi/8, pi/2
- Rotations at 0 and pi/2
- Y-offset camera: `vec3(camDist * cos(camAngle), 1.6, camDist * sin(camAngle))`
- Camera distance 4.5, check-before-step ray march
- Tube radius 0.11, glow halo, quadratic density, exponential alpha

**Judge report:** "Completely black with no visible content."

**Root cause hypothesis:** The camera setup uses `vec3 rayDir = normalize(vec3(uv, -1.5))` as the initial ray direction in screen space, then rotates it via the camera basis. The `forward` vector is `normalize(-camPos)`, `right` is `cross(vec3(0,1,0), forward)`, and `up` is `cross(forward, right)`. This is the standard camera rig.

However, the ray march uses a **fixed step size of 0.08** for **80 steps**, giving a maximum ray travel of 6.4 units. With the camera at distance 4.5 from the origin, the geometry occupies roughly a 2-3 unit radius sphere around the origin. The ray needs to travel approximately 4.5 - 3.0 = 1.5 units minimum to reach the near geometry, and up to 4.5 + 3.0 = 7.5 units to the far side. The maximum ray travel of 6.4 should reach most geometry.

**More likely root cause:** The ray march iterates over ALL 8 fibers x 40 segments = 320 segment checks PER step, for 80 steps = 25,600 total segment-distance evaluations per pixel. This is an extremely heavy shader. On resource-constrained GPU environments, this may:
1. Hit a GPU timeout (shader execution time limit)
2. Fail to compile due to loop unrolling limits in GLSL ES
3. Silently produce zero output when the driver kills the shader

The `distanceToSegment` function is called 320 times per step. In GLSL ES, the inner loops `for (int fib = 0; fib < 8; ...)` and `for (int seg = 0; seg < 40; ...)` may need to be fully unrolled by the compiler. That's 320 iterations of a non-trivial function body — many GLSL ES implementations have loop iteration limits (often 256 or 512 for the total of nested loops).

**Alternative root cause:** The shader declares `float fiberData[960]` inside `main()`. This allocates 960 floats (3,840 bytes) on the stack. Many GLSL ES implementations have strict stack/local variable limits. If the driver silently fails this allocation, `fiberData` contains uninitialized garbage (likely zeros), and all fiber positions are at the origin — creating a degenerate point instead of curves.

### Candidate 1 (Iterative) — 1/10: Flat Orange Field

**Shader analysis:** Uses the same mathematical structure as Candidate 0 but with a different Hopf map approach. After computing the quaternion `q`, it computes an explicit Hopf map `S³ → S²`:
```glsl
float X = 2.0 * (q.x * q.y + q.z * q.w);
float Y = 2.0 * (q.y * q.z - q.x * q.w);
float Z = q.x * q.x - q.y * q.y - q.z * q.z + q.w * q.w;
```
Then stereographically projects from S² to R³:
```glsl
float denom = 1.0 - Z + 0.35;
vec3 p3d = vec3(2.0 * X / denom, 2.0 * Y / denom, (1.0 + Z) / denom);
```

**Root cause:** This is a **mathematical error**. The Hopf fibration maps S³ → S² → fiber circles. The code projects the *base point on S²* stereographically, not the *fiber point on S³*. This maps each quaternion to a point on S², then projects that S² point — producing a 2-manifold (sphere surface), not a fiber circle. All 40 samples along a fiber (varying theta) may map to the same or very nearby S² points, collapsing the fibers to degenerate geometry.

Additionally, the SDF computation uses `float sdf = abs(minDist - tubeRadius)` — this creates a hollow shell at exactly `tubeRadius` distance from the fiber. The density is `sdf * sdf` which is ZERO when `minDist == tubeRadius` and grows as you move away from that exact shell radius. Combined with `1 - exp(-density * 4.5)`, this produces maximum alpha AWAY from the fibers, not at them. The rendering logic is inverted — it colors the background instead of the geometry.

**Combined effect:** Degenerate geometry (S² projection instead of S³ fibers) + inverted density function (shell at tube radius) = uniform orange field. The entire screen is "near" degenerate fiber geometry (all collapsed to points/lines), and the inverted density colors everything uniformly.

### Candidate 2 (Iterative) — 1/10: Flat Cyan Field

**Shader analysis:** Similar to Candidate 1 but uses direct stereographic projection of S³ (the correct approach):
```glsl
vec3 p = vec3(2.0 * q.x, 2.0 * q.y, 2.0 * q.z) / (1.0 - q.w + singularity);
```

However, it uses the **same inverted SDF** as Candidate 1:
```glsl
float sdf = abs(minDist - tubeRadius);
float density = sdf * sdf;
```

**Root cause:** The `abs(minDist - tubeRadius)` creates a hollow tube shell, and `density = sdf * sdf` means density is ZERO at the tube surface and increases as you move away. With `alpha = 1.0 - exp(-density * 4.5)` and `alpha *= 0.85`, the alpha is zero AT the fibers and high EVERYWHERE ELSE.

This is the same inverted-density bug as Candidate 1. Every pixel is assigned the color of the nearest fiber (cyan from the closest fiber's HSV), with high alpha everywhere in space except right at the fibers. Result: uniform color field.

### Candidate 3 (Exploratory) — 1/10: Black Screen

**Shader analysis:** Implements the "Trefoil-Linked Fiber Triptych" with 6 fibers using longitude offsets. The novel element is phase-shifted glow where brightness pulses along fibers.

**Root cause:** The density accumulation is fundamentally broken. The inner loop accumulates density for ALL fiber segments at every ray step:
```glsl
for (int f = 0; f < 6; f++) {
    for (int seg = 0; seg < 40; seg++) {
        float contrib = exp(-dist * dist * 50.0) * pulse;
        totalDensity += contrib;
        colorAccum += fiberColors[f] * contrib;
    }
}
```

This runs 240 iterations per ray step (6 fibers x 40 segments). With 64 ray steps, that's 15,360 density contributions accumulated into `totalDensity`. Even if each contribution is small (say 0.001 when far from geometry), after 15,360 accumulations totalDensity reaches ~15.4, making `alpha = 1 - exp(-15.4 * 4.5)` ≈ 1.0. The color is `colorAccum / totalDensity`, which is an average of all fiber colors — but alpha hits 1.0 almost immediately.

Additionally, the early exit condition `if (minDist > 2.0) break` will trigger on the FIRST step if the camera starts more than 2.0 units from any fiber — which it does, since the camera is at distance 4.5. This exits the ray march after exactly one step, with negligible accumulated density. Result: near-zero alpha → pure background color → black.

**Combined failure:** Early exit prevents ray marching into geometry. Even if it didn't exit early, the accumulation model is broken (sums ALL segment contributions at every step, not just the nearest).

### Candidate 4 (Exploratory) — 1/10: Tiny Cyan Crescent

**Shader analysis:** Implements "Nested Villarceau Circles with Chromatic Depth Separation" — 8 fibers on two tori with depth-to-hue color mapping.

**Root cause:** Uses a helper function `hopfFiber()` defined outside `main()`. This is not inherently wrong in GLSL ES, but the function applies the longitude rotation differently:
```glsl
float t = theta + rotation;
vec4 q = vec4(cp2 * cos(t), cp2 * sin(t), sp2 * cos(t), sp2 * sin(t));
```

This applies `rotation` as a simple offset to theta, which means the third and fourth quaternion components ALSO use `theta + rotation` (not `theta + xi1` independently for the S² base point offset). This changes the mathematical meaning — it rotates the fiber in S³ rather than selecting a different base point on S². For certain rotation values, this may collapse fibers onto each other.

Additionally, the UV setup uses `vec2 uv = (gl_FragCoord.xy * 2.0 - u_resolution.xy) / u_resolution.y` — this maps the screen to [-aspect, aspect] x [-1, 1] with a factor of 2 PLUS the standard centering. The typical formula is `(gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y`. The factor of 2 doubles the field of view, making the projected geometry appear half-sized and potentially pushing it outside the visible frustum for most viewing angles.

**Also:** The ray march runs 160 steps with step size 0.05, checking 8 fibers x 40 segments = 320 distance evaluations per step = 51,200 total per pixel. This exceeds likely GPU shader execution limits.

**Combined effect:** Halved apparent geometry size from doubled UV range + collapsed fiber positions from wrong rotation application + GPU limits = only a tiny crescent fragment visible.

## Patterns

### 1. TOTAL SYSTEM FAILURE: All 5 Candidates at 1/10

This has never happened before. The prior round had scores of 2, 3, 5, 2, 1 — at least one candidate was partially visible. This round, NOTHING rendered correctly.

### 2. The Inverted Density Bug (Candidates 1 and 2)

Both iterative candidates used `abs(minDist - tubeRadius)` as their SDF, then computed `density = sdf * sdf`. This is a **hollow shell SDF** — it measures distance FROM the tube surface, not distance from the tube interior. Density is zero at the surface and grows outward. This is the opposite of what tube rendering requires (density should be maximum at the center and decrease toward the surface).

The correct formula (used by the prior 7.5/10 winner and Candidate 0 this round) is:
```glsl
if (minDist < tubeRadius) {
    float d = (tubeRadius - minDist) / tubeRadius;  // 1 at center, 0 at surface
    float density = d * d;
}
```

### 3. GPU Execution Limits Are Likely a Hidden Factor

Candidates 0, 3, and 4 have correct-enough math to produce SOMETHING, yet produced black screens or tiny fragments. The common factor is extreme computational load:
- 8 fibers x 40 segments = 320 distance checks per ray step
- 64-160 ray steps
- Total: 20,480 to 51,200 distance evaluations per pixel

GLSL ES on many implementations (especially WebGL/software renderers) has loop iteration limits, execution time limits, or instruction count limits. Shaders that exceed these silently produce zero output.

### 4. Mathematical Variant of Hopf Projection (Candidate 1)

Candidate 1 introduced a novel S³ → S² → R³ two-step projection that is mathematically incorrect for fiber visualization. This is a new failure class not seen before. The fiber structure lives in S³; projecting to S² first loses the fiber circles (they map to points on S²).

### 5. All Mandatory Constraints Were Followed (Superficially)

Every candidate used:
- Correct quaternion form (or close to it)
- Y-offset camera (not spherical)
- Flat arrays inside main()
- Post-projection scale 0.85
- distanceToSegment function
- Tube radius ~0.11

Yet all failed. The TIER 1 constraints prevent known bad patterns but don't prevent new failure classes: inverted density, GPU limits, wrong projection path, broken accumulation models.

## Root Causes

### Primary: Shader Complexity Exceeds GPU Execution Limits

The fundamental architecture of "march rays through space, check distance to every segment of every fiber at every step" creates O(steps × fibers × segments) workload per pixel. At 80 steps × 8 fibers × 40 segments = 25,600, this is at or beyond the execution capacity of many GLSL ES implementations. The prior 7.5/10 winner may have run on a different GPU/driver or with a simpler step count.

**Recommended action:** Reduce total work per pixel:
- Use fewer ray steps (32-48 instead of 64-160)
- Use fewer segments (20-24 instead of 40) — still enough for smooth circles
- Use adaptive step size (larger steps when far from geometry)
- Or reduce to 4-6 fibers to keep the inner loop tractable
- Target: total iterations per pixel < 10,000

### Secondary: Inverted Density Function (New Bug Class)

The `abs(minDist - tubeRadius)` pattern crept into Candidates 1 and 2, producing the opposite of the intended rendering. This is a subtle bug — the formula looks plausible but creates a hollow shell instead of a solid tube.

**Recommended action:** Add to TIER 1 mandatory: "Tube density must be `(tubeRadius - minDist) / tubeRadius` inside the tube, NOT `abs(minDist - tubeRadius)`."

### Tertiary: Accumulation Model Errors (Candidate 3)

Candidate 3's approach of summing density from ALL segments at every step (instead of using only the nearest segment's distance) causes runaway accumulation. This is a fundamental misunderstanding of volumetric rendering.

**Recommended action:** Add to TIER 1: "Only the nearest segment contributes to density at each ray position."

### Quaternary: Wrong Projection Path (Candidate 1)

The S³ → S² → R³ projection path loses fiber geometry. The correct path is S³ → R³ (direct stereographic).

**Recommended action:** Add to DEPRECATED: "S³ → S² → R³ two-step projection."

### Meta-Observation: The Evolution Process Regressed

Round 0 scored up to 5/10. Round 1 scored all 1/10. The tiered guidance grew more detailed but the output quality collapsed. This suggests the LLM generating shaders may be:
1. Over-constraining itself with "MANDATORY" tags, producing rigid but broken code
2. Introducing new patterns (inverted SDF, accumulation sums) that aren't covered by existing rules
3. Hitting a complexity ceiling where the shaders are too computationally expensive to run

The process needs to **simplify aggressively**: fewer fibers, fewer segments, fewer ray steps, simpler rendering. Get a visible output first, then add complexity incrementally.
