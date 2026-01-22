#version 300 es
precision highp float;

// Uniforms
uniform float u_time;
uniform vec2 u_resolution;

// Output
out vec4 gl_FragColor;

// ============================================================================
// Simplex Noise - Foundation for curl field generation
// ============================================================================

vec3 permute(vec3 x) {
  return mod(((x * 34.0) + 1.0) * x, 289.0);
}

float snoise(vec2 v) {
  const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
  vec2 i = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 x12 = x0.xyxy + C.xxzz;
  i = mod(i, 289.0);
  vec3 p = permute(permute(i.y + vec3(0.0, C.z, C.w)) + i.x);
  vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
  m = m * m;
  m = m * m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
  vec3 g;
  g.x = a0.x * x0.x + h.x * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

// 3D noise using 2D layering
float noise3D(vec3 p) {
  return snoise(p.xy + p.z * 0.5) * 0.5 + snoise(p.xy - p.z * 0.5) * 0.5;
}

// ============================================================================
// Curl Noise Implementation
// Generates divergence-free vector field by taking curl of 3D noise
// ============================================================================

vec3 curlNoise(vec3 p, float scale) {
  const float eps = 0.001;

  // Calculate partial derivatives numerically for curl
  float n1 = noise3D(vec3(p.x + eps, p.y, p.z) / scale);
  float n2 = noise3D(vec3(p.x - eps, p.y, p.z) / scale);
  float dnx_dy = (n1 - n2) / (2.0 * eps);

  n1 = noise3D(vec3(p.x, p.y + eps, p.z) / scale);
  n2 = noise3D(vec3(p.x, p.y - eps, p.z) / scale);
  float dny_dx = (n1 - n2) / (2.0 * eps);

  n1 = noise3D(vec3(p.x, p.y, p.z + eps) / scale);
  n2 = noise3D(vec3(p.x, p.y, p.z - eps) / scale);
  float dnz_dy = (n1 - n2) / (2.0 * eps);

  n1 = noise3D(vec3(p.x, p.y, p.z + eps) / scale);
  n2 = noise3D(vec3(p.x, p.y, p.z - eps) / scale);
  float dny_dz = (n1 - n2) / (2.0 * eps);

  n1 = noise3D(vec3(p.x + eps, p.y, p.z) / scale);
  n2 = noise3D(vec3(p.x - eps, p.y, p.z) / scale);
  float dnx_dz = (n1 - n2) / (2.0 * eps);

  n1 = noise3D(vec3(p.x, p.y + eps, p.z) / scale);
  n2 = noise3D(vec3(p.x, p.y - eps, p.z) / scale);
  float dnz_dx = (n1 - n2) / (2.0 * eps);

  // Curl: ∇ × F = (∂Fz/∂y - ∂Fy/∂z, ∂Fx/∂z - ∂Fz/∂x, ∂Fy/∂x - ∂Fx/∂y)
  vec3 curl;
  curl.x = dnz_dy - dny_dz;
  curl.y = dnx_dz - dnz_dx;
  curl.z = dny_dx - dnx_dy;

  return normalize(curl + vec3(0.001)); // Prevent zero vector
}

// ============================================================================
// Multi-Octave Turbulent Field
// Blend multiple curl noise frequencies for complex swirling patterns
// ============================================================================

vec3 turbulentField(vec3 p, float time) {
  vec3 field = vec3(0.0);
  float amplitude = 1.0;
  float frequency = 1.0;
  float maxAmplitude = 0.0;

  // Layer 4 octaves of curl noise with decreasing amplitude
  for (int i = 0; i < 4; i++) {
    float t = time * (0.5 + float(i) * 0.1);
    vec3 p_layered = p * frequency + vec3(t, t * 0.7, t * 0.3);

    field += curlNoise(p_layered, 2.0 + float(i) * 1.5) * amplitude;
    maxAmplitude += amplitude;

    amplitude *= 0.5;
    frequency *= 2.0;
  }

  return normalize(field / max(maxAmplitude, 0.001));
}

// ============================================================================
// Particle Advection Along Streamlines
// Trace particle positions through the vector field
// ============================================================================

vec3 advectParticle(vec3 startPos, float time, int steps) {
  vec3 pos = startPos;
  float stepSize = 0.02;

  for (int i = 0; i < steps; i++) {
    vec3 velocity = turbulentField(pos, time);
    pos += velocity * stepSize;
  }

  return pos;
}

// ============================================================================
// Color Mapping from Particle Properties
// ============================================================================

vec3 colorFromVelocity(vec3 velocity) {
  // Map velocity magnitude and direction to HSV-like color
  float speed = length(velocity);
  vec3 dir = normalize(velocity);

  // Hue from direction
  float hue = atan(dir.y, dir.x) / 6.28318530718 + 0.5;

  // Map HSV to RGB
  float h = hue * 6.0;
  float c = speed * 0.8 + 0.2;
  float x = c * (1.0 - abs(mod(h, 2.0) - 1.0));

  vec3 rgb;
  if (h < 1.0) rgb = vec3(c, x, 0.0);
  else if (h < 2.0) rgb = vec3(x, c, 0.0);
  else if (h < 3.0) rgb = vec3(0.0, c, x);
  else if (h < 4.0) rgb = vec3(0.0, x, c);
  else if (h < 5.0) rgb = vec3(x, 0.0, c);
  else rgb = vec3(c, 0.0, x);

  return rgb;
}

// ============================================================================
// Main Shader
// ============================================================================

void main() {
  // Normalized coordinates
  vec2 uv = gl_FragCoord.xy / u_resolution;
  vec2 centerUv = uv - 0.5;
  centerUv.x *= u_resolution.x / u_resolution.y;

  // Create multiple particle streams from grid points
  vec3 finalColor = vec3(0.0);
  float sampleCount = 0.0;

  // Sample 3x3 grid of particles with temporal jitter
  for (float px = -1.0; px <= 1.0; px += 1.0) {
    for (float py = -1.0; py <= 1.0; py += 1.0) {
      // Particle seed position with subpixel offset
      vec2 particleSeed = centerUv + vec2(px, py) * 0.15;
      vec3 particleStart = vec3(particleSeed, sin(u_time + length(particleSeed)) * 0.5);

      // Advect particle through curl noise field
      vec3 advectedPos = advectParticle(particleStart, u_time, 12);

      // Get velocity at advected position
      vec3 velocity = turbulentField(advectedPos, u_time);

      // Color based on velocity field properties
      vec3 particleColor = colorFromVelocity(velocity);

      // Add distance attenuation
      float distToOrigin = length(advectedPos.xy - particleStart.xy);
      float attenuation = exp(-distToOrigin * distToOrigin * 2.0);

      finalColor += particleColor * attenuation;
      sampleCount += 1.0;
    }
  }

  // Average samples and add animated glow
  finalColor /= sampleCount;

  // Add time-varying glow effect based on local field strength
  vec3 localField = turbulentField(vec3(centerUv, u_time * 0.3), u_time);
  float fieldStrength = length(localField);
  vec3 glowColor = vec3(sin(u_time * 0.5) * 0.5 + 0.5,
                        sin(u_time * 0.7) * 0.5 + 0.5,
                        sin(u_time * 0.9) * 0.5 + 0.5);

  finalColor += glowColor * fieldStrength * 0.3;

  // Enhance contrast and apply tone mapping
  finalColor = finalColor / (finalColor + vec3(1.0));
  finalColor = pow(finalColor, vec3(0.8)); // Gamma correction

  gl_FragColor = vec4(finalColor, 1.0);
}
