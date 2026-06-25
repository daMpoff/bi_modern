<script setup>
/**
 * GraphCloudShader - WebGL shader with animated graph and cloud visualization
 * Creates dynamic data visualization with graph lines, particles and clouds
 */

import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { vertexShaderSource, fragmentShaderSource } from '../js/shader-sources.js'

const canvasRef = ref(null)
let gl = null
let program = null
let animationFrame = null
let startTime = null
let positionBuffer = null
let resizeObserver = null
let resizeTimeout = null
let resizeHandler = null

function createShader(glCtx, type, source) {
  const shader = glCtx.createShader(type)
  glCtx.shaderSource(shader, source)
  glCtx.compileShader(shader)

  if (!glCtx.getShaderParameter(shader, glCtx.COMPILE_STATUS)) {
    logError('Shader compilation error:', glCtx.getShaderInfoLog(shader))
    glCtx.deleteShader(shader)
    return null
  }

  return shader
}

function createProgram(glCtx, vs, fs) {
  const prog = glCtx.createProgram()
  glCtx.attachShader(prog, vs)
  glCtx.attachShader(prog, fs)
  glCtx.linkProgram(prog)

  if (!glCtx.getProgramParameter(prog, glCtx.LINK_STATUS)) {
    logError('Program linking error:', glCtx.getProgramInfoLog(prog))
    glCtx.deleteProgram(prog)
    return null
  }

  return prog
}

function initWebGL() {
  const canvas = canvasRef.value
  if (!canvas) return

  gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: false })
       || canvas.getContext('experimental-webgl', { alpha: true, premultipliedAlpha: false })
  if (!gl) return

  const vs = createShader(gl, gl.VERTEX_SHADER, vertexShaderSource)
  const fs = createShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource)
  if (!vs || !fs) return

  program = createProgram(gl, vs, fs)
  if (!program) return

  gl.deleteShader(vs)
  gl.deleteShader(fs)

  positionBuffer = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
    -1, -1, 1, -1, -1, 1, 1, 1
  ]), gl.STATIC_DRAW)

  startTime = performance.now()

  function resize() {
    if (!canvas || !gl) return
    const rect = canvas.getBoundingClientRect()
    if (rect.width === 0 || rect.height === 0) return

    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const width = Math.floor(rect.width * dpr)
    const height = Math.floor(rect.height * dpr)

    if (canvas.width === width && canvas.height === height) return
    canvas.width = width
    canvas.height = height
    gl.viewport(0, 0, width, height)
  }

  function debouncedResize() {
    if (resizeTimeout) cancelAnimationFrame(resizeTimeout)
    resizeTimeout = requestAnimationFrame(resize)
  }

  resize()
  setTimeout(resize, 0)

  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(debouncedResize)
    resizeObserver.observe(canvas)
  }

  resizeHandler = debouncedResize
  window.addEventListener('resize', resizeHandler, { passive: true })

  const uTime = gl.getUniformLocation(program, 'u_time')
  const uResolution = gl.getUniformLocation(program, 'u_resolution')
  const aPosition = gl.getAttribLocation(program, 'a_position')

  function animate() {
    if (!gl || !program || !startTime) return

    const time = (performance.now() - startTime) / 1000.0

    gl.useProgram(program)

    if (uTime !== null) gl.uniform1f(uTime, time)
    if (uResolution !== null) gl.uniform2f(uResolution, canvas.width, canvas.height)

    gl.enableVertexAttribArray(aPosition)
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer)
    gl.vertexAttribPointer(aPosition, 2, gl.FLOAT, false, 0, 0)

    gl.clearColor(0, 0, 0, 0)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)

    animationFrame = requestAnimationFrame(animate)
  }

  animate()
}

function cleanup() {
  if (animationFrame) cancelAnimationFrame(animationFrame)
  if (resizeTimeout) cancelAnimationFrame(resizeTimeout)
  if (resizeObserver) resizeObserver.disconnect()
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (gl && positionBuffer) gl.deleteBuffer(positionBuffer)
  if (gl && program) gl.deleteProgram(program)
  gl = null
  program = null
}

onMounted(() => nextTick(initWebGL))
onUnmounted(cleanup)
</script>

<template>
  <canvas ref="canvasRef" class="graph-cloud-shader" />
</template>

<style scoped>
.graph-cloud-shader {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: none;
}
</style>
