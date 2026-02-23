# Round 3 Analysis

## Score Summary

| Candidate | Type | Score | Key Feature |
|-----------|------|-------|-------------|
| C0 | baseline | 5/10 | 8 fibers, 4 shells x 2 rotations, scale 1.5 |
| C1 | iterative | 6.5/10 | 6 fibers, 3 shells x 2 rotations, scale 1.5 |
| C2 | iterative | 2/10 | 6 fibers, scale 1.8, epsilon 0.12, tube 0.05 |
| C3 | exploratory | 3/10 | 6 fibers, spread Clifford torus, latitude-gradient color |
| C4 | exploratory | 6.5/10 | 8 fibers, dual-scale Villarceau circles, warm/cool split |

**Best: C1 and C4 tied at 6.5/10. No improvement over prior best of 7.5/10.**

---

## What Worked (and WHY)

### Candidate 1 (6.5/10): 6 fibers, 3 shells, standard parameters
- **Technique**: 6 fibers (3 shells at pi/6, pi/3, pi/2 x 2 rotations), scale 1.5, epsilon 0.15, tube radius 0.06, camera dist 3.0, Y-offset 1.5. Used a single flat `fiberData[960]` array storing x,y,z,hue per segment point.
- **Visual result**: "Curved, twisted fiber-like structures in vibrant colors (blue, green, red, yellow)... strands have a grainy, stippled texture and appear to weave around each other."
- **Why it scored well**: The geometry was correctly spread apart (scale 1.5, epsilon 0.15, thin tubes 0.06) so individual fibers were distinguishable. Colors were vivid with HSV(h, 0.95, 0.95). The interweaving was visible. However, judge noted fibers were "cut off at the edges" (incomplete loops) and the "grainy, stippled texture" suggests the ray march step size (0.10) relative to tube radius (0.06) caused inconsistent sampling. Still, this is the cleanest execution of the standard approach.

### Candidate 4 (6.5/10): Dual-scale Villarceau with warm/cool split
- **Technique**: 8 fibers on two shells (pi/4 and pi/6), Family A with rotations {0, pi/2, pi, 3pi/2}, Family B with rotations {pi/4, 3pi/4, 5pi/4, 7pi/4}. Warm ruby-coral for inner family, cool teal-sapphire for outer. 8 separate `float f0[120]..f7[120]` arrays.
- **Visual result**: "Dynamic, glowing bundle of intertwined circular ribbons and arcs... warm colors (red, orange, yellow) and cool colors (cyan, blue)."
- **Why it scored well**: The warm/cool color split was "clearly present and well-executed" (8/10 for color). The dual-scale concept was visible with "larger sweeping arcs and smaller circular elements." The 8 fibers with 4 rotations per family created more visible structure than 2 rotations. However, judge found the result "somewhat chaotic" and the Villarceau circle geometry "not immediately apparent."

### Common success factors in C1 and C4:
1. Post-projection scale 1.5 (not 0.85) -- fibers spread apart
2. Epsilon 0.15 -- natural projection without over-compression
3. Tube radius 0.05-0.06 -- thin enough to distinguish individual fibers
4. Camera dist 3.0 with Y-offset 1.2-1.5 -- fills frame with spread geometry
5. Dark background vec3(0.02) -- maximum contrast
6. HSV with high saturation/value -- vivid colors

---

## What Failed (and WHY)

