# Tiered Guidance

## TIER 1: MANDATORY (violating guarantees failure)
- **Correct Hopf quaternion**: `q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta+rot), sin(phi/2)*sin(theta+rot))` | Evidence: R0-R4 all candidates
- **Direct S3 stereographic projection ONLY**: `q.xyz / (1 - q.w + EPSILON)`. NEVER S3->S2->R3 | Evidence: R1C1 degenerate 1/10
- **Camera as Y-offset orbit with explicit forward/right/up vectors**: `vec3(dist*cos(angle), Y_OFFSET, dist*sin(angle))`, Y_OFFSET 1.2-1.5. NEVER lookAt matrix, NEVER spherical angles | Evidence: R0C2,C3 overhead 1-5/10; R4C2 lookAt matrix->1/10
- **Camera distance 2.5-3.5**: Use 3.0 with scale 1.5 | Evidence: R2 too far; R3C1,C4 at 3.0->6.5; R4C1 at 3.0->7/10
- **Flat float arrays inside main(), <=960 floats** (or inline computation via helper function) | Evidence: R0-R4 all candidates; global arrays fail
- **Post-projection scale 1.2-1.8**: Use 1.5. NOT 0.85 (blob) or 1.8+ (too spread) | Evidence: R2 all 0.85->3/10; R3C2 at 1.8->2/10
- **Stereographic epsilon 0.10-0.20**: Use 0.15 | Evidence: R2 compressed blob at 0.35; R3C1,C4 at 0.15->6.5
- **Solid tube density, nearest-segment-only**: `(tubeRadius - minDist) / tubeRadius` for closest segment only | Evidence: R1C1,C2 hollow->1/10; R1C3 sum-all->1/10
- **Per-step front-to-back alpha accumulation**: `color += fiberColor * alpha * (1-accum); accum += alpha * (1-accum)`. NEVER post-accumulate from density sum | Evidence: R3C2 post-accum->2/10 vs R3C1 per-step->6.5
- **Tube radius 0.07**: Sweet spot — 0.06 produces grainy/dashed artifacts, 0.11+ causes blob merging | Evidence: R4C1 at 0.07->7/10 smooth; R3C1 at 0.06->6.5 grainy; R2 at 0.11->blob
- **Glow halo at 1.5x tube radius**: `exp(-glowDist*5.0)*0.08`. Structurally necessary to cover sampling gaps | Evidence: R3C1,C4 with glow->6.5; R3C3 without->3/10; R4C1 with glow->7/10
- **40 segments per fiber with wrap**: next = (seg+1)%40. Can reduce to 24-30 if fiber count >6 for GPU budget | Evidence: All working candidates R0-R4
- **Standard UV formula**: `(gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y` | Evidence: R1C4 scaled->1/10
- **Total GPU work < 15,000 iterations/pixel**: steps x fibers x segments | Evidence: R1C3,C4 timeout->1/10; R4C2 at 20,480->1/10
- **Ray march check BEFORE step advance** | Evidence: Prior 7.5 vs 6.0
- **Quadratic density + exponential alpha**: `d*d` then `(1-exp(-d*4.5))*0.85` | Evidence: Prior 7.5; R3C1 6.5; R4C1 7/10 (promoted from TIER 2: 4 rounds of evidence)

## TIER 2: PROVEN (used by high scorers)
- **6-8 fibers (2-3 shells x 2-3 rotations)**: More fibers = higher math scores, but must fit GPU budget | Evidence: R3C1 6 fibers->6.5; R4C1 6 fibers->7/10; R3C4 8 fibers->6.5
- **Shell angles pi/6, pi/3, pi/2**: Wider spacing for distinct projected radii | Evidence: R3C0 pi/8->5/10; R3C1 pi/6,pi/3,pi/2->6.5; R4C1 same->7/10
- **Rotation spacing pi (180 degrees) between fiber pairs**: Maximally separated on S1 | Evidence: R4C1 rot=pi->7/10; R4C0 rot=pi/2->5/10 "chaotic"
- **Warm/cool color split by shell family**: Encodes mathematical structure in color | Evidence: R3C4 warm/cool->8/10 color; R4C1 warm/cool->8/10 color
- **HSV(h, 0.95, 0.95) per fiber**: High saturation/value on dark bg | Evidence: R0-R4 all high scorers
- **Dark background vec3(0.02)** | Evidence: R0-R4 all high scorers
- **Orbital camera 0.25 rad/s, Y=1.2-1.5** | Evidence: R3C1,C4 both 6.5; R4C1 at Y=1.4->7/10
- **60 ray march steps at step size 0.10**: Better coverage than 48 steps, fits budget with 6 fibers x 40 seg | Evidence: R4C1 60 steps->7/10; R4C0 48 steps->5/10
- **Inline fiber computation via helper function**: Avoids flat array complexity, works within GPU budget | Evidence: R4C1 inline hopfPoint()->7/10

