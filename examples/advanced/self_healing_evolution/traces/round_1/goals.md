# Hopf Fibration Art - Creative Goals (Round 1)

## Goal 0: Trefoil-Linked Fiber Triptych with Phase-Shifted Glow

**Mathematical Foundation:**
The Hopf fibration maps each point on S2 to a great circle in S3. Fibers over points that form a great circle on S2 are pairwise linked with linking number 1. By choosing 3 fibers at equally-spaced longitudes (xi1 = 0, 2pi/3, 4pi/3) on a single latitude shell (phi = pi/4, the Clifford torus equator), we get three linked circles that form a (3,3)-torus link -- visually resembling Borromean-like threading. Adding a second shell at phi = 3pi/8 with the same 3 longitudes produces 6 total fibers, all on two closely-spaced tori, maximizing visible interlocking.

The Hopf quaternion is the standard: `q = (cos(phi/2)*cos(theta), cos(phi/2)*sin(theta), sin(phi/2)*cos(theta+xi1), sin(phi/2)*sin(theta+xi1))` where theta sweeps 0..2pi in 40 segments. Stereographic projection via `xyz / (1 - w + 0.35)` scaled by 0.85.

The novel element: animated **phase-shifted glow**. Each fiber's glow intensity is modulated by `0.7 + 0.3 * sin(theta_param + fiber_index * pi/3 + u_time)`, creating a pulse of brightness that travels along each fiber at different phases. This produces a visual rhythm -- like three neon signs flickering in sequence -- that reveals the fiber's directionality and makes the linking more legible.

**Visual Vision:**
Three pairs of glowing rings, each pair a slightly different size (from the two shells), threading through each other in a tight braid-like arrangement. Colors use a triadic scheme: fiber pair 0 in coral-red (hue 0.02), pair 1 in emerald-green (hue 0.35), pair 2 in violet-blue (hue 0.72) -- all at saturation 0.95, value 0.95. The phase-shifted glow creates a subtle "chasing lights" effect along each ring, making the 3D structure read clearly. Dark background (vec3(0.01, 0.01, 0.02)). Camera orbits at distance 4.5, Y-offset 1.5, speed 0.25 rad/s.

