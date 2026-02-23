# Global Learnings: Hopf Fibration Art

## What Works (proven patterns)
- **Continuous curves via `distanceToSegment()`** — THE difference between 2/10 and 7/10. Never render discrete points/spheres.
- **6 fibers, 3 shells x 2 rotations** — 6 fibers at pi/6, pi/3, pi/2 with rotation spacing pi (180°). Fewer is too sparse; more merges into blob or exceeds GPU budget.
- **Tube radius 0.07 with glow at 1.5x** — 0.06 causes grainy/dashed artifacts; 0.11+ causes blob merging at scale 1.5. Glow halo is structurally necessary to cover ray march sampling gaps.
- **Post-projection scale 1.5, epsilon 0.15** — Scale 0.85 compresses fibers into undifferentiated blob. Scale 1.8+ pushes geometry outside ray march range. Epsilon 0.35 over-compresses; 0.15 spreads naturally.
- **Iterative refinement > exploratory jumps** — Across 5 rounds: iterative avg ~5/10, exploratory avg ~3/10. Novel rendering concepts (Fresnel, fog, ribbons) introduce new bug classes without improving base geometry.

## What Fails (anti-patterns)
- **`abs(minDist - tubeRadius)` density** — Creates hollow shell (density=0 AT surface). Use `(tubeRadius - minDist) / tubeRadius` inside tube. This bug caused total R1 wipeout.
- **Camera elevation as spherical angle** — `camDist * cos(1.5rad)` = overhead view destroying 3D perspective. Use Y-OFFSET: `vec3(dist*cos(t), 1.4, dist*sin(t))`.
- **`lookAt()` matrix camera** — Fragile, easy to transpose/flip. Use explicit forward/right/up vectors.
- **Depth fog, Fresnel edges, animation features** — Judge evaluates still images. Fog at `exp(-0.3*t)` destroys visibility. Fresnel is invisible on dashed tubes. Phase animation is meaningless in stills.
- **GPU overload (>15K iterations/pixel)** — steps x fibers x segments must stay under 15,000. Exceeding causes silent black output. Budget: 60 x 6 x 40 = 14,400 is proven safe.

## Mathematical Techniques
- **Hopf quaternion**: `q = (cos(φ/2)cos(θ), cos(φ/2)sin(θ), sin(φ/2)cos(θ+rot), sin(φ/2)sin(θ+rot))` — proven correct across all successful runs.
- **Direct S³ stereographic projection**: `q.xyz / (1.0 - q.w + epsilon) * scale` — NEVER use S³→S²→R³ two-step (loses fiber geometry).
- **Shell angles pi/6, pi/3, pi/2** — Project to distinct radii in R³. Closely-spaced shells (pi/8, pi/4, 3pi/8) merge visually.
- **Rotation spacing pi (180°)** — Maximally separates fiber pairs within a shell. pi/2 spacing looks chaotic.
- **40 segments per fiber** — Sufficient smoothness. 24 segments acceptable if needed for more fibers (budget tradeoff).

## Visual Strategies
- **Warm/cool color split** — Shells 1-2 warm (hues 0.05-0.15), shell 3 cool (hues 0.55-0.65). Scored 8/10 for color consistently.
- **Orbital camera Y-offset** — `vec3(3.0*cos(t), 1.4, 3.0*sin(t))`. Distance 3.0 fills frame with scale-1.5 geometry. Y=1.4 shows 3D linking.
- **High saturation HSV** — `hsv2rgb(vec3(hue, 0.95, 0.95))`. Metallic/desaturated palettes become muddy.
- **Dark background vec3(0.02)** — NOT gradients. Maximum contrast for glowing tubes.
- **Front-to-back alpha compositing per step** — `color += fiberColor * alpha * (1-accumulated)`. Post-accumulation alpha from density sums produces invisible output.

## Quick Reference: Working Shader Template

