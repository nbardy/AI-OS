# Round 4 Goals: Hopf Fibration Art

## Goal 0: Fresnel-Edged Fibers with Crossing Brightness Flare

**Mathematical Foundation:**
Standard Hopf parameterization with 4 fibers on the Clifford torus at η = π/4 (equal S¹ radii), using the proven quaternion formula `q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ+rot), sin(φ/2)sin(θ+rot))` with rotations at 0, π/2, π, 3π/2. The key mathematical addition is a **Fresnel-like view-angle term** on each tube: compute the dot product between the ray direction and the local fiber tangent vector (finite difference of adjacent segment centers). When the ray is nearly perpendicular to the fiber (grazing angle), boost brightness to create sharp silhouette edges. At fiber-fiber crossing points in screen space, the overlapping glow halos naturally sum, creating **bright nodes at topological linking points** — the visual signature of the Hopf invariant.

**Visual Vision:**
Four luminous tubes on a dark background (vec3(0.01, 0.01, 0.02)), each a different hue from a complementary split palette: ruby (hue 0.0), amber (0.08), teal (0.5), and violet (0.75). Fibers appear as **glowing neon wires with bright edges** — brighter at the silhouette than the center, like glass rods lit from within. Where two fibers cross in the viewer's line of sight, a brief **white-hot flare** appears from the combined glow, making the linking structure pop. Slow orbital camera at distance 3.0 with Y-offset 1.5. The overall effect is reminiscent of neon light sculpture — sharp, architectural, luminous.

**Why This Approach:**
This directly targets the "breaking 7.5→8+" guidance: "sharper fiber definition (less blur, more surface-like)" and "visible linking at crossing points (depth cues, brightness shift)." The Fresnel edge term is cheap (one dot product per step) and doesn't change the proven geometry pipeline at all — it's purely a shading enhancement on top of the exact template that scored 6.5/10. The crossing flare comes free from the existing glow halo mechanism (already mandatory at 1.5x tube radius) — we just allow it to accumulate slightly more at overlaps instead of clamping early. This is an iterative refinement, not a reinvention.

**Key Implementation Hint:**
For the Fresnel term: at each ray march step, after finding the nearest segment (a, b) to point p, compute `tangent = normalize(b - a)` and `viewAngle = abs(dot(normalize(rayDir), tangent))`. The Fresnel factor is `fresnel = pow(1.0 - viewAngle, 2.0)`. Multiply the fiber's base color contribution by `mix(1.0, 2.5, fresnel)`. This makes edges 2.5x brighter than centers. For crossing flare: after computing all 4 fibers' contributions at a step, if total alpha exceeds 0.6, add `vec3(0.3) * (totalAlpha - 0.6)` as a white boost. Keep all mandatory constraints: 40 segments/wrap, tube radius 0.06, glow at 1.5x, per-step front-to-back accumulation, flat arrays in main().

---

## Goal 1: Dual-Latitude Fiber Families with Depth-Fog Separation

**Mathematical Foundation:**
Instead of 4 fibers at a single Clifford torus latitude (η = π/4), use **two fiber families at different latitudes**: Family A at η = π/6 (smaller torus, tighter circles) with 2 fibers at rotations 0 and π, and Family B at η = π/3 (larger torus, wider circles) with 2 fibers at rotations π/4 and 5π/4. This exploits the actual structure of the Hopf fibration — every point on S² (parameterized by η) gives a different fiber, and fibers at different latitudes are **linked but geometrically distinct** (different torus radii in R³ after stereographic projection). A subtle **depth fog** darkens distant geometry: `fogFactor = exp(-depth * 0.3)`, giving the first clear **depth separation** between the two torus scales.

**Visual Vision:**
Two nested torus-shaped fiber structures, one inside the other, like Russian nesting dolls made of light. The **inner pair** (η = π/6) glows warm gold and copper, tracing tight linked circles. The **outer pair** (η = π/3) glows cool cyan and silver-blue, tracing wider arcs that visibly pass through and around the inner fibers. The depth fog causes the far side of each torus to fade slightly, creating a strong sense of 3D volume — you can tell which fibers are in front. Dark background, orbital camera at distance 3.0, Y-offset 1.2. The warm/cool color split between inner and outer families makes the nested topology immediately readable. The overall effect is like a glowing orrery — concentric orbits of light at different scales.

**Why This Approach:**
The 6.5/10 "Dual-Scale Villarceau" attempt proved that multi-scale fiber families can score well, but it used Villarceau circles which add geometric complexity without improving the core Hopf structure. This approach is simpler: standard Hopf fibers at two different latitudes, using the same proven quaternion + stereographic pipeline. The depth fog is the specific fix for a known weakness — previous attempts lack depth cues, making 3D structure ambiguous (noted in "breaking 7.5→8+: depth cues"). The fog is trivially cheap (one exp per step) and doesn't affect the geometry pipeline. Still only 4 total fibers (proven optimal count), still 40 segments each (proven), still uses all mandatory constraints.

**Key Implementation Hint:**
Family A fibers use η = π/6 → `cos(η/2) ≈ 0.966, sin(η/2) ≈ 0.259`, producing a smaller stereographic radius. Family B uses η = π/3 → `cos(η/2) ≈ 0.866, sin(η/2) ≈ 0.500`, producing a larger radius. Apply scale 1.5 post-projection as mandatory. For depth fog: track the ray parameter `t` at each step and apply `fogFactor = exp(-t * 0.3)` to the fiber color before accumulation. Color mapping: fibers 0,1 (Family A) use `hsv(0.08, 0.9, 1.0)` and `hsv(0.05, 0.85, 0.9)` (gold/copper); fibers 2,3 (Family B) use `hsv(0.52, 0.9, 1.0)` and `hsv(0.55, 0.7, 0.85)` (cyan/silver). All other parameters exactly per mandatory constraints: tube radius 0.06, glow halo at 1.5x with exp(-d*5.0)*0.08, 40 segments with wrap, per-step front-to-back alpha, camera at (3.0*cos(t), 1.2, 3.0*sin(t)), epsilon 0.15.