### Candidate 2 (2/10): "Sparse, glowing curved lines... dotted/beaded arcs"
- **Root cause: Broken alpha accumulation.** C2 accumulated `totalDensity += density * stepSize` and then computed alpha as `1.0 - exp(-totalDensity * 4.5)` at the END, rather than accumulating alpha per-step. This means color was accumulated as `accumulatedColor += fiberColor * density * stepSize` -- a raw additive integral, not proper front-to-back compositing. The final `mix(background, accumulatedColor / totalDensity, alpha)` divides by totalDensity, which normalizes the color but the alpha itself is wrong because density*stepSize for thin tubes (0.05 radius) with step size 0.10 yields tiny values per step, so totalDensity never gets large enough for meaningful alpha.
- **Secondary cause: Scale 1.8 with epsilon 0.12.** These more aggressive parameters pushed some fibers further apart, possibly outside the 48-step ray march range. The judge saw only "a few dotted/beaded arcs" -- most fibers were invisible because rays passed between the thin tubes without hitting them.
- **Lesson**: Per-step alpha accumulation (as in C1) is mandatory. Post-accumulation alpha from summed density is not equivalent and produces near-invisible output for thin tubes. Also, scale 1.8 may be too aggressive -- stick to 1.5.

### Candidate 3 (3/10): "Collection of curved, glowing lines... dashed/segmented appearance"
- **Root cause: Same rendering quality as C1 but visually sparser.** C3 and C1 use nearly identical parameters (scale 1.5, epsilon 0.15, tube 0.06, 6 fibers, same shells). C3 uses `color += (1.0 - alpha) * stepAlpha * fiberColor` and `alpha += (1.0 - alpha) * stepAlpha` -- this IS correct front-to-back compositing. Yet C3 scored 3/10 vs C1's 6.5/10.
- **The actual difference**: C3 does NOT multiply alpha by 0.85 transparency factor, and does NOT have a glow halo. C1 has both the 0.85 factor and a glow halo at 1.5x tube radius. The glow halo is critical -- it fills in the gaps between ray march steps, making fibers appear continuous rather than dashed/dotted. Without glow, the 0.10 step size relative to 0.06 tube radius means rays often step completely over the tube, producing the "dashed" appearance.
- **Lesson**: The glow halo is not merely decorative -- it is structurally necessary to cover sampling gaps from coarse ray marching. It should be promoted to MANDATORY.

### Candidate 0 (5/10): "Flowing, ribbon-like strands... vertical streaks"
- **Root cause: Camera angle + fiber parametrization issue.** C0 used 8 fibers across 4 shells (pi/8, pi/4, 3pi/8, pi/2) with only 2 rotations (0, pi/2). The judge saw "purely vertical arrangement" and "generic light streaks" rather than interlocking circles. With `rotation` added to `theta` directly (not to the z/w components), fibers at rotation=pi/2 are simply phase-shifted, not rotated in 3D. From the camera's Y-offset orbit view, this created vertical-looking streaks rather than visibly interlinked rings.
- **Secondary cause: Too many shells too close together.** Shell angles pi/8, pi/4, 3pi/8, pi/2 project to similar radii after stereographic projection, making fibers overlap and appear as "generic light streaks" rather than distinct interlinked circles.
- **Lesson**: The pi/6, pi/3, pi/2 shell selection (used by C1 and C3) is superior because the projected radii are more distinct. Also, 4 shells with only 2 rotations produces less visible linking structure than 2-3 shells with more rotations.

---

## Patterns

### 1. The "Grainy/Stippled/Dashed" Problem is Universal
Four of five candidates show visible sampling artifacts. The judge describes "grainy, stippled texture" (C1), "dotted/beaded arcs" (C2), "dashed/segmented appearance" (C3), and "dotted lines" (C4). This is the dominant visual flaw across the round.

**Root cause**: Ray step size 0.10 vs tube radius 0.05-0.06 means the ray advances ~2x the tube diameter per step. Many rays step completely over thin tubes, producing intermittent hits that look dashed/dotted.

**Fix options** (in order of preference):
1. **Reduce step size to 0.05** -- halves the stepping error but doubles iteration count. Budget: 48 steps x 8 fibers x 40 segments = 15,360 (at limit). Could reduce to 40 steps to compensate: 40 x 8 x 40 = 12,800. Total ray distance = 40 x 0.05 = 2.0 units -- may be too short for camera dist 3.0. Would need to start ray closer to geometry.
2. **Increase tube radius to 0.08** -- each tube is 0.16 diameter, step 0.10 always hits. But thicker tubes risk merging. The R2 blob happened at 0.11 with scale 0.85; at scale 1.5, tubes are more spread, so 0.08 may be safe.
3. **Add analytical ray-tube intersection** -- compute exact hit point rather than stepping. Would eliminate the problem entirely but is complex and changes the rendering approach fundamentally.
4. **Glow halo (proven)** -- C1 and C4 both had glow and scored 6.5; C3 had no glow and scored 3/10 despite identical geometry. The glow fills sampling gaps.

