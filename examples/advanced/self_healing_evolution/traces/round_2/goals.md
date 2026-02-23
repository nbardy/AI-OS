# Hopf Fibration Art — Round 2 Goals

## Goal 0: Nested Tori with Parallax Depth and Fresnel Edges

**Mathematical Foundation:**
Two concentric Clifford tori at different η values (η₁=π/4 for the standard torus, η₂=π/6 for a thinner inner torus). Each torus carries 4 Hopf fibers parameterized as `z₁ = cos(η)e^(iξ₁), z₂ = sin(η)e^(iξ₂)` with ξ₁ varying over [0, 2π] at 40 segments. The fibers are stereographically projected via `q.xyz / (1 - q.w + 0.35)` scaled by 0.85. The key mathematical addition: a Fresnel-like edge term `pow(1.0 - abs(dot(rayDir, fiberTangent)), 3.0)` that brightens fibers when viewed edge-on, giving them a rim-lit silhouette quality. This creates depth perception through view-dependent shading rather than fog.

**Visual Vision:**
Two nested rings of glowing fibers — an outer set of 4 thick golden-amber fibers wrapping a larger torus, and an inner set of 4 thinner cyan-blue fibers on a smaller torus. Where the inner fibers peek through gaps in the outer torus, they appear brighter due to the Fresnel edge effect, creating a sense of layered depth like looking through a cage of light. The outer fibers have warm hues (gold → coral), the inner have cool hues (cyan → violet). Dark background (near-black with subtle blue). Camera orbits slowly at y=1.5, distance=4.5, giving a slight top-down perspective that reveals the nested structure.

**Why This Approach:**
The 7/10 "Chromatic Soul Migration" used nested tori successfully. The 7.5/10 iterative best used proven fiber geometry. This combines both: nested tori (proven 7/10) with the sharp tube rendering of the iterative best (7.5/10), plus a Fresnel edge term to push toward 8+/10 by adding "sharper fiber definition" and "depth cues" — two of the explicit suggestions for breaking past 7.5. Complementary warm/cool color pairs (gold/cyan) are proven. Only 8 fibers total across 2 shells keeps GPU work well under the 15,000 iteration limit (64 steps × 8 fibers × 40 segments = 20,480 — need to use ≤48 ray steps to stay safe, or reduce to 32 segments: 64×8×32 = 16,384, trimming to ≤46 steps for safety).

**Key Implementation Hint:**
Compute fiber tangent as `normalize(nextPoint - currentPoint)` at the nearest segment, then modulate density by `mix(baseDensity, baseDensity * 2.0, fresnelTerm)` where `fresnelTerm = pow(1.0 - abs(dot(normalize(rayDir), tangent)), 3.0)`. Keep total fibers at 8 (2 shells × 4 fibers), 40 segments each, tube radius 0.11 for outer and 0.08 for inner. Use ≤48 ray march steps to stay within GPU budget. Color the nearest fiber only (no summation across segments).


## Goal 1: Phase-Animated Hopf Fibers with Crossing Brightness

**Mathematical Foundation:**
4 Hopf fibers on a single Clifford torus (η=π/4) with the standard quaternion parameterization, but with a time-dependent phase offset: `ξ₁ = θ + u_time * 0.3`, causing all fibers to rotate slowly around the torus axis. At each ray march step, compute the minimum distance to each of the 4 fibers independently. When two fibers have distances both below `2.0 * tubeRadius`, this indicates a near-crossing point. At crossings, apply a brightness multiplier of 1.5× and a slight white shift via `mix(fiberColor, vec3(1.0), 0.3)`. This implements the "visible linking at crossing points" improvement suggested for breaking past 7.5/10. The animation is a simple phase rotation in S³ — a rigid motion that preserves all Hopf fiber geometry exactly.

**Visual Vision:**
Four luminous fibers in a warm-to-cool gradient (deep red → amber → teal → indigo, evenly spaced by latitude) slowly rotating as a linked ring system on a dark background. Where fibers cross in 3D, bright white-hot nodes appear and drift along the crossing curves, creating a subtle pulsing rhythm as the rotation brings different pairs of fibers into alignment. The effect resembles four interlocked rings of molten light, with their intersections glowing brightest — emphasizing the topological linking that makes the Hopf fibration special. Camera at distance 4.5, y-offset 1.2, orbiting at a different rate than the fiber phase to create evolving viewpoints.

**Why This Approach:**
This directly targets the three "Breaking 7.5→8+" suggestions from the learnings: (1) sharper fiber definition via nearest-segment-only density, (2) visible linking at crossing points via the dual-proximity brightness boost, and (3) subtle animation via phase rotation. It stays entirely within the proven template — 4 fibers, 40 segments, single Clifford torus, standard stereographic projection — adding only two new computations: a time-varying phase (trivial) and a crossing detection (comparing 4 stored minimum distances). Total GPU work: 48 steps × 4 fibers × 40 segments = 7,680 iterations/pixel, well within budget. This is the most conservative possible path to 8+ because it changes almost nothing from the 7.5/10 template except adding the two features specifically identified as missing.

**Key Implementation Hint:**
Store `float minDist[4]` for the 4 fibers at each ray step. After finding all 4 minimum distances, check for crossings: `int crossCount = 0; for(i) if(minDist[i] < tubeRadius * 2.5) crossCount++;`. If `crossCount >= 2`, multiply the winning fiber's density contribution by 1.5 and shift its color toward white. The phase animation is just replacing `theta` with `theta + u_time * 0.3` in the quaternion formula — this rotates all fibers rigidly in S³. Keep all other parameters identical to the proven 7.5/10 template.
