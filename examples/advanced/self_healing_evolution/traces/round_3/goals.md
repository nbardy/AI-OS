# Hopf Fibration Art — Round 3 Goals

## Goal 0: Spread Clifford Torus with Latitude-Gradient Color and Analytic Depth Cues

**Mathematical Foundation:**
Six Hopf fibers on three distinct shells (η = π/6, π/3, π/2) with two rotations each (ξ₁ offsets 0 and π/2). The standard Hopf quaternion `q = (cos(η/2)cos(θ), cos(η/2)sin(θ), sin(η/2)cos(θ), sin(η/2)sin(θ))` where θ sweeps 0..2π in 40 segments. Stereographic projection via `q.xyz / (1 - q.w + 0.15)` — the reduced singularity protection (0.15 instead of 0.35) allows more natural spread of the projected circles. Post-projection scale of 1.5 (NOT 0.85) to spread fibers across a wide spatial footprint. The three shell angles π/6, π/3, π/2 are chosen because they project to circles of distinctly different radii in R³: cos(η/2)/sin(η/2) ratios are ~3.7, ~1.7, ~1.0, giving clearly separable torus radii. Color is mapped from shell latitude: `hue = η / π` giving a smooth red (η=π/6, hue≈0.05) → gold (η=π/3, hue≈0.11) → cyan (η=π/2, hue≈0.17)` — but shifted to span a wider hue range for clarity: `hue = mix(0.0, 0.55, (η - π/6) / (π/2 - π/6))`, giving red → green → cyan across the three shells. Depth cue via gentle brightness falloff: `mix(0.85, 1.0, exp(-0.03 * rayDepth))` — proven gentle enough to avoid the R0 "invisible at distance" failure.

**Visual Vision:**
Three concentric rings of light — a wide red outer ring, a mid-sized golden-green ring, and a tight cyan inner ring — each composed of two linked fiber circles offset by 90°. The camera orbits at distance 3.0 with Y-offset 1.5, close enough that the spread geometry fills most of the frame. Individual fibers are clearly distinguishable as thin luminous tubes (radius 0.06) against near-black background (`vec3(0.02)`). The fiber circles at different shells have visibly different diameters, making the "nested tori" structure legible. Where fibers from different shells cross, the warm outer fibers pass over the cool inner fibers, creating a depth-layered tapestry of interlocking colored light. The overall impression: a luminous orrery of linked orbits, each ring a different size and color, clearly threaded through one another.

**Why This Approach:**
This is a **geometry-first fix** addressing the ROOT CAUSE identified in the Round 2 methodology critique: "The evolution process needs a geometry fix, not a rendering fix." Every parameter change directly targets the "compressed blob" failure:
- Scale 1.5 (not 0.85) → fibers spread apart instead of merged
- Singularity protection 0.15 (not 0.35) → natural projection without over-compression
- Tube radius 0.06 (not 0.11) → thin enough that adjacent fibers don't merge
- Camera distance 3.0 (not 4.5) → fills the frame with the now-larger geometry
- Shell angles π/6, π/3, π/2 (not π/8..π/2) → project to clearly different-sized circles
- 6 fibers (not 8) → less density, more individual visibility
- NO animation, NO Fresnel, NO crossing detection → zero GPU budget on invisible features
- Latitude-to-hue mapping is proven (7/10 "Chromatic Soul Migration" entry)

This follows ALL mandatory constraints and ALL R2 recommendations. It is the most conservative possible attempt to get the geometry right before adding any visual polish.

**Key Implementation Hint:**
The critical parameter set: `float SCALE = 1.5; float EPSILON = 0.15; float TUBE_RADIUS = 0.06; float CAM_DIST = 3.0; float Y_OFFSET = 1.5;`. Generate fiber data as flat arrays inside main(): `float f0[120]; float f1[120]; ... float f5[120];` (6 fibers × 40 segments × 3 floats = 720 total, under 960 limit). For each fiber, compute 40 points: `float phi = shellAngle; float theta = float(seg) * 6.2832 / 40.0; vec4 q = vec4(cos(phi*0.5)*cos(theta), cos(phi*0.5)*sin(theta), sin(phi*0.5)*cos(theta+rotation), sin(phi*0.5)*sin(theta+rotation)); vec3 proj = q.xyz / (1.0 - q.w + EPSILON) * SCALE;`. Ray march with 48 steps, step size 0.10, check-before-step. At each step, find nearest segment across all 6 fibers. Only nearest fiber contributes density: `float density = max(0.0, (TUBE_RADIUS - minDist) / TUBE_RADIUS); density = density * density;`. Alpha accumulation: `alpha += (1.0 - alpha) * (1.0 - exp(-density * 4.5));`. Color from shell index via HSV.


## Goal 1: Dual-Scale Villarceau Circles with Complementary Warm/Cool Split

**Mathematical Foundation:**
Eight Hopf fibers arranged as two families of Villarceau circles at different scales. Family A: 4 fibers on the Clifford torus at η = π/4 with ξ₁ offsets of 0, π/2, π, 3π/2 — the configuration that scored 7/10 in the Hall of Fame "Villarceau Circles" entry. Family B: 4 fibers on a larger torus at η = π/6 with ξ₁ offsets of π/4, 3π/4, 5π/4, 7π/4 — interleaved 45° from Family A. The standard Hopf quaternion parameterization with stereographic projection `q.xyz / (1.0 - q.w + 0.15)` and post-projection scale 1.5. The η = π/6 shell projects to a larger circle than η = π/4, so Family B forms a wider ring that Family A threads through. The 45° offset between families ensures maximum visible separation between fibers from different families. Villarceau circles on a torus are true Hopf fibers — this is not an approximation but an exact representation of the fibration's topology. The linking number between any fiber from Family A and any from Family B is exactly 1, which should be visible as threading.

**Visual Vision:**
Two sets of four interlinked rings — an inner set in warm ruby-coral tones (hues 0.0–0.05) and an outer set in cool teal-sapphire tones (hues 0.5–0.58). The inner rings are tighter and thread through the wider outer rings like a chain-mail weave. Each individual ring is clearly visible as a thin luminous tube (radius 0.05) against the dark background. The complementary warm/cool split makes it immediately obvious which rings belong to which family, and where they cross, the warm-over-cool or cool-over-warm layering reveals the 3D interlocking structure. The camera at distance 3.0 and Y-offset 1.2 catches the structure at a slight angle, revealing the depth of the threading. Overall impression: a jeweled knot of ruby and sapphire rings, each clearly distinct, woven through each other in an impossible-seeming but mathematically precise pattern.

**Why This Approach:**
This directly extends the highest-scoring approach from the Hall of Fame (Villarceau Circles, 7/10) while applying ALL of the Round 2 geometry fixes:
- Starts from the proven 7/10 Villarceau configuration (4 fibers at η=π/4) — not reinventing
- Adds a second shell at η=π/6 for scale contrast (wider outer ring) — addresses "all fibers same size" critique
- Uses updated projection parameters (scale 1.5, epsilon 0.15, tube radius 0.05) — avoids the "blob" failure
- Complementary ruby/cyan colors are proven (7/10 Villarceau entry used ruby/cyan)
- 8 fibers at 40 segments = 960 floats (exactly at limit), 48 steps × 8 fibers × 40 segments = 15,360 — tight but within budget (reduce to 46 steps = 14,720 for safety)
- NO animation features (wasted on still evaluation)
- The 45° rotation offset between families maximizes spatial separation, a geometric improvement over the R1 "Nested Villarceau" attempt which used same-angle offsets
- The warm/cool split by family (not by depth) provides consistent color coding that the judge can parse even in a still image

**Key Implementation Hint:**
Generate 8 fiber arrays inside main(): `float f0[120]..f7[120]` (8 × 40 × 3 = 960 floats, at the limit). Shells: `float shells[2] = float[2](0.7854, 0.5236);` (π/4, π/6). Family A (fibers 0–3): shell 0, rotations 0, π/2, π, 3π/2. Family B (fibers 4–7): shell 1, rotations π/4, 3π/4, 5π/4, 7π/4. Each point: `vec4 q = vec4(cos(s*0.5)*cos(theta), cos(s*0.5)*sin(theta), sin(s*0.5)*cos(theta+rot), sin(s*0.5)*sin(theta+rot)); vec3 proj = q.xyz / (1.0 - q.w + 0.15) * 1.5;`. Color: Family A → `hsv2rgb(vec3(0.02 + 0.03*float(fiberIdx), 0.95, 0.95))`, Family B → `hsv2rgb(vec3(0.52 + 0.03*float(fiberIdx-4), 0.95, 0.95))`. Ray march: 46 steps, step size 0.10, find nearest segment across all 8 fibers, render nearest only. Density: `max(0.0, (0.05 - minDist) / 0.05)` squared, alpha via `1-exp(-d*4.5)`. Camera: `vec3(3.0*cos(u_time*0.25), 1.2, 3.0*sin(u_time*0.25))`.
