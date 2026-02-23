# Round 4 Analysis

## Score Summary

| Candidate | Type | Score | Key Feature |
|-----------|------|-------|-------------|
| C0 | baseline | 5/10 | 6 fibers, 3 shells x 2 rotations, tube 0.065, camera Y=1.3, 48 steps |
| C1 | iterative | 7/10 | 6 fibers, 3 shells x 2 rotations, tube 0.07, warm/cool split, 60 steps |
| C2 | iterative | 1/10 | 8 fibers, 2 shells x 4 rotations, lookAt matrix camera, 64 steps |
| C3 | exploratory | 5.5/10 | 4 fibers Clifford torus, Fresnel edge term, precomputed segment arrays |
| C4 | exploratory | 4/10 | 4 fibers dual-latitude, depth fog, warm/cool split |

**Best: C1 at 7/10. Improvement from R3 best (6.5), but still below prior all-time best (7.5).**

---

## What Worked (and WHY)

### Candidate 1 (7/10): The iterative refinement that almost broke through

- **Technique**: 6 fibers at 3 shells (pi/6, pi/3, pi/2) with 2 rotations (0, pi) each. Tube radius bumped to 0.07 (from 0.06), glow radius at 1.5x = 0.105. 60 ray march steps at 0.10 step size. Warm/cool color split: shell 1-2 warm reds/oranges (hues 0.05-0.15), shell 3 cool cyans/blues (hues 0.55-0.65). Camera at Y=1.4, dist 3.0. All fibers parametrized inline with `hopfPoint()` function, no precomputed arrays.

- **Visual result**: "Interlocking curved ribbons or tubes in vibrant colors (cyan, yellow, orange, blue) arranged in a flowing, weaving pattern against a black background. The forms have a smooth, luminous quality with soft gradients that suggest depth and dimensionality."

- **Why it scored well**: Several factors combined:
  1. **Tube radius 0.07**: Slightly thicker than the R3 best (0.06), which improved sampling consistency. The judge noted "smooth, luminous quality" rather than the "grainy, stippled texture" seen in R3. This confirms the hypothesis from R3 analysis that 0.06 was too thin for 0.10 step size.
  2. **60 steps instead of 48**: More ray march coverage (6.0 units total vs 4.8), meaning more complete fiber visibility. Judge saw "flowing, weaving pattern" rather than "cut off at edges."
  3. **Warm/cool color split**: Color scored 8/10 — "Vibrant, complementary color palette (warm yellows/oranges against cool cyans/blues) creates visual pop." This confirms R3C4's finding that warm/cool split is effective.
  4. **Inline fiber computation**: The `hopfPoint()` function computed segments on-the-fly inside the ray march loop rather than precomputing into arrays. This worked within GPU budget: 60 steps x 6 fibers x 40 segments = 14,400 (under 15,000 limit).

- **Why it didn't break 7.5**: Judge critique identifies three specific weaknesses:
  1. "Limited complexity — Only 4-5 visible fiber loops" (the 3 shells x 2 rotations produced visible structure but still sparse)
  2. "Generic shader aesthetic — The soft glowing tubes against black background is a very common shader art trope"
  3. "Missing mathematical depth — The Hopf fibration has beautiful properties... that aren't fully exploited"
  The judge wants MORE fibers showing the dense linking structure, and MORE visual sophistication beyond basic glow tubes.

### Key insight from C1: The tube radius sweet spot is 0.07, not 0.06
R3's 0.06 tubes produced "grainy, stippled" artifacts. C1's 0.07 tubes produced "smooth, luminous quality." This 0.01 increase eliminated the dominant visual flaw of R3. The glow at 1.5x (0.105) covers the remaining sampling gaps. Combined with 60 steps, this is the best rendering quality achieved since the 7.5/10 prior.

---

## What Failed (and WHY)

### Candidate 2 (1/10): Complete render failure — gradient only