```glsl
#ifdef GL_ES
precision mediump float;
#endif
uniform float u_time;
uniform vec2 u_resolution;
#define PI 3.14159265359
#define TWO_PI 6.28318530718

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

vec4 hopfPoint(float phi, float theta, float rot) {
    float cp2 = cos(phi * 0.5), sp2 = sin(phi * 0.5);
    return vec4(cp2*cos(theta), cp2*sin(theta), sp2*cos(theta+rot), sp2*sin(theta+rot));
}

float distToSegment(vec3 p, vec3 a, vec3 b) {
    vec3 ab = b - a, ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    return length(p - a - ab * t);
}

void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) / u_resolution.y;
    float angle = u_time * 0.25;
    vec3 camera = vec3(3.0*cos(angle), 1.4, 3.0*sin(angle));
    vec3 forward = normalize(-camera);
    vec3 right = normalize(cross(vec3(0,1,0), forward));
    vec3 up = cross(forward, right);
    vec3 rayDir = normalize(forward + right*uv.x + up*uv.y);

    // 6 fibers: [phi, rotation, hue, saturation] x 6
    float fibers[24];
    fibers[0]=PI/6.0; fibers[1]=0.0; fibers[2]=0.05; fibers[3]=0.95;
    fibers[4]=PI/6.0; fibers[5]=PI;  fibers[6]=0.15; fibers[7]=0.95;
    fibers[8]=PI/3.0; fibers[9]=0.0; fibers[10]=0.10; fibers[11]=0.95;
    fibers[12]=PI/3.0; fibers[13]=PI; fibers[14]=0.08; fibers[15]=0.95;
    fibers[16]=PI/2.0; fibers[17]=0.0; fibers[18]=0.55; fibers[19]=0.95;
    fibers[20]=PI/2.0; fibers[21]=PI;  fibers[22]=0.65; fibers[23]=0.95;

    float tubeRadius = 0.07, glowRadius = tubeRadius * 1.5;
    float epsilon = 0.15, scale = 1.5;
    vec3 color = vec3(0.0);
    float accumulated = 0.0;

    for (int step = 0; step < 60; step++) {
        vec3 p = camera + rayDir * float(step) * 0.10;
        float minDist = 1e10;
        vec3 closestColor = vec3(0.0);
        for (int f = 0; f < 6; f++) {
            float phi=fibers[f*4], rot=fibers[f*4+1], hue=fibers[f*4+2], sat=fibers[f*4+3];
            for (int seg = 0; seg < 40; seg++) {
                float t0 = float(seg)*TWO_PI/40.0;
                float t1 = seg==39 ? 0.0 : float(seg+1)*TWO_PI/40.0;
                vec4 q0 = hopfPoint(phi, t0, rot), q1 = hopfPoint(phi, t1, rot);
                vec3 p0 = q0.xyz/(1.0-q0.w+epsilon)*scale;
                vec3 p1 = q1.xyz/(1.0-q1.w+epsilon)*scale;
                float d = distToSegment(p, p0, p1);
                if (d < minDist) { minDist = d; closestColor = hsv2rgb(vec3(hue,sat,0.95)); }
            }
        }
        if (minDist < glowRadius) {
            float core = minDist < tubeRadius ? pow((tubeRadius-minDist)/tubeRadius, 2.0) : 0.0;
            float glow = exp(-max(0.0, minDist-tubeRadius)*5.0) * 0.08;
            float alpha = (1.0 - exp(-(core+glow)*4.5)) * 0.85;
            color += closestColor * alpha * (1.0 - accumulated);
            accumulated += alpha * (1.0 - accumulated);
            if (accumulated > 0.95) break;
        }
    }
    color += vec3(0.02) * (1.0 - accumulated);
    gl_FragColor = vec4(color, 1.0);
}
```

## Hall of Fame
1. **7.5/10 — Iterative Refinement (pre-R0)** — Incremental improvements on proven template; original high-water mark.
2. **7/10 — R4 Candidate 1 (Iterative)** — 6 fibers, 3 shells, warm/cool split, tube 0.07, scale 1.5. Template above.
3. **6.5/10 — R3 Candidate 4 (Dual-Scale Villarceau)** — 8 fibers, warm ruby / cool teal, dual-shell families.

## Current Best
Score: 7/10 — 6-fiber iterative with warm/cool split (R4C1)

## Breaking 7/10 → 8+/10
- **More fibers (8-10)** — Judge says "limited complexity, only 4-5 visible loops." Try 3 shells x 3 rotations = 9 fibers at 24 segments (60x9x24=12,960 budget).
- **Thinner tubes once step size decreases** — SDF-guided stepping (sphere tracing) would allow 0.05 tubes without dashing artifacts.
- **Ensure complete loops visible** — Ray march range must cover full geometry extent. At scale 1.5, outer fibers reach ~5.6 units; 60 steps x 0.10 = 6.0 covers this.
- **Novel perspectives WITH proven geometry** — Inside-out view or close-up of linking region, but keep the exact quaternion/projection math.
