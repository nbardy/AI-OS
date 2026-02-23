# Round Analysis

## What Worked (and WHY)

### Candidate 2 (5/10) — Best of Round

**Technique chain:** 8 fibers (4 shells x 2 rotations), correct Hopf quaternion form, 960-float flat array inside main(), post-projection scale 0.85, glow halo, 85% transparency factor, check-before-step ray march order.

**Visual result:** Judge described "a twisted rainbow ribbon forming an hourglass or figure-8 shape" with "colors cycle smoothly through the spectrum." The structure was recognizable as topologically related to fiber bundles.

**Why it scored highest (but still only 5/10):**
- The correct quaternion parametrization (`q = (cos(phi/2)cos(theta), cos(phi/2)sin(theta), sin(phi/2)cos(theta), sin(phi/2)sin(theta))`) produced coherent fiber geometry. This is the same form that scored 7.5/10 in prior rounds.
- Shell angles at pi/8, pi/4, 3pi/8, pi/2 with rotations at 0 and pi/2 produced distinguishable fibers.
- Glow halo (`dist < tubeRadius * 1.5`) and transparency (`alpha *= 0.85`) added atmosphere.
- Camera at distance 4.5 with elevation 1.5, check-before-step order.

**Why only 5/10 (regression from prior 7.5/10):**
- Judge called it "a simple twisted ribbon" rather than "interlocking colored rings." The structure read as a single parametric shape rather than multiple linked circles.
- Composition score 5/10: "Centered but static. The form is isolated in the middle."
- Complexity/Interest score 4/10: "Too simple. Essentially a twisted ribbon."
- The judge specifically noted the absence of "interlocking circles or tori in S3 projected to 3D space."

**Key question:** Why did essentially the same shader that scored 7.5/10 in a prior round score only 5/10 here? Possible causes:
1. Different judge calibration between rounds (likely — the critique style is notably harsher this round)
2. The camera angle at the specific u_time value when the screenshot was taken may have presented a less favorable viewing angle
3. The elevation calculation differs subtly: Candidate 2 uses `camDist * cos(angle) * cos(elevation)` with elevation as a constant 1.5 radians, which produces `cos(1.5) = 0.07` — this means the camera is nearly at the pole, looking almost straight down. This dramatically flattens the 3D structure into what appears as a 2D ribbon.

**ROOT CAUSE IDENTIFIED:** The camera elevation parameter is being used as a fixed angle (1.5 radians = 86 degrees above the XZ plane), NOT as a Y-offset. `cos(1.5) ≈ 0.07` collapses the horizontal camera orbit to a tiny circle near the Y axis. The camera is essentially looking straight down, destroying the 3D perspective that made prior rounds score well.

Compare:
- **Prior round winner (7.5/10):** Camera at `vec3(4.5 * cos(angle), 1.5, 4.5 * sin(angle))` — elevation is a Y OFFSET, camera orbits in the XZ plane at Y=1.5
- **This round's Candidate 2:** Camera at `vec3(camDist * cos(angle) * cos(elevation), camDist * sin(elevation), camDist * sin(angle) * cos(elevation))` — elevation is an ANGLE in spherical coordinates, camera orbits near the top of a sphere

This is the critical difference. The spherical coordinate form with elevation=1.5 rad places the camera at Y = 4.5 * sin(1.5) = 4.49, X ≈ 0.32 * cos(angle), Z ≈ 0.32 * sin(angle). The camera is almost directly above, orbiting in a tiny circle of radius 0.32. This overhead view makes the 3D fiber structure appear as a flat 2D ribbon.

### Candidate 1 (3/10) — Marginal

**Technique chain:** Same correct quaternion form, same 960-float array, same parameters as Candidate 2.

**Why it scored lower:** Judge described it as "small, twisted rainbow ribbon floating in the center of a black void." Despite using identical mathematical structure, the rendered result appeared even simpler.

**Difference from Candidate 2:** Candidate 1 uses `float shellAngles[4] = float[4](...)` and `float rotations[2] = float[2](...)` — GLSL ES array initializer syntax that may not compile on all platforms. If this compiled, the shader is mathematically identical to Candidate 2 except for the camera: Candidate 1 uses the Y-offset camera form `vec3(4.5 * cos(angle), 1.5, 4.5 * sin(angle))`.

