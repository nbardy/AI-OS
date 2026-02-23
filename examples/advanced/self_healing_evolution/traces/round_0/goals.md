# Hopf Fibration Art - Creative Goals

## Goal 0: Interlocked Clifford Tori with Depth-Aware Silhouettes

**Mathematical Foundation:**
The Hopf fibration decomposes S3 into a family of great circles (fibers) parameterized by points on S2. Choosing fibers at two distinct latitudes (phi = pi/6 and phi = pi/3) on S2 produces two nested Clifford tori in 3-space after stereographic projection. Each torus is traced by 2 fibers (4 total), using the standard Hopf quaternion form: `q = (cos(phi/2)cos(theta), cos(phi/2)sin(theta), sin(phi/2)cos(theta), sin(phi/2)sin(theta))` with theta sweeping 0 to 2*pi in 40 segments. The two tori have different major/minor radius ratios, creating visually distinct but linked ring structures. The key mathematical insight: fibers on different tori are linked with linking number 1 -- they cannot be separated without cutting. This topological linking should be *visible* through careful depth rendering.

**Visual Vision:**
Two nested toroidal families of glowing curves against a near-black background (`vec3(0.01, 0.01, 0.02)`). The outer torus fibers glow in warm amber/gold (`hue ~ 0.08, sat 0.95`), the inner torus fibers in cool sapphire blue (`hue ~ 0.6, sat 0.95`). Where fibers from different tori cross in depth, the nearer fiber brightens slightly and the farther one dims -- creating a visual "over-under" weave effect that makes the linking tangible. The camera orbits slowly at distance 4.5, revealing how the two rings of light thread through each other. No rainbow gradients -- just the two complementary color families creating warm/cool tension.

**Why This Approach:**
- Builds directly on the 7.5/10 iterative champion: same camera distance (4.5), same segment count (40), same distanceToSegment curves, same tube radius range (0.11).
- Adds depth-aware brightness modulation -- a technique from the "Breaking 7.5 -> 8+" notes ("depth cues, brightness shift at crossings").
- Two tori at different phi values is a natural mathematical extension that hasn't been tried, creating richer geometry from the same parameterization.
- Complementary gold/blue palette follows the proven "complementary color pairs" strategy.

**Key Implementation Hint:**
Use the ray march check-before-step pattern. For each ray step, compute distance to all 4 fibers. Track the *closest* fiber index and its depth along the ray. When accumulating color, weight by `exp(-0.5 * rayDepth)` so near fibers appear brighter. Assign hue based on which torus the fiber belongs to (fibers 0-1 = gold, fibers 2-3 = blue). Post-projection scale of 0.85. Keep flat float arrays inside main(), 4 fibers x 40 segments x 3 coords = 480 floats (well under the 960 limit).


## Goal 1: Hopf Fibers as Luminous Moebius Ribbons

**Mathematical Foundation:**
Each Hopf fiber is a great circle in S3. Instead of rendering fibers as round tubes, render each as a thin *ribbon* -- a ruled surface swept along the fiber curve with width defined by the fiber's Frenet-Serret normal. For a fiber at latitude phi, the quaternion parameterization `q = (cos(phi/2)cos(theta), cos(phi/2)sin(theta), sin(phi/2)cos(theta), sin(phi/2)sin(theta))` gives the curve after stereographic projection. The tangent vector T is the theta-derivative; the normal N comes from `normalize(cross(T, vec3(0,1,0)))` (or a stable fallback). The ribbon surface is the set of points `curve(theta) + s * N(theta)` for s in [-w, w]. In SDF terms, the distance to a ribbon segment between points a and b with normals na and nb is: project p onto the line segment, then measure the *planar* distance in the cross-section (a flat rectangle instead of a circle). This creates flat, reflective-looking bands rather than round tubes. Use 4 fibers at phi = pi/4 (the Clifford torus equator) with different xi1 offsets (0, pi/2, pi, 3pi/2) for even spacing.

**Visual Vision:**
Four luminous ribbon-like bands weaving around a torus shape, each catching light differently depending on their surface orientation relative to the camera. Think of four strips of polished copper, each twisting as they orbit. The ribbons are colored by a latitude-to-hue map but with a twist: the *face* of the ribbon facing the camera appears brighter (diffuse-like shading from `abs(dot(ribbonNormal, rayDir))`), giving a sense of material surface rather than pure glow. Colors: warm spectrum -- deep red (hue 0.0) through gold (hue 0.12) across the four fibers. Background: deep charcoal-navy. The ribbon width (0.12) is comparable to tube radius but the flat cross-section reads as architecturally distinct from the round tubes of previous attempts.

**Why This Approach:**
- The global learnings note "Sharper fiber definition (less blur, more surface-like)" as a path to 8+/10. Ribbons are inherently more surface-like than tubes.
- Still uses all mandatory constraints: distanceToSegment (adapted for ribbon cross-section), 40 segments, external camera at 4.5, flat arrays inside main(), post-projection scale 0.85.
- Orientation-dependent brightness adds the "depth cues" identified as missing from the 7.5/10 result, without changing the proven ray march structure.
- 4 fibers on the Clifford torus equator is the most reliable configuration (proven in 7/10 Villarceau Circles result).
- Novel visual identity (ribbons vs tubes) provides creative distinction while staying within proven geometry.

**Key Implementation Hint:**
For the ribbon SDF: after computing the closest point on a line segment (same `distanceToSegment` logic), decompose the residual vector into tangent-plane and normal components using the interpolated ribbon normal. The ribbon distance is `max(abs(tangentComponent) - ribbonWidth, abs(normalComponent) - ribbonThickness)` where ribbonWidth = 0.12 and ribbonThickness = 0.02. This is essentially a box cross-section instead of circular. Compute ribbon normals per segment as `normalize(cross(tangent, vec3(0,1,0)))` with a fallback to `cross(tangent, vec3(1,0,0))` when tangent is near vertical. Store normals alongside positions: 4 fibers x 40 segments x 6 floats (pos+normal) = 960 floats (exactly at the limit).
