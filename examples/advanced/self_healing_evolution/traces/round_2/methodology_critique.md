# Round 2 Analysis

## Score Summary

| Candidate | Strategy | Score |
|-----------|----------|-------|
| 0 | Baseline (8 fibers, 4 shells x 2 rotations) | 3/10 |
| 1 | Iterative (8 fibers, proper alpha accumulation) | 3/10 |
| 2 | Iterative (8 fibers, volume rendering) | 3/10 |
| 3 | Exploratory (Nested Tori + Fresnel edges) | 3/10 |
| 4 | Exploratory (Phase-animated + crossing brightness) | 3/10 |

**Round best: 3/10 (all tied). Prior round best: 1/10 (all). Historic best: 7.5/10 (pre-R0).**

This round is a recovery from R1's total wipeout (all 1/10) to uniform 3/10 — geometry is now rendering visibly, but the visual quality is uniformly poor. Every candidate produces a distorted blob or partial crescent rather than the elegant linked-circles structure of a Hopf fibration.

## What Worked (and WHY)

### Recovery from R1's Black Screen / Uniform Color Failures

All five candidates now produce VISIBLE output. This is a direct result of the R1 post-mortem fixes:

1. **Solid tube density formula restored**: All candidates use `(tubeRadius - minDist) / tubeRadius` correctly. No candidate uses the R1 `abs(minDist - tubeRadius)` hollow shell bug. Evidence: Candidates 0-4 all produce visible colored geometry instead of R1's uniform color fields.

2. **Nearest-segment-only density**: All candidates check distance to all segments but only render the closest fiber. No runaway accumulation. Evidence: No candidate produces the R1 "early exit → black" failure.

3. **GPU budget respected**: All candidates use <=64 ray steps with 8 fibers x 40 segments. Candidate 0 uses 64 steps (64x8x40 = 20,480 — above the 15K guideline but within GPU capacity on this platform). Candidates 1, 3, 4 use 46-48 steps. Evidence: All produce output (vs R1 Candidates 3,4 using 160 steps → black).