**Contradiction:** Candidate 1 uses the "good" camera form but scored LOWER (3/10 vs 5/10). This means the camera isn't the only differentiator. The GLSL ES array initializer syntax may have caused a partial compilation failure, or the specific u_time value at screenshot time showed an unfavorable angle. Alternatively, the judge may have been harsher on the second review.

## What Failed (and WHY)

### Candidate 0 (2/10) — Small Torus, Lost in Void

**Root cause: Camera elevation as angle (same as Candidate 2).**

Candidate 0 uses the Y-offset camera form: `vec3(camDist * cos(camAngle), camElev, camDist * sin(camAngle))` with `camElev = 1.5`. This should produce good results — it's the same camera as the prior 7.5/10 winner.

**Why it scored only 2/10:**
- Only 6 fibers (3 shells x 2 rotations) instead of 8. Fewer fibers = less visible interlocking structure.
- Shell angles at pi/6, pi/3, pi/2 (wider spacing) vs pi/8, pi/4, 3pi/8, pi/2 (denser spacing in prior winner).
- Rotations at 0 and pi (not 0 and pi/2). The pi offset means fibers in each shell are diametrically opposite — they overlap when viewed from certain angles, reducing apparent complexity.
- Tube radius 0.13 (slightly larger than proven 0.11) — thicker tubes blur fine structure.
- Added animated hue (`fract(baseHue + u_time * 0.1)`) — TIER 3 experiment that may have confused the judge or produced less distinct fiber colors.

**Key factor:** The judge saw "a small, colorful toroidal shape" with "no visual tension." The combination of fewer fibers, wider spacing, and pi-offset rotations produced a simpler visual that failed to demonstrate the Hopf fibration's characteristic interlocking structure.

### Candidate 4 (2/10) — Exploratory Goal, Ribbon Approach Failed

**Root cause: Ribbon SDF implementation error.**

The exploratory goal was ambitious: "Hopf Fibers as Luminous Moebius Ribbons" — render fibers as flat ribbons instead of round tubes. The shader attempted:
1. Store positions AND normals (6 floats per segment, 960 total)
2. Use box-cross-section distance instead of circular tube distance
3. Orientation-dependent brightness via `abs(dot(ribbonNormal, rayDir))`

**Why it produced a "single vertical orange-red cylindrical form":**

The ribbon distance calculation on lines 127-131 is:
```glsl
float normalDist = abs(dot(residual, interpNormal));
float ribbonDist = max(dist - 0.12, normalDist - 0.02);
```

Problem: `dist` here is the full 3D distance to the centerline, not the tangent-plane component. For a ribbon SDF, you need to decompose the residual into:
1. Component along the ribbon normal (thickness direction)
2. Component along the ribbon binormal (width direction)
3. Component along the tangent (should be zero after closest-point projection)

Instead, Candidate 4 uses `dist` (full radial distance) minus 0.12, which creates a hollow cylinder of radius 0.12, then intersects with a slab of thickness 0.02. The intersection of a cylinder and a slab is NOT a ribbon — it's two small lens-shaped regions at the top and bottom of the cylinder.

Additionally, the `normalize(cross(tangent, vec3(0,1,0)))` normal computation degenerates when the tangent is near vertical. The fallback check `if (length(ribbonNormal) < 0.1)` uses the result of `normalize()`, which always has length 1.0 (or is NaN for zero input). The fallback never triggers. For fibers with near-vertical tangents, ribbonNormal is NaN, and all subsequent calculations produce NaN or zero.

**Combined effect:** Broken SDF + degenerate normals → most fibers invisible, surviving geometry renders as a single blob.

### Candidate 3 (1/10) — Nearly Invisible, Dark Render

**Root cause: Camera elevation as spherical angle + depth attenuation producing near-zero brightness.**

Candidate 3 uses:
```glsl
vec3 camPos = vec3(
    camDist * cos(camAngle) * cos(camElevation),  // X ≈ 4.5 * cos(t) * 0.07
    camDist * sin(camElevation),                    // Y ≈ 4.5 * 0.997 = 4.49
    camDist * sin(camAngle) * cos(camElevation)     // Z ≈ 4.5 * sin(t) * 0.07
);
```

With `camElevation = 1.5` (radians), this places the camera almost directly above (Y=4.49, XZ radius ≈ 0.32). Combined with `exp(-0.5 * rayDepth)` depth attenuation where rayDepth starts at ~4.5 (camera distance), the initial brightness multiplier is `exp(-2.25) ≈ 0.10`. The fibers render at only 10% brightness.

