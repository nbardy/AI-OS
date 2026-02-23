# Tiered Guidance

## TIER 1: MANDATORY (violating guarantees failure)
- **Correct Hopf quaternion**: `q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta), sin(phi/2)*sin(theta))` where phi=shell, theta=0..2pi | Evidence: R0-R2 all candidates; broken forms → blobs
- **Direct S3 stereographic projection ONLY**: `q.xyz / (1 - q.w + EPSILON)`. NEVER project S3→S2→R3 | Evidence: R1 Candidate 1 → degenerate → 1/10
- **Camera as Y-offset orbit, NOT spherical angles**: `vec3(dist*cos(angle), Y_OFFSET, dist*sin(angle))` where Y_OFFSET is 1.0-2.0. NEVER use cos/sin(elevation) | Evidence: R0 Candidates 2,3 → overhead → 1-5/10
- **Camera distance 2.5-4.5**: Scale with post-projection size. Closer for larger scale. 4.5 proven with 0.85 scale, use 3.0 with 1.5 scale | Evidence: R0-R2; R2 too far for compressed geometry
- **Flat float arrays inside main(), <=960 floats**: `float fiberData[N]` inside main() | Evidence: R0-R2 all candidates; global arrays fail
- **Post-projection scale 1.2-2.0**: Multiply projected coords by 1.5 (NOT 0.85). 0.85 compresses fibers into merged blob | Evidence: R2 all candidates at 0.85 → "kidney bean blob" → 3/10
- **Ray march check BEFORE step**: Check distances at rayPos, THEN advance | Evidence: Prior Candidate 1 (7.5) vs Candidate 0 (6.0)
- **Segment distance for curves**: `distanceToSegment(p, a, b)` not point distance | Evidence: All working candidates
- **Unsigned distance only**: No negative distances in density calc | Evidence: Prior Candidate 3 (1/10)
- **Solid tube density, NOT hollow shell**: Use `(tubeRadius - minDist) / tubeRadius`. NEVER use `abs(minDist - tubeRadius)` | Evidence: R1 Candidates 1,2 → uniform color → 1/10
- **Nearest-segment-only density**: Only closest segment contributes. NEVER sum all segments | Evidence: R1 Candidate 3 → runaway accumulation → 1/10
- **Tube radius 0.04-0.08**: Thin tubes prevent fiber merging. 0.11 too thick for spread geometry | Evidence: R2 all at 0.11 → merged blob → 3/10
- **40 segments per fiber with wrap**: next = (seg+1)%40 | Evidence: All working candidates
- **Stereographic singularity protection 0.10-0.20**: `1/(1-w+0.15)`. 0.35 over-compresses geometry | Evidence: R2 all at 0.35 → compressed blob → 3/10
- **Total GPU work < 15,000 iterations/pixel**: steps x fibers x segments. Use <=48 steps, <=8 fibers, <=40 segments | Evidence: R1 Candidates 3,4 → GPU timeout → 1/10
- **Standard UV formula**: `(gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y`. No extra scaling | Evidence: R1 Candidate 4 → halved geometry → 1/10

## TIER 2: PROVEN (used by high scorers)
- **6-8 fibers (3-4 shells x 2 rotations)**: Enough for linking, not so many they merge | Evidence: Prior 7.5/10; R0-R2
- **Shell angles pi/6, pi/3, pi/2**: Wider spacing for distinct projected radii in R3 | Evidence: R2 analysis; pi/8..pi/2 too close after projection
- **Rotations 0 and pi/2**: Avoids overlap | Evidence: Prior 7.5/10
- **HSV(h, 0.95, 0.95) per fiber**: High saturation/value | Evidence: Prior 7.5/10
- **Dark background vec3(0.02)**: Maximum contrast | Evidence: All high scorers R0-R2
- **Orbital camera 0.25 rad/s, Y=1.5**: Slow orbit | Evidence: Prior 7.5/10
- **Quadratic density + exponential alpha**: `d*d` then `1-exp(-d*4.5)` | Evidence: Prior 7.5/10
- **Transparency factor 0.85**: For fiber overlap | Evidence: Prior 7.5/10
- **Glow halo at 1.5x tube radius**: `exp(-glowDist*5.0)*0.08` | Evidence: Prior 7.5/10
- **Ray step size 0.08-0.15**: Fine enough for thin tubes | Evidence: Prior 7.5/10

## TIER 3: EXPERIMENTAL (worth trying)
- **Post-projection scale 2.0 with camera dist 2.5**: Maximize geometric spread and screen fill | Risk: May push fibers outside view frustum
- **Singularity protection 0.10**: More natural spread, less compression | Risk: May create large/infinite geometry near pole
- **Tube radius 0.04**: Ultra-thin fibers for maximum individual visibility | Risk: May become invisible if too thin
- **Warm/cool color split by shell**: Outer warm, inner cool for depth perception | Risk: Requires visible nesting
- **Gentle depth brightness**: `mix(0.85, 1.0, exp(-0.03*depth))` | Risk: Prior aggressive attenuation failed

## DEPRECATED (don't retry)
- **Post-projection scale 0.85**: Compresses all fibers into merged blob | Failed because: R2 all 5 candidates → 3/10 "kidney bean"
- **Singularity protection 0.35**: Over-compresses projected geometry | Failed because: R2 all candidates → compressed blob
- **Tube radius 0.11+**: Too thick, causes fiber merging at any projection scale | Failed because: R2 merged blob
- **Camera distance 4.5 with scale 0.85**: Too far for compressed geometry | Failed because: R2 "small form floating in void"
- **Fresnel edge term**: Invisible in opaque tube rendering | Failed because: R2 Candidate 3 → no visible effect → 3/10
- **Phase animation for still-image evaluation**: Judge evaluates stills, animation invisible | Failed because: R2 Candidate 4 → wasted GPU budget
- **Crossing brightness detection**: Requires animation to show, invisible in stills | Failed because: R2 Candidate 4 → no visible effect → 3/10
- **Spherical-coordinate camera with elevation>0.5 rad**: cos(1.5)=0.07 collapses orbit | Evidence: R0 Candidates 2,3
- **S3→S2→R3 two-step projection**: Collapses fibers to points on S2 | Evidence: R1 Candidate 1
- **abs(minDist - tubeRadius) as density**: Hollow shell, inverts rendering | Evidence: R1 Candidates 1,2
- **Sum-all-segments accumulation**: Runaway density, early exit bugs | Evidence: R1 Candidate 3
- **>100 ray march steps with 8x40 inner loop**: Exceeds GPU limits | Evidence: R1 Candidates 3,4
- **UV scaling factor != 1.0**: Doubles/halves apparent geometry size | Evidence: R1 Candidate 4
- **Rotations at 0 and pi**: Overlap from opposite sides | Evidence: R0 Candidate 0
- **GLSL ES array initializers float[N](...)**: Compilation issues | Evidence: Prior rounds
- **Aggressive depth attenuation exp(-0.5*d)**: Invisible at dist 4.5 | Evidence: R0 Candidate 3
- **Ribbon SDF via max(dist-width, normalDist-thickness)**: Degenerate normals | Evidence: R0 Candidate 4