4. **Direct S3 stereographic projection**: All candidates use `q.xyz / (1 - q.w + 0.35)`. No S3→S2→R3 two-step. Evidence: Geometry is coherent (vs R1 Candidate 1's degenerate S2 projection).

5. **Standard UV formula**: All use `(gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y`. No scaling artifacts. Evidence: Geometry fills a reasonable portion of screen (vs R1 Candidate 4's doubled UV → tiny crescent).

### Tier 1 Mandatory Rules Fully Effective

Every TIER 1 rule from the R1 guidance was obeyed by every candidate. The system-level failures from R1 (inverted density, wrong projection, GPU overload) are completely eliminated. The remaining 3/10 score is NOT from violating known constraints — it's from a different class of problem.

## What Failed (and WHY)

### ALL CANDIDATES: Distorted Geometry — "Kidney Bean" / "Blob" / "Crescent"

Every judge report describes essentially the same failure: the rendered geometry is a distorted, asymmetric blob rather than recognizable interlocking circles.

**Judge descriptions:**
- Candidate 0: "distorted, kidney-bean shaped form" — "severely distorted" — "collapsed, asymmetric blob"
- Candidate 1: "single elliptical/kidney-shaped form" — "curved color strip"
- Candidate 2: "single elliptical/kidney-shaped form" — "a single fiber or loop"
- Candidate 3: "curved, glowing ribbons arranged in a rough vertical cluster" — "separate ribbon segments"
- Candidate 4: "single curved, tube-like form" — "a single strand floating in space"

This is a UNIVERSAL failure mode across all 5 candidates despite different strategies.

### Root Cause Analysis: The Hopf Parameterization Produces Overlapping Fibers

The core issue is NOT a rendering bug — it's that the mathematical parameterization places fibers too close together, causing them to merge into an undifferentiated blob when rendered.

**Evidence chain:**

1. All candidates use the same quaternion: `q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta), sin(phi/2)*sin(theta))`

2. With shells at pi/8, pi/4, 3pi/8, pi/2 and rotations at 0, pi/2 — the 8 fibers generate Hopf circles at different "latitudes" on S3.

3. After stereographic projection `q.xyz / (1 - q.w + 0.35)`, these circles project into R3. But the stereographic projection with the singularity protection term `+0.35` compresses the geometry significantly. The `0.85` post-scale further shrinks it.

4. The projected fibers end up **very close together in R3** — close enough that with tube radius 0.11 and the volumetric rendering, they merge into a single blobby mass. The judge cannot distinguish individual circles.

5. The "kidney bean" shape arises because the stereographic projection maps the different phi shells to different-sized circles in R3, but they all overlap near the projection "pole," creating an asymmetric merged shape.

### Candidate 3 (Nested Tori + Fresnel): Nested Structure Not Visible

**Goal:** Two tori at eta=pi/4 and eta=pi/6 with 4 fibers each, Fresnel edge term.

**Why it scored 3/10 despite a novel approach:**
- The two torus shells (pi/4 and pi/6) produce fibers at different radii in R3, but the outer torus obscures the inner one from most viewing angles.
- The Fresnel term `pow(1.0 - abs(dot(rayDir, tangent)), 3.0)` is computed correctly but has minimal visual impact because the ray marching renders solid tubes — the Fresnel brightening is absorbed into the already-opaque tube rendering rather than creating visible rim lighting.
- The warm/cool color split (gold outer, cyan inner) is invisible because the inner fibers are hidden behind the outer ones. The judge saw only "curved, glowing ribbons" with "no convincing parallax depth."
- The mathematical parameterization has a subtle issue: `xi2` is fixed per fiber (not varying with `xi1`), so each fiber is a circle where `xi1` traces the fiber and `xi2` is constant. This is valid but produces fibers that trace along the torus in only one angular direction, making them appear as parallel arcs rather than linked circles.

### Candidate 4 (Phase-Animated + Crossing Brightness): Animation Invisible in Still

**Goal:** 4 fibers with time-varying phase, brightness boost at fiber crossings.

**Why it scored 3/10:**
- The judge evaluates a STILL IMAGE, not an animation. The `+ u_time * 0.3` phase animation is invisible in a static screenshot. The crossing brightness feature (the key novelty) only appears at specific frames — the screenshot may have captured a frame with no crossings visible.
- Only 4 fibers on a single torus (eta=pi/4) produces a visually sparse structure. With the stereographic projection compression, 4 fibers is not enough to fill the frame with interlocking structure.
- The judge specifically noted: "completely misses the essence... the interweaving structure of multiple fibers." Four fibers on one torus produce circles that are all the same size and shape — they don't demonstrate the nested/linked property of Hopf fibrations.
- The phase animation applies `theta + u_time * 0.3` to ALL fibers uniformly, so their relative positions don't change. The crossing detection (`crossCount >= 2`) triggers in the same spatial locations regardless of time — the animation just rotates the entire structure, it doesn't create evolving crossings.

### Candidate 0 (Baseline): Triadic Color Scheme Adds Nothing

The baseline uses a triadic color scheme (warm/cool/neutral families) instead of simple per-fiber HSV hues. However, because the fibers merge into a blob, the color scheme is irrelevant — the judge just sees "vibrant rainbow-like colors cycling through the structure" without connecting colors to individual fibers.

### Candidates 1 & 2 (Iterative): Nearly Identical Code, Identical Failure

Candidates 1 and 2 are extremely similar — both are faithful reproductions of the proven template. Their minor differences (volume rendering accumulation in C2 vs simple mix in C1, lookAt matrix in C2 vs manual camera in C1) don't affect the fundamental output. Both produce the same kidney-bean blob.

## Patterns

### 1. Plateau at 3/10: The "Visible But Ugly" Floor

R1 was a total failure (all 1/10). R2 recovered to all 3/10. This suggests the TIER 1 mandatory rules successfully prevent catastrophic failures (black screen, uniform color field) but the proven template itself only produces ~3/10 quality output. The historic 7.5/10 was likely from a different rendering environment or judge calibration.

### 2. All Candidates Converge to Same Visual Output

Despite different strategies (baseline, iterative, exploratory), different fiber counts (4 vs 8), different color schemes (triadic, warm/cool split, per-fiber HSV), and different features (Fresnel, crossing detection, volume rendering) — all produce essentially the same "distorted blob on black background." The bottleneck is NOT in rendering details but in the underlying geometry and its projection.

### 3. Stereographic Projection + Singularity Protection = Compressed Geometry

The `q.xyz / (1 - q.w + 0.35)` projection with the `+0.35` term prevents division by zero but significantly compresses the geometry near the projection pole. The `* 0.85` post-scale further shrinks it. The result is that all fibers are squeezed into a compact, overlapping mass instead of spread out as clearly distinguishable interlocking circles.

### 4. Judge Consistently Wants "Multiple Linked Circles" — Not Getting Them

Every judge critique says the same thing: they want to see multiple distinct circular fibers that are clearly linked/interlocking. Every candidate produces a merged blob instead. This is the singular gap between current output and the goal.

### 5. Exploratory Goals Didn't Help (But Didn't Catastrophically Fail Either)

Candidates 3 and 4 had novel features (Fresnel edges, crossing brightness) but scored the same 3/10 as the baseline and iterative candidates. The novel features didn't hurt (unlike R0/R1 where exploration caused new bugs) but they also didn't help because the base geometry is the real problem.

### 6. Animation Features Wasted on Still-Image Evaluation

Candidate 4's phase animation and crossing brightness are designed for animated viewing. The judge evaluates a single still frame. Features optimized for animation (time-varying phase, crossing detection) are invisible or arbitrary in a still.

## Root Causes

### PRIMARY: Fiber Geometry Is Too Compressed After Stereographic Projection

The stereographic projection `q.xyz / (1 - q.w + 0.35)` with singularity protection `0.35` and post-scale `0.85` compresses 8 Hopf fibers into a ~2-unit-diameter blob. At camera distance 4.5, this blob subtends maybe 25 degrees of the viewing angle. The fibers within this blob are separated by fractions of the tube radius, so they merge visually.

**What needs to change:**
- Reduce singularity protection from 0.35 to a smaller value (e.g., 0.1) to allow more geometric spread — BUT this risks infinity near the pole
- Increase post-scale from 0.85 to 1.5-2.0 to spread the geometry out — this is the safest approach
- Use a different set of shell angles that produces more widely-separated circles in R3 after projection
- Reduce tube radius below 0.11 to prevent fiber merging (try 0.05-0.07)
- OR fundamentally change the parameterization to produce more visually distinct fiber positions

### SECONDARY: Camera Distance Too Far for Compressed Geometry

Camera at 4.5 viewing ~2-unit geometry means the fibration fills only a small portion of the screen. The judge sees "a small form floating in void." Moving the camera closer (distance 2.5-3.0) or increasing the post-projection scale would both help.

### TERTIARY: Single-Image Evaluation Penalizes Animation Features

The evolution loop evaluates still frames. Any GPU work spent on animation features (phase rotation, crossing detection) is wasted computation that could have been spent on more fibers or finer ray marching.

### QUATERNARY: Fiber Count vs. Visual Distinction Tradeoff

8 fibers produces dense geometry that merges into a blob. 4 fibers is too sparse to show linking. The sweet spot may be 6 fibers with larger post-projection scale and smaller tube radius, so each fiber is individually visible AND there are enough to show interlocking.

### META: The Evolution Process Needs a Geometry Fix, Not a Rendering Fix

Three rounds of evolution have optimized rendering parameters (tube radius, glow, alpha, color schemes, Fresnel, crossing detection) while the underlying geometry has remained the same compressed blob. No amount of rendering polish can fix compressed geometry. The next round MUST address the stereographic projection parameters to spread fibers out into individually visible, clearly interlocking circles.

## Recommendations for Round 3

1. **INCREASE post-projection scale to 1.5-2.0** (from 0.85) — spread the geometry to fill more screen space
2. **DECREASE camera distance to 3.0** (from 4.5) — get closer to the spread-out geometry
3. **DECREASE tube radius to 0.06** (from 0.11) — thinner tubes prevent fiber merging
4. **DECREASE singularity protection to 0.15** (from 0.35) — allow more natural geometric spread
5. **Use 6 fibers** (3 shells x 2 rotations or 2 shells x 3 rotations) — enough for linking without blob merge
6. **Use shell angles that project to DIFFERENT SIZES**: Try pi/6, pi/3, pi/2 for varied radii in R3
7. **Don't invest in animation** — the judge evaluates stills
8. **Don't invest in Fresnel/crossing detection** — these are polish on a geometry that doesn't work yet