### 2. All Candidates Hit the Same Score Ceiling (~6.5)
No candidate this round exceeded 6.5/10. The prior best was 7.5/10. The geometric fixes from R2 (scale 1.5, epsilon 0.15, thin tubes) successfully avoided the "blob" failure mode but introduced the "dashed/grainy" failure mode. We traded one problem for another.

### 3. Mathematical Clarity vs Visual Quality Trade-off
The judge consistently wants to see "complete circular fibers linking through space" (C1 critique), "the closed-loop structure that defines the Hopf fibration" (C1), and "precise mathematical construct" (C4). The current approach renders fibers as tubes approximated by 40 line segments, ray-marched at coarse step size. This fundamentally limits both smoothness and mathematical clarity.

### 4. Warm/Cool Color Split is Effective
C4's warm/cool family split scored 8/10 for color and was praised as "clearly present and well-executed." This is the highest color score this round. The approach of encoding mathematical structure (shell family) in color hue range improves both aesthetics and mathematical legibility.

### 5. Alpha Accumulation Method Matters Critically
C1 (per-step exponential alpha, 6.5/10) vs C2 (post-accumulation from density sum, 2/10). Same geometry, same parameters -- the only structural difference is when alpha is computed. Per-step front-to-back compositing is mandatory for volumetric ray marching of thin features.

---

## Root Causes

### The Fundamental Bottleneck: Ray March Resolution vs Tube Thinness
The core tension is:
- **Thin tubes (0.05-0.06)** are needed to show individual fibers distinctly
- **Coarse steps (0.10)** are needed to stay within GPU budget (48 x 8 x 40 = 15,360)
- **0.10 step >> 0.05 tube diameter** guarantees sampling artifacts

This cannot be solved by parameter tuning alone. The rendering approach needs a structural change. Options:
1. **Analytical ray-cylinder intersection**: Compute exact distance to nearest fiber tube along the ray analytically, step directly to the surface. Eliminates stepping entirely for the initial hit.
2. **SDF-guided stepping**: Use the minimum distance to any fiber as the step size (sphere tracing). Steps are large in empty space, tiny near geometry. This is standard SDF ray marching.
3. **Accept thicker tubes (0.08) + glow**: A pragmatic fix. Thicker tubes ensure consistent hits, glow covers remaining gaps. Risk: reduced distinction between adjacent fibers.

### Secondary Bottleneck: Loop Structure Without Visible Completion
The judge repeatedly notes fibers are "cut off at edges" or don't show "complete circular fibers." The 40-segment loop with wrap-around DOES close the loop mathematically, but:
- At scale 1.5 with camera dist 3.0, parts of large fibers extend outside the view frustum
- The ray march only reaches 48 x 0.10 = 4.8 units from camera, but fibers at shell pi/6 project to radius ~5.6 at scale 1.5. Parts of fibers are beyond ray march range.
- Fix: increase ray march range (more steps or larger step) OR reduce scale to keep all geometry within range.

### Strategic Assessment
The evolution has been focused on getting the geometry parameters right (scale, epsilon, tube radius, camera distance). R3 confirms these are now in a reasonable range -- no more "blob" failures. The next improvement requires:
1. Fixing the rendering quality (dashed/grainy artifacts)
2. Ensuring complete fiber visibility (no cut-off loops)
3. These are rendering/camera problems, not geometry problems

The 6.5/10 ceiling suggests the current ray-march-with-fixed-step approach has reached its limit for thin tube rendering. SDF-guided stepping would be the highest-impact change for R4.