- **Root cause: `lookAt()` matrix camera construction returns transposed basis.** C2 used a custom `lookAt()` function that builds `mat3(xaxis, yaxis, zaxis)` — in GLSL, `mat3(a, b, c)` fills columns, so this creates a matrix where xaxis is column 0, yaxis is column 1, zaxis is column 2. But `rayDir = normalize(cam * vec3(uv, 1.5))` then computes `xaxis*uv.x + yaxis*uv.y + zaxis*1.5`. The problem: the `zaxis` (forward) is `normalize(target - eye)`, not the cross product result. The standard camera construction in all other candidates uses separate `forward`, `right`, `up` vectors and computes `rayDir = normalize(forward + right*uv.x + up*uv.y)`. C2's matrix approach swapped the `right` computation: `cross(up, zaxis)` instead of `cross(zaxis, up)` or `cross(vec3(0,1,0), forward)` — this flips the right vector, and combined with the FOV scaling `vec3(uv, 1.5)` (should be 1.0), rays point in wrong directions.

- **Secondary cause: 8 fibers x 40 segments x 64 steps = 20,480 iterations/pixel.** This exceeds the 15,000 GPU budget. Even if the camera worked, the shader likely timed out or was optimized away by the driver.

- **Lesson**: The `lookAt()` matrix approach is fragile in GLSL. Stick to explicit `forward/right/up` vector computation. The FOV factor in `vec3(uv, 1.5)` also differs from the standard `normalize(forward + right*uv.x + up*uv.y)` which uses an implicit FOV of ~90 degrees.

### Candidate 0 (5/10): Functional but chaotic and visually unstructured

- **Root cause: Parameter tweaks without structural improvement.** C0 is described as "baseline" and uses nearly identical parameters to R3C1 (the 6.5/10 candidate) with minor tweaks: tube 0.065 instead of 0.06, camera Y 1.3 instead of 1.5. Shell configuration uses 2 rotations (0, pi/2) instead of (0, pi).

- **Visual result**: "Colorful but mathematically vague; misses the elegant structure that defines a Hopf fibration." Judge saw "random intertwining curves" and "energy but somewhat chaotic."

- **Why it scored LOWER than R3C1 despite similar code**: Two differences hurt:
  1. **Rotations (0, pi/2) vs (0, pi)**: With rotation = pi/2, the second fiber in each shell is only 90 degrees offset, creating less visual separation than pi (180 degrees). The fibers appear "random" rather than clearly linked because the angular separation is too small.
  2. **Camera Y=1.3 vs Y=1.5**: Lower camera means more "looking across" the structure rather than slightly down on it. From this angle, the toroidal linking structure is less visible.
  3. **48 steps vs 60 (C1)**: Shorter ray march range = more fiber clipping.

- **Lesson**: Rotation spacing of pi (180 degrees) between fiber pairs within a shell is superior to pi/2 (90 degrees) for visual clarity. Larger rotations create visually distinct interlinked circles; smaller rotations create "adjacent tracks" that look chaotic.

### Candidate 3 (5.5/10): Fresnel concept invisible, dotted artifacts

- **Root cause: Only 4 fibers on a single Clifford torus shell.** C3 used eta = pi/4 with 4 rotations (0, pi/2, pi, 3pi/2), generating all fiber geometry into a precomputed `segments[480]` flat array. The Fresnel edge term was computed as `edgeBoost = mix(1.0, 2.5, pow(1.0 - abs(dot(rayDir, tangent)), 2.0))`.

- **Why Fresnel didn't help**: The judge saw "dotted/beaded texture along the curves" and "flat 2D strokes with uniform glow" — the Fresnel boost was overwhelmed by the fundamental sampling artifacts. With tube radius 0.06 and step size 0.10, the ray hits are so intermittent that the Fresnel modulation is invisible. You can't enhance the edge of something that's already a series of disconnected dots.

- **Why only 5.5/10**: Single-shell (pi/4) with 4 fibers is geometrically less interesting than 3-shell configurations. All fibers have the same projected radius, so there's no visual nesting or scale variation. The judge noted "too simple and unclear... too sparse."