Additionally, only 4 fibers (2 tori x 2 fibers) provide very sparse geometry. With the camera nearly overhead and 10% brightness, the result is "nearly black canvas with two extremely faint, twisted ribbon-like shapes."

**Dual failure mode:**
1. Spherical-coordinate camera with 1.5 rad elevation ≈ overhead view (geometry flattened)
2. Depth-based attenuation `exp(-0.5 * rayDepth)` aggressively dims everything (camera is 4.5 units away → 10% brightness)

The depth attenuation was meant to create "over-under" weave effects at fiber crossings, but it attenuated EVERYTHING, not just occluded fibers.

## Patterns

### 1. Camera Elevation Bug is the Round's Dominant Failure Mode

Three of five candidates (0 excluded, 1 excluded) used spherical-coordinate camera with elevation=1.5 radians, producing a near-overhead view. This is the single biggest cause of score regression from prior rounds. The proven camera form is:
```glsl
vec3 camPos = vec3(camDist * cos(angle), elevationOffset, camDist * sin(angle));
```
Where `elevationOffset` is a Y POSITION (1.5 meters above origin), NOT an angle.

**Candidates 2 and 3** explicitly used `cos(elevation)` and `sin(elevation)` with elevation=1.5 rad, producing the overhead camera.
**Candidate 4** also used elevation as an angle but with a different structure.
**Candidates 0 and 1** used the correct Y-offset form.

### 2. Every Candidate Used the Correct Hopf Quaternion Form

Unlike prior rounds where quaternion bugs caused blob/torus failures, ALL five candidates this round used the correct `q = (cos(phi/2)cos(theta), cos(phi/2)sin(theta), sin(phi/2)cos(theta), sin(phi/2)sin(theta))` form. The tiered guidance successfully eliminated this class of error.

### 3. Exploratory Goals Underperformed Iterative Goals

- Iterative candidates: 5/10, 3/10, 2/10 (avg 3.3)
- Exploratory candidates: 2/10, 1/10 (avg 1.5)

The two exploratory candidates (4: ribbons, 3: interlocked Clifford tori) attempted novel rendering techniques that introduced new bugs. The iterative candidates stuck to proven tube rendering and scored higher despite not innovating.

### 4. Scores Across the Board are Lower Than Prior Rounds

Best this round: 5/10. Prior best: 7.5/10. Even the candidates reusing proven techniques scored lower. This suggests either:
- Judge calibration shift (harsher critique)
- Screenshot timing (unfavorable camera angles captured)
- Camera elevation bugs in top candidates (confirmed for Candidates 2, 3)

### 5. Glow + Transparency Insufficient Without Good Camera

Candidates 1 and 2 both had glow halos and transparency (the techniques that boosted prior rounds to 7.5/10) but scored 3/10 and 5/10. The camera view angle is more impactful than rendering refinements. A bad viewing angle makes all rendering improvements moot.

## Root Causes

### Primary: Camera Configuration Errors (Affects 3/5 Candidates)

The spherical coordinate camera with `elevation = 1.5 rad` is a persistent trap. It looks reasonable in code but places the camera overhead, destroying the 3D perception that makes Hopf fibrations visually compelling. The tiered guidance specified "External camera >= 4.0 from origin" but did NOT specify the camera POSITION pattern precisely enough.

**Fix for guidance:** Add explicit camera position formula as MANDATORY: `vec3(dist * cos(angle), offsetY, dist * sin(angle))` where offsetY is a small constant (1.0-2.0), NOT an angular parameter.

### Secondary: Exploratory Techniques Introduce New Bug Classes

Candidate 4's ribbon SDF and Candidate 3's depth attenuation each introduced new failure modes not covered by existing guidance. Exploratory goals are valuable for breaking past plateaus, but they need tighter implementation constraints.

**Fix for guidance:** Experimental rendering techniques should be constrained to ONLY modify the color/compositing stage, not the geometry representation or distance computation, which are proven and fragile.

### Tertiary: Diminishing Returns on Iterative Refinement

The iterative candidates faithfully reproduced the prior round's best techniques but scored lower. Without novel visual elements (composition, palette, structure), the same visual output plateaus or regresses as judge expectations increase.

**Fix for guidance:** Next round should focus on structural novelty (more fibers, different fiber families, animation) rather than rendering refinement (glow, transparency, tube radius).
