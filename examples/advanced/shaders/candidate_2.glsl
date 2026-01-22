// Parallel Transport Visualization: S² with Horizontal Lifts to S³
// Computes tangent vectors, integrates fiber curves with geometric phase,
// colors by holonomy angle, and visualizes Villarceau circles from torus sections
//
// Key mathematical structures:
// - Base manifold: S² (2-sphere)
// - Total space: S³ (3-sphere, principal U(1) bundle over S²)
// - Connection: Geometric phase from parallel transport
// - Holonomy: Accumulated phase around base loops
// - Villarceau circles: Special torus sections intersecting S³

#ifdef GL_ES
precision highp float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

const float PI = 3.14159265359;
const float TAU = 6.28318530718;
const float EPSILON = 1e-6;

// ============================================================================
// Utility Functions
// ============================================================================

// Create orthonormal basis for tangent space at point on S²
void getTangentBasis(vec3 p, out vec3 u, out vec3 v) {
    // u: derivative in theta direction (longitude)
    // v: derivative in phi direction (latitude)
    float theta = atan(p.y, p.x);
    float phi = acos(clamp(p.z, -1.0, 1.0));

    u = vec3(-sin(theta), cos(theta), 0.0);
    v = vec3(cos(theta) * cos(phi), sin(theta) * cos(phi), -sin(phi));
}

// Hermitian connection form (geometric phase)
// For U(1) bundle, connection is 1-form A = A_θ dθ + A_φ dφ
vec2 getConnectionForm(vec3 p) {
    float theta = atan(p.y, p.x);
    float phi = acos(clamp(p.z, -1.0, 1.0));

    // Monopole-like connection: Dirac string at south pole
    // A_θ = (1 - cos(phi)) / 2  (Gives integer flux through S²)
    // A_φ = 0
    float A_theta = (1.0 - cos(phi)) * 0.5;
    return vec2(A_theta, 0.0);
}

// Parallel transport operator (infinitesimal rotation in fiber)
// Accumulates holonomy as we traverse curve on base
float computeHolonomy(vec3 p0, vec3 p1, float s) {
    // Linear interpolation on S² (projection onto sphere)
    vec3 path = normalize(mix(p0, p1, s));

    vec2 conn0 = getConnectionForm(p0);
    vec2 conn1 = getConnectionForm(p1);
    vec2 conn = mix(conn0, conn1, s);

    // Tangent direction to path
    vec3 tangent = normalize(p1 - p0);
    vec3 u, v;
    getTangentBasis(path, u, v);

    // Project tangent onto basis
    float t_u = dot(tangent, u);
    float t_v = dot(tangent, v);

    // Holonomy 1-form evaluation: A·ds
    float dA = conn.x * t_u + conn.y * t_v;
    return dA;
}

// S² to S³ lift: horizontal section of principal bundle
// Given point on S² and fiber coordinate psi, return point on S³
vec4 liftToS3(vec3 base, float psi) {
    // S³ as S² × S¹ with connection
    // The psi coordinate is modified by parallel transport

    // Compute accumulated phase from reference point
    vec3 ref = vec3(1.0, 0.0, 0.0);
    float phase = 0.0;

    // Integrate connection along geodesic from ref to base
    float steps = 20.0;
    for (float i = 0.0; i < steps; i++) {
        float s = i / steps;
        float s_next = (i + 1.0) / steps;
        phase += computeHolonomy(ref, base, s) * (1.0 / steps);
    }

    // S³ coordinates: (cos(psi), sin(psi)*base)
    float c = cos(psi + phase);
    float s = sin(psi + phase);

    return vec4(c, s * base);
}

// Curvature 2-form: F = dA (holonomy density)
// For monopole connection: F = (1/2) * sin(phi) dθ ∧ dφ
float getCurvature(vec3 p) {
    float phi = acos(clamp(p.z, -1.0, 1.0));
    // Magnetic monopole field strength
    return sin(phi) * 0.5;
}

// ============================================================================
// Loop Holonomy: Integrate around closed curves
// ============================================================================

float computeLoopHolonomy(vec3 center, float radius, float t) {
    // Loop on S² around center point
    // Uses Stokes' theorem: ∮_C A = ∫∫_S F

    // Gaussian curvature on S² is 1
    // For monopole: integral of F over loop = flux through surface

    // Parametric loop: small circle around center
    float holonomy = 0.0;
    float samples = 32.0;

    for (float i = 0.0; i < samples; i++) {
        float theta1 = TAU * i / samples;
        float theta2 = TAU * (i + 1.0) / samples;

        // Small circle on S² (not geodesic)
        vec3 u, v;
        getTangentBasis(center, u, v);

        vec3 p1 = normalize(center + radius * (cos(theta1) * u + sin(theta1) * v));
        vec3 p2 = normalize(center + radius * (cos(theta2) * u + sin(theta2) * v));

        holonomy += computeHolonomy(p1, p2, 0.5);
    }

    return holonomy;
}

