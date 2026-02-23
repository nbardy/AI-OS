# Tiered Guidance

## TIER 1: MANDATORY (violating guarantees failure)
- **Correct Hopf quaternion**: `q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta+rot), sin(phi/2)*sin(theta+rot))` | Evidence: R0-R3 all candidates
- **Direct S3 stereographic projection ONLY**: `q.xyz / (1 - q.w + EPSILON)`. NEVER S3->S2->R3 | Evidence: R1C1 degenerate 1/10
- **Camera as Y-offset orbit**: `vec3(dist*cos(angle), Y_OFFSET, dist*sin(angle))`, Y_OFFSET 1.0-2.0. NEVER spherical angles | Evidence: R0C2,C3 overhead 1-5/10
- **Camera distance 2.5-3.5**: Use 3.0 with scale 1.5 | Evidence: R2 too far; R3C1,C4 at 3.0 scored 6.5
- **Flat float arrays inside main(), <=960 floats** | Evidence: R0-R3 all candidates; global arrays fail
- **Post-projection scale 1.2-1.8**: Use 1.5. NOT 0.85 (blob) or 1.8+ (too spread) | Evidence: R2 all 0.85->3/10; R3C2 at 1.8->2/10
- **Stereographic epsilon 0.10-0.20**: Use 0.15. NOT 0.35 | Evidence: R2 compressed blob; R3C1,C4 at 0.15->6.5
- **Solid tube density, nearest-segment-only**: `(tubeRadius - minDist) / tubeRadius` for closest segment only | Evidence: R1C1,C2 hollow->1/10; R1C3 sum-all->1/10
- **Per-step front-to-back alpha accumulation**: `color += fiberColor * alpha * (1-accum); accum += alpha * (1-accum)`. NEVER post-accumulate from density sum | Evidence: R3C2 post-accum->2/10 vs R3C1 per-step->6.5
- **Tube radius 0.05-0.08**: Thin enough to distinguish fibers, thick enough to hit with step 0.10 | Evidence: R2 at 0.11->blob; R3 at 0.05-0.06->dashed artifacts
- **Glow halo at 1.5x tube radius**: `exp(-glowDist*5.0)*0.08`. Structurally necessary to cover ray march sampling gaps | Evidence: R3C1,C4 with glow->6.5; R3C3 without glow->3/10 (identical geometry)
- **40 segments per fiber with wrap**: next = (seg+1)%40 | Evidence: All working candidates R0-R3
- **Standard UV formula**: `(gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y` | Evidence: R1C4 scaled->1/10
- **Total GPU work < 15,000 iterations/pixel**: steps x fibers x segments | Evidence: R1C3,C4 timeout->1/10
- **Ray march check BEFORE step advance** | Evidence: Prior 7.5 vs 6.0

## TIER 2: PROVEN (used by high scorers)
- **6-8 fibers (2-3 shells x 2-4 rotations)** | Evidence: R3C1 6 fibers->6.5; R3C4 8 fibers->6.5
- **Shell angles pi/6, pi/3, pi/2 (not pi/8)**: Wider spacing for distinct projected radii | Evidence: R3C0 pi/8->5/10 "vertical streaks"; R3C1 pi/6,pi/3,pi/2->6.5
- **Warm/cool color split by shell family**: Encodes mathematical structure in color | Evidence: R3C4 warm/cool->8/10 color score
- **HSV(h, 0.95, 0.95) per fiber**: High saturation/value on dark bg | Evidence: R0-R3 all high scorers
- **Dark background vec3(0.02)** | Evidence: R0-R3 all high scorers
- **Orbital camera 0.25 rad/s, Y=1.2-1.5** | Evidence: R3C1,C4 both 6.5
- **Quadratic density + exponential alpha**: `d*d` then `(1-exp(-d*4.5))*0.85` | Evidence: Prior 7.5; R3C1 6.5
- **Ray step size 0.08-0.12** | Evidence: R3 all at 0.10

## TIER 3: EXPERIMENTAL (worth trying)
- **SDF-guided stepping (sphere tracing)**: Use minDist as step size instead of fixed 0.10. Large steps in empty space, tiny near geometry. Eliminates dashed/grainy artifacts | Risk: More complex implementation; may need min step floor
- **Tube radius 0.08 with scale 1.5**: Thicker tubes ensure consistent ray hits, glow covers gaps. Scale 1.5 keeps fibers spread | Risk: Adjacent fibers may merge at same shell
- **Reduce step size to 0.06 with 64 steps**: 64x8x40=20,480 over budget. Use with 6 fibers: 64x6x40=15,360 at limit | Risk: GPU budget tight
- **4 rotations per shell (0, pi/4, pi/2, 3pi/4)**: More fibers per shell shows linking better | Risk: Adjacent fibers may merge; more GPU work
- **Depth-aware camera dist**: Start ray at bounding sphere of geometry, not camera pos. Saves steps for distant geometry | Risk: Requires knowing geometry bounds

## DEPRECATED (don't retry)
- **Post-projection scale 0.85**: Compresses into merged blob | R2 all 5 candidates->3/10
- **Post-projection scale 1.8+**: Too spread, fibers outside view/ray range | R3C2->2/10 sparse invisible
- **Singularity protection 0.35**: Over-compresses geometry | R2 all->compressed blob
- **Singularity protection 0.12**: Too aggressive, combined with scale 1.8 pushes geometry too far | R3C2->2/10
- **Tube radius 0.11+**: Too thick, fiber merging | R2 merged blob
- **Camera distance 4.5 with scale 0.85**: Too far for compressed geometry | R2 "small floating form"
- **Post-accumulation alpha from density sum**: Near-invisible output for thin tubes | R3C2->2/10
- **No glow halo**: Dashed/segmented appearance from sampling gaps | R3C3->3/10 vs R3C1->6.5 (same geometry)
- **Shell angles pi/8 through pi/2 in 4 steps**: Too close after projection, appear as vertical streaks | R3C0->5/10
- **Fresnel edge term**: Invisible in opaque tube rendering | R2C3 no effect
- **Phase animation for still-image evaluation**: Judge evaluates stills | R2C4 wasted budget
- **Spherical-coordinate camera with elevation>0.5**: Collapses orbit | R0C2,C3
- **S3->S2->R3 two-step projection**: Collapses fibers to points | R1C1
- **abs(minDist - tubeRadius) as density**: Hollow shell inversion | R1C1,C2
- **Sum-all-segments accumulation**: Runaway density | R1C3
- **>100 steps with 8x40 inner loop**: GPU timeout | R1C3,C4
- **UV scaling factor != 1.0**: Halves geometry | R1C4
- **GLSL ES array initializers float[N](...)**: Compilation issues | Prior rounds
- **Aggressive depth attenuation exp(-0.5*d)**: Invisible far geometry | R0C3
