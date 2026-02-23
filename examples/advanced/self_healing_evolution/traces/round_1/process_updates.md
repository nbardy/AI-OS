# Tiered Guidance

## TIER 1: MANDATORY (violating guarantees failure)
- **Correct Hopf quaternion**: `q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta), sin(phi/2)*sin(theta))` where phi=shell, theta=0..2pi | Evidence: R0-R1 all candidates; broken forms → blobs
- **Direct S³ stereographic projection ONLY**: Project quaternion q directly via `q.xyz / (1 - q.w + 0.35)`. NEVER project S³→S²→R³ | Evidence: R1 Candidate 1 used Hopf map to S² first → degenerate geometry → 1/10
- **Camera as Y-offset orbit, NOT spherical angles**: `vec3(dist*cos(angle), Y_OFFSET, dist*sin(angle))` where Y_OFFSET is 1.0-2.0. NEVER use cos/sin(elevation) | Evidence: R0 Candidates 2,3 → overhead → 1-5/10; R1 all used correct form but still failed
- **Camera distance >= 4.0**: Camera at 4.5 proven | Evidence: R0-R1 all candidates at 4.5
- **Flat float arrays inside main(), <=960 floats**: `float fiberData[N]` inside main() | Evidence: R0-R1 all candidates; global arrays fail
- **Post-projection scale 0.80-0.90**: Multiply by 0.85 | Evidence: R0-R1 all; prior 7.5/10
- **Ray march check BEFORE step**: Check distances at rayPos, THEN advance | Evidence: Prior Candidate 1 (7.5) vs Candidate 0 (6.0)
- **Segment distance for curves**: `distanceToSegment(p, a, b)` not point distance | Evidence: All working candidates
- **Unsigned distance only**: No negative distances in density calc | Evidence: Prior Candidate 3 (1/10)
- **Solid tube density, NOT hollow shell**: Use `(tubeRadius - minDist) / tubeRadius` when minDist < tubeRadius. NEVER use `abs(minDist - tubeRadius)` as density | Evidence: R1 Candidates 1,2 used hollow shell → uniform color field → 1/10
- **Nearest-segment-only density**: Only the closest segment contributes density per ray step. NEVER sum contributions from all segments | Evidence: R1 Candidate 3 summed all → runaway accumulation → black → 1/10
- **Tube radius 0.08-0.15**: 0.11 standard | Evidence: All high scorers
- **40 segments per fiber with wrap**: Check indices 0-39, next = (seg+1)%40 | Evidence: All working candidates
- **Stereographic singularity protection 0.35**: `1/(1-w+0.35)` | Evidence: All working candidates
- **Total GPU work < 15,000 iterations/pixel**: Keep steps×fibers×segments under limit. Use <=64 steps, <=8 fibers, <=40 segments | Evidence: R1 Candidates 3,4 used 160 steps → likely GPU timeout → black/fragment
- **Standard UV formula**: `(gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y`. No extra scaling factors | Evidence: R1 Candidate 4 doubled UV → geometry halved → tiny crescent

## TIER 2: PROVEN (used by high scorers)
- **8 fibers (4 shells x 2 rotations)**: Interlocking density | Evidence: Prior 7.5/10; R0 top scorer
- **Shell angles pi/8, pi/4, 3pi/8, pi/2**: Dense spacing | Evidence: Prior 7.5/10; R0 Candidate 2
- **Rotations 0 and pi/2**: Avoids overlap | Evidence: Prior 7.5/10
- **HSV(h, 0.95, 0.95) per fiber**: High saturation/value | Evidence: Prior 7.5/10
- **Dark background vec3(0.02)**: Maximum contrast | Evidence: All high scorers
- **Orbital camera 0.25 rad/s, Y=1.5**: Slow orbit | Evidence: Prior 7.5/10
- **Quadratic density + exponential alpha**: `d*d` then `1-exp(-d*4.5)` | Evidence: Prior 7.5/10
- **Transparency factor 0.85**: For fiber overlap | Evidence: Prior 7.5/10
- **Glow halo at 1.5x tube radius**: `exp(-glowDist*5.0)*0.08` | Evidence: Prior 7.5/10
- **Ray step size 0.08-0.15**: Fine enough for tube radius 0.11 | Evidence: Prior 7.5/10 used 0.08

## TIER 3: EXPERIMENTAL (worth trying)
- **Reduce to 24 segments per fiber**: Halves inner loop cost, still smooth enough for circles | Risk: Slightly faceted appearance
- **Reduce to 48 ray steps**: Saves 40% GPU work vs 80 steps | Risk: May miss thin geometry
- **Complementary two-color palette**: Gold + sapphire for warm/cool contrast | Risk: May reduce fiber distinguishability
- **Gentle depth brightness**: `mix(0.85, 1.0, exp(-0.03*depth))` | Risk: Prior aggressive attenuation failed
- **Triadic color scheme (3 hue groups)**: Fibers colored in 3 families | Risk: Untested but visually promising
- **Phase-shifted glow on fibers**: Pulse brightness along fiber via theta param | Risk: Only modify compositing, not geometry

## DEPRECATED (don't retry)
- **Spherical-coordinate camera with elevation>0.5 rad**: cos(1.5)=0.07 collapses orbit | Evidence: R0 Candidates 2,3
- **Mixed angle quaternion form**: → blobs | Evidence: Prior Candidates 2,4
- **Global array declarations**: GLSL ES failures | Evidence: Prior rounds
- **Signed SDF without unsigned conversion**: Negative distances → saturated alpha | Evidence: Prior Candidate 3
- **Ray step before check**: Offsets geometry | Evidence: Prior Candidate 0 (6) vs 1 (7.5)
- **Aggressive depth attenuation exp(-0.5*d)**: → invisible at dist 4.5 | Evidence: R0 Candidate 3
- **Ribbon SDF via max(dist-width, normalDist-thickness)**: Degenerate normals | Evidence: R0 Candidate 4
- **Rotations at 0 and pi**: Overlap | Evidence: R0 Candidate 0
- **GLSL ES array initializers float[N](...)**: Compilation issues | Evidence: Prior rounds
- **S³→S²→R³ two-step projection**: Collapses fibers to points on S² | Evidence: R1 Candidate 1
- **abs(minDist - tubeRadius) as density**: Hollow shell, inverts rendering | Evidence: R1 Candidates 1,2
- **Sum-all-segments accumulation**: Runaway density, early exit bugs | Evidence: R1 Candidate 3
- **>100 ray march steps with 8×40 inner loop**: Exceeds GPU limits → black | Evidence: R1 Candidates 3,4
- **UV scaling factor ≠ 1.0**: Doubles/halves apparent geometry size | Evidence: R1 Candidate 4