- **Lesson**: Fresnel edge enhancement is DEPRECATED — it requires smooth, well-sampled tube surfaces to be visible, and the current ray march resolution doesn't provide that. It's a shading improvement that assumes a rendering quality we don't have yet. Also: single-shell 4-fiber configs score lower than multi-shell configs.

### Candidate 4 (4/10): Depth fog destroys visibility

- **Root cause: Fog factor `exp(-t * 0.3)` is far too aggressive.** At camera distance 3.0, the nearest geometry is at t ≈ 1.0-2.0, where fog factor = 0.74-0.55. The far side of the structure at t ≈ 4.0-5.0 gets fog factor 0.30-0.22, losing 70-78% of brightness. The result: everything is dim, and far geometry is nearly invisible.

- **Visual result**: "Quite blurry and lacks definition... extremely heavy-handed... making everything muddy rather than enhancing spatial understanding." The judge specifically called out the fog as the biggest problem.

- **Secondary cause: Only 4 fibers total.** Two families of 2 fibers each (Family A at pi/6, Family B at pi/3) is too sparse. The inner pair (pi/6) projects to a very small radius — potentially too small to be visually significant at camera distance 3.0 with scale 1.5.

- **Lesson**: Depth fog at `exp(-0.3*t)` is far too aggressive. If fog is attempted, use `exp(-0.05*t)` or less — a subtle 5-15% darkening at maximum depth, not 70%+. But more importantly, 4 fibers is too few — the R4C1 success at 7/10 used 6 fibers (3 shells x 2 rotations), and the judge still wanted MORE. Going to 4 fibers is a regression.

---

## Patterns

### 1. Tube Radius 0.07 Eliminates the Grainy Artifact Problem
This is the biggest finding of R4. C1 (0.07, 7/10) vs C3 (0.06, 5.5/10) — both use the same step size (0.10) and glow approach. C1 has "smooth, luminous quality" while C3 has "dotted/beaded texture." The 0.01 increase from 0.06 to 0.07 means the tube diameter (0.14) exceeds the step size (0.10), guaranteeing at least one hit per tube crossing. This is a simple, reliable fix for the dominant R3 artifact.

### 2. The Score Plateau is About Fiber Density, Not Rendering Quality
C1 achieved clean rendering (no artifacts, smooth tubes, good colors) but still only scored 7/10. The judge's main critique: "Only 4-5 visible fiber loops... limited complexity." The next score breakthrough requires MORE fibers — at least 8-10 — showing the dense linking structure of the Hopf fibration. The rendering quality is now sufficient; the mathematical content is the bottleneck.

### 3. Inline Fiber Computation Works and Saves Array Budget
C1 computes Hopf points inline via `hopfPoint()` rather than precomputing into arrays. This avoids the 960-float array limit and the complexity of managing flat array indices. Budget: 60 x 6 x 40 = 14,400 < 15,000. The inline approach is cleaner and equally performant.

### 4. Multi-Shell Configurations Consistently Outperform Single-Shell
- Multi-shell (pi/6, pi/3, pi/2): C1 = 7/10, R3C1 = 6.5/10
- Single-shell (pi/4): C3 = 5.5/10
- Dual-shell (pi/6, pi/3): C4 = 4/10 (but fog killed it)

Three distinct shells with wide angular spacing produce the most visually interesting and mathematically clear structures.

### 5. Camera Formulation Must Be Simple
C2's `lookAt()` matrix approach failed completely (1/10). All successful candidates (C0, C1, C3, C4) use the explicit `forward = normalize(target - eye); right = normalize(cross(up_world, forward)); up = cross(forward, right); rayDir = normalize(forward + right*uv.x + up*uv.y)` pattern. This should be a mandatory template.

### 6. Rotation Spacing Matters for Visual Clarity
C0 used rotation spacing pi/2 (90 degrees) → 5/10, "chaotic." C1 used rotation spacing pi (180 degrees) → 7/10, "flowing, weaving pattern." Larger angular separation between fibers within a shell produces clearer linking structure. With 2 rotations per shell, pi spacing is optimal (maximally separated on S1).