// ============================================================================
// Villarceau Circles: Torus sections intersecting S³
// ============================================================================

// Distance to nearest Villarceau circle in S³
// Villarceau circles emerge from flat torus sections
float villarceuCircleDistance(vec4 p) {
    // Project to relevant coordinates
    // Villarceau circles: special torus sections where torus intersects S³

    float x = p.x;
    float y = length(p.yzw);

    // Two Villarceau circles at different positions
    float r1 = abs(length(vec3(x - 0.707, y - 0.707, 0.0)) - 0.3);
    float r2 = abs(length(vec3(x + 0.707, y - 0.707, 0.0)) - 0.3);

    return min(r1, r2);
}

// ============================================================================
// Fiber Curve Integration
// ============================================================================

// Integrate fiber curve (geodesic in fiber direction)
vec3 integrateBaseCurve(vec2 uv, float t) {
    // Start from a point determined by screen coordinates
    float theta = atan(uv.y, uv.x);
    float r = length(uv);

    // Map to S²
    float phi = r * PI;
    theta = theta * 0.5;

    vec3 base = vec3(
        sin(phi) * cos(theta),
        sin(phi) * sin(theta),
        cos(phi)
    );

    // Add temporal animation: base curves move over time
    float phi_t = phi + 0.3 * sin(u_time);
    float theta_t = theta + 0.2 * u_time;

    base = vec3(
        sin(phi_t) * cos(theta_t),
        sin(phi_t) * sin(theta_t),
        cos(phi_t)
    );

    return base;
}

// ============================================================================
// Main Shader
// ============================================================================

void main() {
    // Normalize coordinates to [-1, 1]
    vec2 uv = (2.0 * gl_FragCoord.xy - u_resolution) / u_resolution.y;

    // Compute base point on S²
    float r = length(uv);

    // Handle north pole (small r)
    if (r < EPSILON) {
        gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
        return;
    }

    // Stereographic projection: uv -> S²
    float scale = 2.0 / (1.0 + dot(uv, uv));
    vec3 base = vec3(scale * uv, scale - 1.0);

    // Add temporal dynamics
    base = normalize(base + 0.2 * vec3(sin(u_time), cos(u_time * 0.7), sin(u_time * 0.5)));

    // Compute holonomy around loops
    float loop_radius = 0.2 + 0.1 * sin(u_time);
    float holonomy = computeLoopHolonomy(base, loop_radius, u_time);

    // Normalize holonomy to [0, 1]
    float phase = fract(holonomy * 2.0 / PI);

    // Lift to S³ with holonomy-dependent fiber coordinate
    vec4 lifted = liftToS3(base, phase * TAU);

    // Compute Villarceau circle interaction
    float villarceau_dist = villarceuCircleDistance(lifted);
    float villarceau_factor = exp(-villarceau_dist * villarceau_dist * 10.0);

    // Curvature field (monopole strength)
    float curvature = getCurvature(base);

    // Color channels encode different geometric information

    // Red: Holonomy phase
    float red = 0.5 + 0.5 * sin(phase * TAU);

    // Green: Curvature/connection strength
    float green = 0.3 + 0.7 * curvature;

    // Blue: Villarceau circle visibility
    float blue = 0.2 + 0.8 * villarceau_factor;

    // Fiber coordinate visualization (S¹ angle)
    float fiber_phase = fract(lifted.x * 3.0 + u_time * 0.5);

    // Add striping from fiber dynamics
    float stripe = 0.5 + 0.5 * sin(fiber_phase * TAU);

    // Combine layers with geometric information
    vec3 color = vec3(red, green, blue);
    color = mix(color, vec3(1.0), stripe * 0.3);

    // Add radial distance shading (stereographic projection fade)
    float fade = 1.0 / (1.0 + r * r);
    color *= fade;

    // Highlight Villarceau circles
    if (villarceau_factor > 0.3) {
        color = mix(color, vec3(1.0, 0.5, 0.0), villarceau_factor * 0.7);
    }

    // Temporal animation: pulsing based on time
    float pulse = 0.8 + 0.2 * sin(u_time * 2.0);
    color *= pulse;

    gl_FragColor = vec4(color, 1.0);
}