## TIER 3: EXPERIMENTAL (worth trying)
- **8-10 fibers with reduced segments (24-30)**: 60x9x24=12,960 or 60x8x30=14,400 fits budget. More fibers addresses judge's "limited complexity" critique | Risk: Coarser fiber approximation; segment boundaries may be visible
- **3 shells x 3 rotations = 9 fibers**: Adds a third rotation per shell (0, 2pi/3, 4pi/3) for denser linking pattern | Risk: GPU budget tight; adjacent fibers in same shell may merge
- **SDF-guided stepping (sphere tracing)**: Use minDist as step size for adaptive stepping | Risk: Complex implementation; may need min step floor
- **Subtle depth fog exp(-t*0.05)**: Very gentle 5-15% darkening at max depth for depth cues | Risk: R4C4 at 0.3 destroyed visibility; must be 6x weaker

## DEPRECATED (don't retry)
- **Post-projection scale 0.85**: Compresses into merged blob | R2 all->3/10
- **Post-projection scale 1.8+**: Too spread, fibers outside view/ray range | R3C2->2/10
- **Singularity protection 0.35**: Over-compresses geometry | R2->compressed blob
- **Singularity protection 0.12**: Combined with scale 1.8 pushes geometry too far | R3C2->2/10
- **Tube radius 0.11+**: Too thick, fiber merging | R2 merged blob
- **Tube radius 0.05-0.06**: Too thin, grainy/dashed artifacts with step 0.10 | R3C1 "stippled" 6.5; R4C3 "dotted" 5.5
- **Camera distance 4.5 with scale 0.85**: Too far for compressed geometry | R2 "small floating form"
- **Post-accumulation alpha from density sum**: Near-invisible output for thin tubes | R3C2->2/10
- **No glow halo**: Dashed/segmented appearance from sampling gaps | R3C3->3/10
- **Shell angles pi/8 through pi/2 in 4 steps**: Too close after projection | R3C0->5/10
- **Fresnel edge term**: Invisible at current ray march resolution; requires smooth surfaces we don't have | R4C3 no visible effect, 5.5/10
- **Depth fog exp(-0.3*t)**: Destroys visibility, makes everything muddy | R4C4->4/10 "extremely heavy-handed"
- **lookAt() matrix camera construction**: Fragile, wrong-handedness/FOV bugs | R4C2->1/10 gradient only
- **Rotation spacing pi/2 (90 degrees)**: Too small, fibers look chaotic not linked | R4C0->5/10 "random intertwining"
- **Only 4 fibers total**: Too sparse, judge wants dense linking structure | R4C3->5.5; R4C4->4/10
- **Phase animation for still-image evaluation**: Judge evaluates stills | R2C4 wasted budget
- **Spherical-coordinate camera with elevation>0.5**: Collapses orbit | R0C2,C3
- **S3->S2->R3 two-step projection**: Collapses fibers to points | R1C1
- **abs(minDist - tubeRadius) as density**: Hollow shell inversion | R1C1,C2
- **Sum-all-segments accumulation**: Runaway density | R1C3
- **>100 steps with 8x40 inner loop**: GPU timeout | R1C3,C4
- **UV scaling factor != 1.0**: Halves geometry | R1C4
- **GLSL ES array initializers float[N](...)**: Compilation issues | Prior rounds
- **Aggressive depth attenuation exp(-0.5*d)**: Invisible far geometry | R0C3