---

## Root Causes

### The Bottleneck Has Shifted: From Rendering to Content
R1-R3 struggled with rendering quality (blobs, invisible fibers, dashed artifacts). R4C1 finally solved the rendering: tube radius 0.07 + glow + 60 steps produces smooth, clean output. But the judge now says the CONTENT is insufficient:

> "Limited complexity — Only 4-5 visible fiber loops. A true Hopf fibration visualization typically shows many more fibers to convey the density of the mapping."

> "Missing mathematical depth — The Hopf fibration has beautiful properties (all fibers are linked circles, base space is S², etc.) that aren't fully exploited."

This means R5 must increase fiber count significantly while maintaining the rendering quality C1 achieved.

### GPU Budget Constraint vs Fiber Density
The budget is steps x fibers x segments < 15,000.
- C1: 60 x 6 x 40 = 14,400 ✓ (6 fibers, 7/10)
- Target: 60 x 10 x 40 = 24,000 ✗ (10 fibers, over budget)

To get 10+ fibers within budget:
1. **Reduce segments to 24**: 60 x 10 x 24 = 14,400. Risk: coarser fiber approximation, possible angular artifacts. But 24 segments ≈ 15-degree angular resolution, likely sufficient.
2. **Reduce steps to 40**: 40 x 10 x 40 = 16,000 (slightly over). Ray range = 40 x 0.10 = 4.0 units. At camera dist 3.0, this covers from 1.0 to 5.0 — may be sufficient with larger tube radius.
3. **Use SDF stepping**: Variable step size means fewer total steps needed. Hard to predict exact budget.

Option 1 (fewer segments) is the most promising because the tube rendering at 0.07 radius + glow smooths over segment boundaries anyway.

### The "Art vs Math" Gap
The judge evaluates on two axes: visual quality (rendering, colors, composition) AND mathematical fidelity (does it look like a Hopf fibration?). C1 scored high on visual quality (8/10 color, 7/10 composition) but lower on mathematical content (6/10 complexity). The path to 8+ requires:
- More fibers to show the dense linking pattern
- Fibers at multiple shells to show the S2 base space structure
- Clear interlinked circles, not just random-looking curves
- Depth cues so the 3D topology is readable

### Exploratory Goals Underperformed This Round
Both exploratory candidates (C3 at 5.5, C4 at 4.0) scored below the iterative candidates (C1 at 7.0). C3's Fresnel idea was sound but invisible at current rendering resolution. C4's depth fog was destructive. The exploratory goals were trying to add visual sophistication (shading, fog) before the base content was rich enough. Premature optimization of visual effects when the fiber count is too low.

### What the 7.5/10 Prior Best Had That R4 Doesn't
We keep referencing a prior 7.5/10 best but haven't matched it. Based on the guidance lineage, the 7.5 likely used:
- More fibers (8+)
- Quadratic density + exponential alpha (the full `(1-exp(-d*d*4.5))*0.85` pipeline)
- Ray march check BEFORE step advance
- Possibly thicker tubes or better step/radius ratio

C1 at 7/10 is very close. The missing 0.5 likely comes from fiber count (6 vs 8+) and possibly from the "ray march check before step advance" ordering which C1 may not have optimized.

---

## Strategic Recommendations for Round 5

1. **Start from C1's exact code** as the iterative baseline — it's the best this round at 7/10
2. **Increase fiber count to 8-10** using reduced segment count (24-30 per fiber) to stay within GPU budget
3. **Keep tube radius 0.07** — this solved the artifact problem
4. **Keep warm/cool color split** — proven at 8/10 color score
5. **Exploratory goals should focus on fiber density and linking visibility**, not on shading effects (Fresnel, fog, etc.)
6. **Consider 3 shells x 3 rotations = 9 fibers** at 24 segments: 60 x 9 x 24 = 12,960 (under budget)
7. **Consider 4 shells x 2 rotations = 8 fibers** at 30 segments: 60 x 8 x 30 = 14,400 (at budget)
