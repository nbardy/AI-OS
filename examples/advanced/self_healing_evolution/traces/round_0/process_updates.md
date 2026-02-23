# Tiered Guidance

## TIER 1: MANDATORY (violating guarantees failure)
- **Correct Hopf quaternion**: `q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta), sin(phi/2)*sin(theta))` where phi=shell, theta=0..2pi | Evidence: R0 all 5 used correctly; prior rounds confirm broken forms → blobs
- **Camera as Y-offset orbit, NOT spherical angles**: Use `vec3(dist*cos(angle), Y_OFFSET, dist*sin(angle))` where Y_OFFSET is 1.0-2.0 (a position, NOT an angle). NEVER use `cos(elevation)` or `sin(elevation)` with elevation>0.5 | Evidence: R0 Candidates 2,3 used spherical elevation=1.5rad → overhead view → 1-5/10; prior 7.5/10 used Y-offset
- **Camera distance >= 4.0**: Camera at 4.5 proven reliable | Evidence: R0 all candidates at 4.5; prior rounds confirm
- **Flat float arrays inside main(), <=960 floats**: Declare `float fiberData[N]` inside main() | Evidence: R0 all candidates; prior rounds confirm global arrays fail
- **Post-projection scale 0.80-0.90**: Multiply stereo-projected points by 0.85 | Evidence: R0 all candidates; prior 7.5/10 used 0.85
- **Ray march check BEFORE step**: Check distances at rayPos, THEN advance | Evidence: Prior round Candidate 1 (7.5) checks first vs Candidate 0 (6.0) steps first
- **Segment distance for curves**: Use `distanceToSegment(p, a, b)` not point distance | Evidence: All working candidates across all rounds
- **Unsigned distance only**: Convert SDF to unsigned before density calc | Evidence: Prior round Candidate 3 (1/10) failed from negative distances
- **Tube radius 0.08-0.15**: Proven visibility range | Evidence: 0.11 standard across high scorers
- **40 segments per fiber**: Check ALL 40 indices 0-39 with wrap | Evidence: Standard across all working candidates
- **Stereographic singularity protection 0.35**: Use `1/(1-w+0.35)` | Evidence: All working candidates across rounds

## TIER 2: PROVEN (used by high scorers)
- **8 fibers (4 shells x 2 rotations)**: Enough density for interlocking appearance | Evidence: Prior 7.5/10; R0 top scorer also used 8
- **Shell angles pi/8, pi/4, 3pi/8, pi/2**: Dense shell spacing | Evidence: Prior 7.5/10; R0 Candidate 2 (5/10)
- **Rotations 0 and pi/2**: Better than 0 and pi which causes overlap | Evidence: Prior 7.5/10 used pi/2; R0 Candidate 0 used pi → worse
- **HSV(h, 0.95, 0.95) per fiber**: High saturation/value against dark bg | Evidence: Prior 7.5/10; R0 Candidate 2
- **Dark background vec3(0.02)**: Maximum contrast | Evidence: All high scorers
- **Orbital camera at 0.25 rad/s with elevation Y=1.5**: Slow orbit reveals 3D | Evidence: Prior 7.5/10
- **Quadratic density + exponential alpha**: `d*d` then `1-exp(-d*4.5)` | Evidence: Prior 7.5/10
- **Transparency factor 0.85**: `alpha *= 0.85` for fiber overlap | Evidence: Prior 7.5/10
- **Glow halo at 1.5x tube radius**: `exp(-glowDist*5.0)*0.08` | Evidence: Prior 7.5/10

## TIER 3: EXPERIMENTAL (worth trying)
- **12-16 fibers for denser interlocking**: 4 shells x 3-4 rotations if array budget allows | Risk: May exceed 960 floats or blur into noise
- **Complementary two-color palette**: Gold (hue 0.08) + sapphire (hue 0.6) for warm/cool contrast instead of rainbow | Risk: May reduce fiber distinguishability
- **Animated hue flow**: `fract(baseHue + u_time * 0.1)` for color flowing along fibers | Risk: Judge found rainbow generic; may not help
- **Depth-based brightness (GENTLE)**: `mix(0.8, 1.0, exp(-0.05*depth))` not `exp(-0.5*depth)` | Risk: R0 Candidate 3 used aggressive depth atten → invisible
- **Fewer fibers (4-6) with thicker tubes 0.13-0.15**: Trade density for clarity | Risk: May appear too sparse
- **Edge brightening on tubes**: Increase brightness at tube edges for crystalline look | Risk: May look artificial

## DEPRECATED (don't retry)
- **Spherical-coordinate camera with elevation>0.5 rad**: Overhead view destroys 3D perception | Evidence: R0 Candidates 2 (5/10), 3 (1/10) — cos(1.5)=0.07 collapses orbit
- **Mixed angle quaternion form**: Different angle params in quaternion components | Evidence: Prior Candidates 2,4 → blobs
- **Global array declarations**: Outside main() | Evidence: Prior round GLSL ES failures
- **Signed SDF without unsigned conversion**: Negative distances → density>1 → saturated alpha | Evidence: Prior Candidate 3 (1/10)
- **Ray step before check**: Offsets geometry, makes it smaller | Evidence: Prior Candidate 0 (6) vs Candidate 1 (7.5)
- **Aggressive depth attenuation exp(-0.5*d)**: At camera dist 4.5 → 10% brightness → invisible | Evidence: R0 Candidate 3 (1/10)
- **Ribbon SDF via max(dist-width, normalDist-thickness)**: Broken decomposition, degenerate normals | Evidence: R0 Candidate 4 (2/10)
- **Rotations at 0 and pi**: Diametrically opposite fibers overlap from many angles | Evidence: R0 Candidate 0 (2/10) vs prior 7.5/10 with 0,pi/2
- **Separate init functions / GLSL ES array initializers**: Compilation issues | Evidence: Prior rounds + R0 Candidate 1 possible