**Why This Approach:**
- Uses 6 fibers (within the proven 4-8 range from TIER 2 guidance), but arranged as 3 longitude groups rather than the standard 4-shell x 2-rotation layout. This is a structural novelty that stays within proven fiber counts.
- All mandatory constraints preserved: correct quaternion, Y-offset camera at 4.5, flat arrays in main() (6 fibers x 40 segments x 3 = 720 floats, under 960), post-projection 0.85, check-before-step, distanceToSegment, unsigned distance, tube radius 0.11.
- The phase-shifted glow is a compositing-stage modification only (per the methodology critique's recommendation: "experimental techniques should only modify color/compositing, not geometry"). The distance field and ray march are identical to the proven 7.5/10 template.
- Triadic color scheme (3 hues at 120-degree separation) has not been tried but follows the "complementary color pairs" principle extended to three families.
- The methodology critique identified "structural novelty (more fibers, different fiber families)" as the next frontier. Three longitude-grouped pairs is a genuinely different fiber family selection.

**Key Implementation Hint:**
In the density accumulation loop, after computing `dist = distanceToSegment(rayPos, segA, segB)` for fiber `f`, compute the theta parameter as `float thetaParam = float(seg) / 40.0 * 6.2832;` and modulate the contribution: `float pulse = 0.7 + 0.3 * sin(thetaParam + float(f) * 1.047 + u_time * 2.0);` Multiply the standard density contribution by `pulse`. This adds directionality without changing geometry. Use 3 distinct hue values assigned by `fiber_index / 2` (fibers 0-1 share hue, 2-3 share hue, 4-5 share hue) for the triadic palette.


## Goal 1: Nested Villarceau Circles with Chromatic Depth Separation

**Mathematical Foundation:**
On the Clifford torus (the image under stereographic projection of fibers at latitude phi = pi/4), there exist two families of **Villarceau circles** -- circles obtained by slicing a torus with a plane tangent to the inner ring at a specific tilt angle `alpha = asin(r/R)` where r is the minor radius and R the major radius. For a standard Clifford torus with R=1, r=1 (equal radii after stereographic projection), alpha = pi/4 -- the plane is tilted 45 degrees. These Villarceau circles are actual Hopf fibers.

The implementation uses 4 fibers on the Clifford torus equator (phi = pi/4) with xi1 offsets of 0, pi/2, pi, 3pi/2 -- the proven Villarceau circle configuration from the 7/10 Hall of Fame entry. The twist: add a **second Clifford torus** at phi = pi/3 with 4 more fibers at the same offsets but shifted by pi/4 (i.e., xi1 = pi/4, 3pi/4, 5pi/4, 7pi/4). This creates two interleaved sets of Villarceau circles at different scales, totaling 8 fibers.

The novel visual technique: **chromatic depth separation**. Instead of per-fiber hue, assign color based on the accumulated ray depth at which each fiber is encountered. Fibers closer to the camera render in warm tones (hue 0.0-0.1, red-gold), fibers further away render in cool tones (hue 0.55-0.65, blue-teal). This is NOT depth attenuation (which dims everything) -- it's a depth-to-hue mapping that preserves full brightness while encoding spatial position in color. The effect: the viewer perceives warm shapes "in front" and cool shapes "behind," dramatically enhancing 3D readability.

**Visual Vision:**
Eight luminous rings arranged in two nested families -- an inner set of four and an outer set of four, rotated 45 degrees relative to each other. The inner family threads through the gaps in the outer family. Viewed from the orbital camera, rings in the foreground glow in warm gold-amber, while rings passing behind glow in cool cyan-teal, with smooth transitions as the camera orbits and fibers move between foreground and background. The depth-to-color mapping creates a constant visual "breathing" as warm and cool tones exchange places during rotation. Background: deep navy-black (vec3(0.01, 0.01, 0.03)). All fibers at full brightness -- no dimming, just hue shifting.

**Why This Approach:**
- Directly extends the 7/10 Villarceau Circles entry from the Hall of Fame, adding a second torus family for richer geometry.
- 8 fibers matches the TIER 2 proven count exactly, now arranged as 2 tori x 4 rotations rather than 4 shells x 2 rotations. Different arrangement, same proven count.
- Chromatic depth separation addresses the "depth cues at crossing points" item from the "Breaking 7.5 -> 8+" notes WITHOUT the fatal depth attenuation that killed R0 Candidate 3. Full brightness is maintained; only hue changes.
- All mandatory constraints preserved: correct quaternion, Y-offset camera at 4.5, flat arrays in main() (8 fibers x 40 segments x 3 = 960 floats, exactly at limit), post-projection 0.85, check-before-step, distanceToSegment, unsigned distance, tube radius 0.11.
- The warm/cool depth mapping is a compositing-stage-only modification: the distance field computation and ray march structure are unchanged from the proven template.
- Ruby/cyan complementary colors proved effective in the 7/10 Villarceau entry; this extends that to a continuous warm-cool gradient driven by geometry.

**Key Implementation Hint:**
Track ray depth during the march: `float currentDepth = float(step) * stepSize;`. When a fiber contributes density, compute its depth-based hue: `float depthHue = mix(0.05, 0.58, smoothstep(1.0, 5.0, currentDepth));`. Use this as the hue in `hsv2rgb(vec3(depthHue, 0.95, 0.95))`. The `smoothstep(1.0, 5.0, depth)` maps the useful depth range (near=1 to far=5 along the ray) to the warm-cool spectrum. This replaces the standard per-fiber hue assignment but keeps everything else identical. For the two torus families: shell 0 at phi=pi/4 with rotations 0, pi/2, pi, 3pi/2; shell 1 at phi=pi/3 with rotations pi/4, 3pi/4, 5pi/4, 7pi/4.
