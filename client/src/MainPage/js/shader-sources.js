export const vertexShaderSource = `
  attribute vec2 a_position;
  varying vec2 v_uv;

  void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
    v_uv = (a_position + 1.0) * 0.5;
    v_uv.y = 1.0 - v_uv.y;
  }
`

export const fragmentShaderSource = `
  precision highp float;

  uniform float u_time;
  uniform vec2 u_resolution;

  #define PI 3.14159265359

  float hash(float n) {
    return fract(sin(n) * 43758.5453123);
  }

  float hash2(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
  }

  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);

    float a = hash2(i);
    float b = hash2(i + vec2(1.0, 0.0));
    float c = hash2(i + vec2(0.0, 1.0));
    float d = hash2(i + vec2(1.0, 1.0));

    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
  }

  float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;

    for (int i = 0; i < 4; i++) {
      value += amplitude * noise(p * frequency);
      frequency *= 2.0;
      amplitude *= 0.5;
    }

    return value;
  }

  float graphFunction1(float x) {
    float t = u_time * 0.5;
    return sin(x * 2.0 + t) * 0.25 +
           sin(x * 3.0 + t * 1.3) * 0.15;
  }

  float graphFunction2(float x) {
    float t = u_time * 0.4;
    return cos(x * 2.5 + t) * 0.2 +
           sin(x * 4.0 + t * 1.5) * 0.15;
  }

  float graphFunction5(float x) {
    float t = u_time * 0.3;
    return sin(x + t) + cos(x + t * 1.2);
  }

  float drawLineSegment(vec2 uv, vec2 a, vec2 b, float width) {
    vec2 pa = uv - a;
    vec2 ba = b - a;
    float baLen = length(ba);
    if (baLen < 0.001) return 0.0;
    float h = clamp(dot(pa, ba) / (baLen * baLen), 0.0, 1.0);
    float d = length(pa - ba * h);
    return smoothstep(width, width * 0.5, d);
  }

  float drawLine(vec2 uv, float y) {
    float lineWidth = 0.003;
    float dist = abs(uv.y - y);
    return smoothstep(lineWidth, 0.0, dist);
  }

  float drawPoint(vec2 uv, vec2 pos, float radius) {
    float dist = length(uv - pos);
    return smoothstep(radius, 0.0, dist);
  }

  float drawCloud(vec2 uv, vec2 pos, float size, float density) {
    float dist = length((uv - pos) / size);
    float cloud = fbm((uv - pos) * 4.0 + u_time * 0.1) * density;
    cloud *= smoothstep(1.5, 0.0, dist);
    return cloud;
  }

  float drawSpark(vec2 uv, vec2 pos, float time, float lifetime) {
    float age = mod(time, lifetime);
    float life = age / lifetime;
    if (life > 1.0) return 0.0;

    vec2 dir = normalize(pos);
    vec2 sparkPos = pos + dir * age * 0.3;
    float dist = length(uv - sparkPos);

    float spark = smoothstep(0.015, 0.0, dist);
    spark *= (1.0 - life) * (1.0 - life);
    spark *= sin(life * PI);

    vec2 tailDir = -dir;
    for (float i = 1.0; i <= 3.0; i++) {
      vec2 tailPos = sparkPos + tailDir * i * 0.02;
      float tailDist = length(uv - tailPos);
      float tail = smoothstep(0.008, 0.0, tailDist);
      tail *= (1.0 - life) * (1.0 - i / 3.0);
      spark = max(spark, tail * 0.5);
    }

    return spark;
  }

  float drawTrendLine(vec2 uv, float x, float slope, float intercept) {
    float y = slope * x + intercept;
    return drawLine(uv, y);
  }

  varying vec2 v_uv;

  void main() {
    vec2 uv = v_uv;
    vec2 centered = (uv * 2.0 - 1.0) * vec2(u_resolution.x / u_resolution.y, 1.0);

    vec3 col = vec3(0.0);
    float alpha = 0.0;

    vec2 graphUV = centered * 1.35;
    graphUV.x -= 2.0;

    float gridAlpha = 0.12;
    for (float i = -2.0; i <= 2.0; i += 0.5) {
      float gridLine = drawLine(graphUV, i) * gridAlpha;
      if (gridLine > 0.0) {
        col = mix(col, vec3(0.4), gridLine);
        alpha = max(alpha, gridLine);
      }
    }

    float axisAlpha = 0.6;
    float axisLine = drawLine(graphUV, 0.0) * axisAlpha;
    if (axisLine > 0.0) {
      col = mix(col, vec3(0.2, 0.3, 0.5), axisLine);
      alpha = max(alpha, axisLine);
    }

    float x = graphUV.x;
    if (x >= -7.0 && x <= 3.0 && abs(graphUV.y) < 2.5) {
      float t = u_time * 0.5;
      float y1 = graphFunction1(x) * 0.7 + graphFunction2(x) * 0.5 +
                 sin(x * 3.0 + t * 2.0) * 0.15;

      float line1 = drawLine(graphUV, y1);
      vec3 lineColor1 = vec3(0.1, 0.3, 0.9);
      if (line1 > 0.0) {
        col = mix(col, lineColor1, line1 * 1.2);
        alpha = max(alpha, line1 * 1.2);
      }

      float y2 = graphFunction5(x);
      float line2 = drawLine(graphUV, y2);
      vec3 lineColor2 = vec3(0.1, 0.6, 0.3);
      if (line2 > 0.0) {
        col = mix(col, lineColor2, line2 * 1.2);
        alpha = max(alpha, line2 * 1.2);
      }

      float y3 = sin(x * 1.5 + t * 0.8) * 0.3 + cos(x * 2.2 + t * 1.1) * 0.25;
      float line3 = drawLine(graphUV, y3);
      vec3 lineColor3 = vec3(0.9, 0.5, 0.2);
      if (line3 > 0.0) {
        col = mix(col, lineColor3, line3 * 0.8);
        alpha = max(alpha, line3 * 0.8);
      }

      float trendY = 0.3 * x + 0.2;
      float trendLine = drawTrendLine(graphUV, x, 0.3, 0.2);
      vec3 trendColor = vec3(0.6, 0.6, 0.8);
      if (trendLine > 0.0) {
        col = mix(col, trendColor, trendLine * 0.4);
        alpha = max(alpha, trendLine * 0.4);
      }

      float pointRadius = 0.02;
      for (float i = -7.0; i <= 3.0; i += 0.3) {
        float px = i;
        float py1 = graphFunction1(px) * 0.7 + graphFunction2(px) * 0.5 +
                    sin(px * 3.0 + t * 2.0) * 0.15;
        float point1 = drawPoint(graphUV, vec2(px, py1), pointRadius);
        if (point1 > 0.0) {
          col = mix(col, vec3(0.0, 0.2, 0.8), point1 * 1.0);
          alpha = max(alpha, point1 * 1.0);
        }

        float py2 = graphFunction5(px);
        float point2 = drawPoint(graphUV, vec2(px, py2), pointRadius);
        if (point2 > 0.0) {
          col = mix(col, vec3(0.0, 0.5, 0.2), point2 * 1.0);
          alpha = max(alpha, point2 * 1.0);
        }

        float py3 = sin(px * 1.5 + t * 0.8) * 0.3 + cos(px * 2.2 + t * 1.1) * 0.25;
        float point3 = drawPoint(graphUV, vec2(px, py3), pointRadius * 0.8);
        if (point3 > 0.0) {
          col = mix(col, vec3(0.8, 0.4, 0.1), point3 * 0.9);
          alpha = max(alpha, point3 * 0.9);
        }
      }

    }

    vec2 cloud1Pos = vec2(0.0, 0.4) + vec2(sin(u_time * 0.3) * 0.2, cos(u_time * 0.2) * 0.1);
    float cloud1 = drawCloud(centered, cloud1Pos, 0.18, 0.5);
    if (cloud1 > 0.0) {
      col = mix(col, vec3(0.7, 0.85, 1.0), cloud1 * 0.7);
      alpha = max(alpha, cloud1 * 0.7);
    }

    vec2 cloud2Pos = vec2(-0.6, 0.3) + vec2(cos(u_time * 0.25) * 0.15, sin(u_time * 0.3) * 0.12);
    float cloud2 = drawCloud(centered, cloud2Pos, 0.15, 0.45);
    if (cloud2 > 0.0) {
      col = mix(col, vec3(0.75, 0.88, 1.0), cloud2 * 0.65);
      alpha = max(alpha, cloud2 * 0.65);
    }

    vec2 cloud3Pos = vec2(0.2, -0.35) + vec2(sin(u_time * 0.2) * 0.18, cos(u_time * 0.25) * 0.1);
    float cloud3 = drawCloud(centered, cloud3Pos, 0.16, 0.48);
    if (cloud3 > 0.0) {
      col = mix(col, vec3(0.72, 0.86, 1.0), cloud3 * 0.68);
      alpha = max(alpha, cloud3 * 0.68);
    }

    vec2 cloud4Pos = vec2(-0.5, -0.25) + vec2(cos(u_time * 0.22) * 0.16, sin(u_time * 0.28) * 0.11);
    float cloud4 = drawCloud(centered, cloud4Pos, 0.14, 0.42);
    if (cloud4 > 0.0) {
      col = mix(col, vec3(0.78, 0.9, 1.0), cloud4 * 0.66);
      alpha = max(alpha, cloud4 * 0.66);
    }

    vec2 cloud5Pos = vec2(0.4, 0.1) + vec2(sin(u_time * 0.28) * 0.14, cos(u_time * 0.22) * 0.09);
    float cloud5 = drawCloud(centered, cloud5Pos, 0.13, 0.4);
    if (cloud5 > 0.0) {
      col = mix(col, vec3(0.74, 0.87, 1.0), cloud5 * 0.64);
      alpha = max(alpha, cloud5 * 0.64);
    }

    vec2 cloud6Pos = vec2(-0.3, -0.2) + vec2(cos(u_time * 0.26) * 0.12, sin(u_time * 0.24) * 0.08);
    float cloud6 = drawCloud(centered, cloud6Pos, 0.15, 0.43);
    if (cloud6 > 0.0) {
      col = mix(col, vec3(0.76, 0.89, 1.0), cloud6 * 0.67);
      alpha = max(alpha, cloud6 * 0.67);
    }

    for (float i = 0.0; i < 15.0; i++) {
      float sparkTime = u_time * 0.8 + i * 0.5;
      float sparkX = -6.0 + mod(i * 0.7, 10.0);
      float sparkY = graphFunction1(sparkX) * 0.7 + graphFunction2(sparkX) * 0.5 +
                     sin(sparkX * 3.0 + u_time) * 0.15;
      vec2 sparkPos = vec2(sparkX, sparkY);
      float spark = drawSpark(graphUV, sparkPos, sparkTime, 2.0);
      if (spark > 0.0) {
        vec3 sparkColor = vec3(1.0, 0.9, 0.3) * (0.9 + sin(sparkTime * 5.0) * 0.1);
        col = mix(col, sparkColor, spark * 1.2);
        alpha = max(alpha, spark * 1.2);
      }
    }

    for (float i = 0.0; i < 10.0; i++) {
      float sparkTime = u_time * 0.6 + i * 0.7;
      float sparkX = -5.5 + mod(i * 0.8, 9.0);
      float sparkY = graphFunction5(sparkX);
      vec2 sparkPos = vec2(sparkX, sparkY);
      float spark = drawSpark(graphUV, sparkPos, sparkTime, 2.5);
      if (spark > 0.0) {
        vec3 sparkColor = vec3(0.3, 1.0, 0.5) * (0.8 + cos(sparkTime * 4.0) * 0.2);
        col = mix(col, sparkColor, spark * 1.0);
        alpha = max(alpha, spark * 1.0);
      }
    }

    for (float i = -6.0; i <= 2.0; i += 1.5) {
      float labelX = i;
      float labelY = graphFunction1(labelX) * 0.7 + graphFunction2(labelX) * 0.5 +
                     sin(labelX * 3.0 + u_time) * 0.15;
      float label = drawPoint(graphUV, vec2(labelX, labelY), 0.025);
      if (label > 0.0) {
        vec3 labelColor = vec3(0.0, 0.2, 0.8);
        col = mix(col, labelColor, label * 1.1);
        alpha = max(alpha, label * 1.1);

        float glow = drawPoint(graphUV, vec2(labelX, labelY), 0.04);
        if (glow > 0.0) {
          col = mix(col, vec3(0.0, 0.2, 0.8) * 0.3, glow * 0.5);
          alpha = max(alpha, glow * 0.5);
        }
      }
    }

    gl_FragColor = vec4(col, alpha);
  }
`
