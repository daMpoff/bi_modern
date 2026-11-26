// Adapted from Ascii Aquarium by Louis Studios. See LICENSE.txt.
import { FISH, SHOALS } from './choreography';

const WAKE_TILE = 2;
const WAKE_TILE_A = 0.35;
const WAKE_DOT_A = 0.75;
const EDGE_LO = 0.86;
const HI_P = [0.14, 0.14, 0.13, 0.13];
const HI_D = [0.5, 0.5, 0.45, 0.5];
const HI_S0 = [20, 20, 30, 20];
const HI_S1 = [110, 120, 130, 110];
const BUB_SIDE = [12, 16, 24, 16];
const FACE = 0.9;

/* ------------------------------------------------------------------------------------------------
   Geometry shared by every fish: spine samples from 30 px in front of the head to 297 px behind it.
------------------------------------------------------------------------------------------------ */
const S0 = -30;
const SSTEP = 3;
const NS = 110;
const KEY = 3; // reference frames per pose keyframe
const LOOP = 908; // frames in one shoal loop (30 per second); every fish has its own cycle
const WORLD_W = 1276.8;
const WORLD_H = 683;
const WAKE_N = 16;

function b64i16(s: string): Int16Array {
  const bin = atob(s);
  const out = new Int16Array(bin.length >> 1);
  for (let i = 0; i < out.length; i++) {
    const v = bin.charCodeAt(2 * i) | (bin.charCodeAt(2 * i + 1) << 8);
    out[i] = v > 32767 ? v - 65536 : v;
  }
  return out;
}

function hash(a: number, b: number, c: number): number {
  let h = Math.imul(a | 0, 374761393) ^ Math.imul(b | 0, 668265263) ^ Math.imul(c | 0, 2246822519);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}

function parseColor(c: string): [number, number, number] {
  const s = c.trim();
  if (s[0] === "#") {
    const h = s.length <= 5 ? s.slice(1, 4).split("").map((x) => x + x).join("") : s.slice(1, 7);
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }
  const m = s.match(/[\d.]+/g);
  if (m && m.length >= 3) return [+m[0], +m[1], +m[2]];
  return [128, 128, 128];
}

const rgbStr = (r: number, g: number, b: number, a = 1) =>
  a >= 1 ? `rgb(${r | 0},${g | 0},${b | 0})` : `rgba(${r | 0},${g | 0},${b | 0},${a.toFixed(3)})`;

/** Tile colour at brightness b: darker tiles deepen and saturate, brighter ones flare toward the highlight. */
function tone(base: [number, number, number], b: number, hi: [number, number, number]): [number, number, number] {
  const e = 1 / Math.pow(Math.max(0.05, Math.min(b, 1.6)), 0.7);
  const out: [number, number, number] = [0, 0, 0];
  for (let i = 0; i < 3; i++) out[i] = Math.min(255, 255 * Math.min(b, 1.25) * Math.pow(base[i] / 255, e));
  if (b > 1.3) {
    const m = Math.min(1, (b - 1.3) / 0.5);
    for (let i = 0; i < 3; i++) out[i] += (hi[i] - out[i]) * m;
  }
  return out;
}

type Decoded = {
  poses: Float32Array[]; // per fish: frames * 5
  bot: Float32Array[];
  top: Float32Array[];
  strokes: Float32Array[]; // per fish: s0, d0, s1, d1 of each thin fin or tail line
  shade: Float32Array[];
  shoals: { kind: number; count: number; sx: number; sy: number; path: Float32Array; seed: number }[];
};

let DECODED: Decoded | null = null;
function decode(): Decoded {
  if (DECODED) return DECODED;
  const poses: Float32Array[] = [];
  const bot: Float32Array[] = [];
  const top: Float32Array[] = [];
  const shade: Float32Array[] = [];
  const strokes: Float32Array[] = [];
  for (let f = 0; f < FISH.length; f++) {
    const raw = b64i16(FISH[f].pose);
    const n = raw.length / 5;
    const p = new Float32Array(n * 5);
    for (let i = 0; i < n; i++) {
      p[i * 5] = raw[i * 5] / 2;
      p[i * 5 + 1] = raw[i * 5 + 1] / 2;
      p[i * 5 + 2] = raw[i * 5 + 2] / 2000;
      p[i * 5 + 3] = raw[i * 5 + 3] / 1e5;
      p[i * 5 + 4] = raw[i * 5 + 4] / 1e5;
    }
    poses.push(p);
    const sh = b64i16(FISH[f].shape);
    const b = new Float32Array(NS);
    const t = new Float32Array(NS);
    const g = new Float32Array(NS);
    for (let i = 0; i < NS; i++) {
      b[i] = sh[i] === -999 ? 999 : sh[i];
      t[i] = sh[NS + i] === -999 ? -999 : sh[NS + i];
      g[i] = sh[2 * NS + i] / 100;
    }
    bot.push(b);
    top.push(t);
    shade.push(g);
    strokes.push(Float32Array.from(b64i16(FISH[f].strokes)));
  }
  const shoals = SHOALS.map((s) => ({ kind: s.kind, count: s.count, sx: s.sx, sy: s.sy, seed: s.seed, path: Float32Array.from(b64i16(s.path), (v) => v / 4) }));
  DECODED = { poses, bot, top, shade, strokes, shoals };
  return DECODED;
}

/** Catmull-Rom sample of a looping keyframe track with `stride` values per key. */
function sampleLoop(arr: Float32Array, stride: number, keys: number, u: number, out: Float32Array, unwrap = -1) {
  const i1 = Math.floor(u);
  const f = u - i1;
  const k0 = (((i1 - 1) % keys) + keys) % keys;
  const k1 = ((i1 % keys) + keys) % keys;
  const k2 = (k1 + 1) % keys;
  const k3 = (k1 + 2) % keys;
  const f2 = f * f;
  const f3 = f2 * f;
  for (let c = 0; c < stride; c++) {
    let p0 = arr[k0 * stride + c];
    const p1 = arr[k1 * stride + c];
    let p2 = arr[k2 * stride + c];
    let p3 = arr[k3 * stride + c];
    if (c === unwrap) {
      const w = (a: number, ref: number) => a - Math.round((a - ref) / (2 * Math.PI)) * 2 * Math.PI;
      p0 = w(p0, p1);
      p2 = w(p2, p1);
      p3 = w(p3, p2);
    }
    out[c] = 0.5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2 + (-p0 + 3 * p1 - 3 * p2 + p3) * f3);
  }
}

const GLYPHS = ["S", "t", "%", "X", "$", "S", "t", "%", "X", ";", "c", "S"];
const HI_GLYPHS = ["@", "8", "@", "8", "%"];

const SCENE = {
  font: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
  cellWidth: 10,
  cellHeight: 14.25,
};
export const FRAMES_PER_SECOND = 24;
export const STILL_AT = 2;

const PALETTES = {
  dark: {
    water: '#061419',
    grid: '#102328',
    fish: ['#c08a52', '#d08a38', '#68a3cb', '#5567e9'].map(parseColor),
    highlight: parseColor('#eaf3fb'),
    wake: parseColor('#738d94'),
    shoal: parseColor('#8da6ac'),
    minnows: parseColor('#a3c0c5'),
    drift: parseColor('#7782ac'),
    bubbles: parseColor('#cde8e9'),
  },
  light: {
    water: '#f2f7f4',
    grid: '#e4eee9',
    fish: ['#b96932', '#ca8243', '#287f83', '#396197'].map(parseColor),
    highlight: parseColor('#fff1c9'),
    wake: parseColor('#6d9690'),
    shoal: parseColor('#557f7b'),
    minnows: parseColor('#4f7077'),
    drift: parseColor('#697998'),
    bubbles: parseColor('#538984'),
  },
};

export function createAquariumPainter(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D) {
  const D = decode();
  const NF = D.poses.length;
  const keys = D.poses.map((p) => p.length / 5);

  let W = 0;
  let H = 0;
  let dpr = 1;
  let cols = 0;
  let rows = 0;
  let sc = 1;
  let ox = 0;
  let oy = 0;
  let owner = new Int8Array(0);
  let cellS = new Float32Array(0);
  let cellD = new Float32Array(0);
  let wakeRing: Int8Array[] = [];
  let wakeTick: number[] = [];

  const resize = () => {
    const r = canvas.getBoundingClientRect();
    const ratio = Math.min(3, window.devicePixelRatio || 1);
    if (W === r.width && H === r.height && dpr === ratio) return false;
    W = Math.max(1, r.width);
    H = Math.max(1, r.height);
    dpr = ratio;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    cols = Math.ceil(W / SCENE.cellWidth) + 1;
    rows = Math.ceil(H / SCENE.cellHeight) + 1;
    sc = Math.max(W / WORLD_W, H / WORLD_H);
    ox = (W - WORLD_W * sc) / 2;
    oy = (H - WORLD_H * sc) / 2;
    owner = new Int8Array(cols * rows);
    cellS = new Float32Array(cols * rows);
    cellD = new Float32Array(cols * rows);
    wakeRing = [];
    wakeTick = [];
    for (let i = 0; i < WAKE_N; i++) {
      wakeRing.push(new Int8Array(cols * rows));
      wakeTick.push(-1e9);
    }
    lastKey = -1;
    return true;
  };

  // Spine scratch.
  const px = new Float32Array(NS);
  const py = new Float32Array(NS);
  const pc = new Float32Array(NS);
  const ps = new Float32Array(NS);
  const pose = new Float32Array(5);
  const qa = new Float32Array(2);
  const qb = new Float32Array(2);
  /** Rasterise every fish at reference frame `ft` into `own` (and s/d into the cell arrays when given). */
  const raster = (ft: number, own: Int8Array, withSD: boolean) => {
    own.fill(-1);
    const cw = SCENE.cellWidth;
    const ch = SCENE.cellHeight;
    for (let f = 0; f < NF; f++) {
      sampleLoop(D.poses[f], 5, keys[f], ft / KEY, pose, 2);
      const [hx, hy, th, ka, kb] = pose;
      let cx = 0;
      let cy = 0;
      let minX = 1e9;
      let maxX = -1e9;
      let minY = 1e9;
      let maxY = -1e9;
      const i0 = 10;
      for (let i = 0; i < NS; i++) {
        const s = S0 + i * SSTEP;
        const sp = Math.max(s, 0);
        const phi = th + ka * s + (kb * sp * sp) / 300;
        const c = Math.cos(phi);
        const sn = Math.sin(phi);
        pc[i] = c;
        ps[i] = sn;
        cx -= c * SSTEP;
        cy -= sn * SSTEP;
        px[i] = cx;
        py[i] = cy;
      }
      const bx = px[i0];
      const by = py[i0];
      const bot = D.bot[f];
      const top = D.top[f];
      let reach = 0;
      for (let i = 0; i < NS; i++) {
        px[i] = ox + (hx + px[i] - bx) * sc;
        py[i] = oy + (hy + py[i] - by) * sc;
        if (bot[i] < 900) {
          reach = Math.max(reach, Math.abs(bot[i]), Math.abs(top[i]));
          if (px[i] < minX) minX = px[i];
          if (px[i] > maxX) maxX = px[i];
          if (py[i] < minY) minY = py[i];
          if (py[i] > maxY) maxY = py[i];
        }
      }
      const pad = (reach + 4) * sc;
      const c0 = Math.max(0, Math.floor((minX - pad) / cw));
      const c1 = Math.min(cols - 1, Math.ceil((maxX + pad) / cw));
      const r0 = Math.max(0, Math.floor((minY - pad) / ch));
      const r1 = Math.min(rows - 1, Math.ceil((maxY + pad) / ch));
      for (let r = r0; r <= r1; r++) {
        const qy = (r + 0.5) * ch;
        for (let c = c0; c <= c1; c++) {
          const qx = (c + 0.5) * cw;
          // Nearest spine sample: coarse pass then a local one.
          let bj = 0;
          let bd = 1e18;
          for (let i = 0; i < NS; i += 4) {
            const dx = qx - px[i];
            const dy = qy - py[i];
            const d2 = dx * dx + dy * dy;
            if (d2 < bd) {
              bd = d2;
              bj = i;
            }
          }
          const lo = Math.max(0, bj - 4);
          const hi = Math.min(NS - 1, bj + 4);
          for (let i = lo; i <= hi; i++) {
            const dx = qx - px[i];
            const dy = qy - py[i];
            const d2 = dx * dx + dy * dy;
            if (d2 < bd) {
              bd = d2;
              bj = i;
            }
          }
          if (bj === 0 || bj === NS - 1) continue;
          const dx = (qx - px[bj]) / sc;
          const dy = (qy - py[bj]) / sc;
          const sd = -dx * ps[bj] + dy * pc[bj];
          const sa = S0 + bj * SSTEP - (dx * pc[bj] + dy * ps[bj]);
          const k = Math.round((sa - S0) / SSTEP);
          if (k < 0 || k >= NS) continue;
          if (sd < bot[k] || sd > top[k]) continue;
          const idx = r * cols + c;
          own[idx] = f;
          if (withSD) {
            cellS[idx] = sa;
            cellD[idx] = (sd - bot[k]) / Math.max(1, top[k] - bot[k]);
          }
        }
      }
      // Thin fins and tails: one cell wide, stepping cell by cell along each line.
      const st = D.strokes[f];
      const mark = (u: number, v: number, s: number) => {
        const c = Math.floor(u);
        const r = Math.floor(v);
        if (c < 0 || r < 0 || c >= cols || r >= rows) return;
        const idx = r * cols + c;
        own[idx] = f;
        if (withSD) {
          cellS[idx] = s;
          cellD[idx] = 0.2;
        }
      };
      const at = (s: number, d: number, o: Float32Array) => {
        const x = (s - S0) / SSTEP;
        const i = Math.max(0, Math.min(NS - 2, Math.floor(x)));
        const t = Math.max(0, Math.min(1, x - i));
        const c = pc[i] + (pc[i + 1] - pc[i]) * t;
        const sn = ps[i] + (ps[i + 1] - ps[i]) * t;
        o[0] = (px[i] + (px[i + 1] - px[i]) * t - sn * d * sc) / cw;
        o[1] = (py[i] + (py[i + 1] - py[i]) * t + c * d * sc) / ch;
      };
      for (let j = 0; j + 3 < st.length; j += 4) {
        const s0 = st[j];
        const d0 = st[j + 1];
        const s1 = st[j + 2];
        const d1 = st[j + 3];
        const n = Math.max(2, Math.ceil(Math.hypot(s1 - s0, d1 - d0) / 1.5));
        at(s0, d0, qa);
        mark(qa[0], qa[1], s0);
        for (let i = 1; i <= n; i++) {
          const s = s0 + ((s1 - s0) * i) / n;
          at(s, d0 + ((d1 - d0) * i) / n, qb);
          const du = qb[0] - qa[0];
          const dv = qb[1] - qa[1];
          if (Math.abs(du) >= Math.abs(dv)) {
            const lo = Math.min(qa[0], qb[0]) - 0.5;
            const hi = Math.max(qa[0], qb[0]) - 0.5;
            for (let k = Math.floor(lo) + 1; k <= Math.floor(hi); k++) mark(k + 0.5, qa[1] + (dv * (k + 0.5 - qa[0])) / du, s);
          } else {
            const lo = Math.min(qa[1], qb[1]) - 0.5;
            const hi = Math.max(qa[1], qb[1]) - 0.5;
            for (let k = Math.floor(lo) + 1; k <= Math.floor(hi); k++) mark(qa[0] + (du * (k + 0.5 - qa[1])) / dv, k + 0.5, s);
          }
          qa[0] = qb[0];
          qa[1] = qb[1];
        }
        mark(qa[0], qa[1], s1);
      }
    }
  };
  let lastKey = -1;
  const draw = (time: number, theme: keyof typeof PALETTES = 'dark') => {
    const { water, grid, fish: fishRGB, highlight: hiRGB, wake: wakeRGB,
      shoal: shoalRGB, minnows: minRGB, drift: drRGB, bubbles: bubRGB } = PALETTES[theme];
    const cw = SCENE.cellWidth;
    const ch = SCENE.cellHeight;
    const tick = Math.floor(time * FRAMES_PER_SECOND + 1e-6);
    const ft = (tick * 30) / FRAMES_PER_SECOND; // reference frames since the start; each fish wraps on its own cycle
    const fr = ((ft % LOOP) + LOOP) % LOOP; // shoal loop
    const ltm = Math.max(1, Math.round((LOOP * FRAMES_PER_SECOND) / 30));
    const lt = ((tick % ltm) + ltm) % ltm; // seeds the flicker
    const key = tick;

    // Wake history: rasterise the frames we have not seen yet.
    if (key !== lastKey) {
      const fresh = lastKey < 0 || key < lastKey || key - lastKey > WAKE_N ? WAKE_N : key - lastKey;
      for (let j = fresh; j >= 1; j--) {
        const kk = key - j;
        const slot = ((kk % WAKE_N) + WAKE_N) % WAKE_N;
        if (wakeTick[slot] === kk) continue;
        const frk = (kk * 30) / FRAMES_PER_SECOND;
        raster(frk, wakeRing[slot], false);
        wakeTick[slot] = kk;
      }
      lastKey = key;
    }
    raster(ft, owner, true);

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = water;
    ctx.fillRect(0, 0, W, H);

    // Grid.
    ctx.fillStyle = grid;
    const lw = 1 / dpr;
    for (let c = 0; c <= cols; c++) {
      const x = Math.round(c * cw * dpr) / dpr;
      ctx.fillRect(x, 0, lw, H);
    }
    for (let r = 0; r <= rows; r++) {
      const y = Math.round(r * ch * dpr) / dpr;
      ctx.fillRect(0, y, W, lw);
    }

    // Wake: fading tiles where a body just was, then dots.
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const idx = r * cols + c;
        if (owner[idx] >= 0) continue;
        let age = 0;
        let who = -1;
        for (let j = 1; j <= WAKE_N; j++) {
          const slot = (((key - j) % WAKE_N) + WAKE_N) % WAKE_N;
          if (wakeTick[slot] !== key - j) break;
          const o = wakeRing[slot][idx];
          if (o >= 0) {
            age = j;
            who = o;
            break;
          }
        }
        if (who < 0) continue;
        const x = c * cw;
        const y = r * ch;
        if (age <= WAKE_TILE) {
          const [fr0, fg0, fb0] = fishRGB[who];
          const a = WAKE_TILE_A * (1 - (age - 1) / WAKE_TILE);
          ctx.fillStyle = rgbStr(fr0, fg0, fb0, a);
          ctx.fillRect(x + 1, y + 1, cw - 1, ch - 1);
        } else {
          const a = WAKE_DOT_A * (1 - (age - WAKE_TILE) / (WAKE_N - WAKE_TILE + 1));
          if (hash(c, r, lt) < 0.12) continue;
          ctx.fillStyle = rgbStr(wakeRGB[0], wakeRGB[1], wakeRGB[2], a);
          ctx.fillRect(x + cw / 2 - 1, y + ch / 2 - 1, 2, 2);
        }
      }
    }

    // Shoals.
    const smallFont = `600 ${Math.round(ch * 0.64)}px ${SCENE.font}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const ctr = new Float32Array(3);
    for (let si = 0; si < D.shoals.length; si++) {
      const S = D.shoals[si];
      const nk = S.path.length / 3;
      sampleLoop(S.path, 3, nk, (fr / LOOP) * nk, ctr);
      const scx = ox + ctr[0] * sc;
      const scy = oy + ctr[1] * sc;
      const rgb = S.kind === 0 ? shoalRGB : S.kind === 1 ? minRGB : drRGB;
      if (S.kind !== 0) ctx.font = smallFont;
      const visibleN = ctr[2];
      for (let m = 0; m < S.count; m++) {
        if (m >= visibleN) break;
        const h1 = hash(S.seed, m, 1);
        const h2 = hash(S.seed, m, 2);
        const h3 = hash(S.seed, m, 3);
        // Box-Muller for a soft cloud.
        const rr = Math.sqrt(-2 * Math.log(Math.max(1e-6, h1)));
        const gx = rr * Math.cos(6.2832 * h2);
        const gy = rr * Math.sin(6.2832 * h2);
        const ph = h3 * 6.2832;
        const tt = fr / 30;
        const wob = S.kind === 2 ? 5 : 1;
        const per = (2 * Math.PI) / (LOOP / 30);
        // Wobble on whole multiples of the loop so it closes seamlessly.
        const mx = scx + (gx * S.sx + Math.sin(tt * per * (S.kind === 2 ? 2 : 9) + ph) * 6 * wob) * sc;
        const my = scy + (gy * S.sy + Math.cos(tt * per * (S.kind === 2 ? 3 : 7) + ph * 1.3) * 4 * (S.kind === 2 ? 3 : 1)) * sc;
        // Minnows sit on every other column, so their glyphs never touch.
        const c = S.kind === 0 ? Math.floor(mx / cw) : 2 * Math.floor(mx / (2 * cw));
        const r = Math.floor(my / ch);
        if (c < 0 || r < 0 || c >= cols || r >= rows) continue;
        if (owner[r * cols + c] >= 0) continue;
        const fl = hash(si * 131 + m, lt, 7);
        if (fl < (S.kind === 0 ? 0.16 : 0.1)) continue;
        const a = 0.55 + 0.45 * hash(si * 131 + m, lt >> 1, 9);
        ctx.fillStyle = rgbStr(rgb[0], rgb[1], rgb[2], a);
        const x = c * cw;
        const y = r * ch;
        if (S.kind === 0) {
          const dw = Math.max(3, cw * 0.56);
          ctx.fillRect(Math.round((x + (cw - dw) / 2) * dpr) / dpr, Math.round((y + ch / 2 - 0.75) * dpr) / dpr, dw, 1.5);
        } else {
          ctx.fillText(S.kind === 1 ? "><" : ">=<", x + cw, y + ch / 2);
        }
      }
    }

    // Fish tiles: a lit rim, a dimmer face and a dark glyph, brightness drawn per cell.
    ctx.font = `500 ${Math.round(ch * 0.7)}px ${SCENE.font}`;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const idx = r * cols + c;
        const f = owner[idx];
        if (f < 0) continue;
        const sa = cellS[idx];
        const rd = cellD[idx];
        const k = Math.max(0, Math.min(NS - 1, Math.round((sa - S0) / SSTEP)));
        const edge = Math.min(rd, 1 - rd);
        const sx = Math.round(sa / 9);
        const sy = Math.round(rd * 5);
        const q = hash(c * 3 + f, r, (lt / 2) | 0);
        // Measured brightness spread of the reference tiles (quantiles 0, 10, 25, 50, 75, 100 %).
        let b = q < 0.1 ? 0.55 + q * 0.6 : q < 0.25 ? 0.61 + (q - 0.1) * 1.2 : q < 0.5 ? 0.79 + (q - 0.25) * 0.84 : q < 0.75 ? 1 + (q - 0.5) * 0.5 : 1.12 + (q - 0.75) * 0.8;
        b *= D.shade[f][k] * (EDGE_LO + (1 - EDGE_LO) * Math.min(1, edge * 3.2));
        const hiP = HI_P[f] * Math.max(0, 1 - Math.abs(rd - HI_D[f]) * 2.2) * (sa > HI_S0[f] && sa < HI_S1[f] ? 1 : 0.2);
        const isHi = hash(c, r, (lt / 2) | 0) < hiP;
        if (isHi) b = 1.45 + 0.35 * hash(c, r, lt + 5);
        const base = fishRGB[f];
        const x = c * cw;
        const y = r * ch;
        const tw = cw - 1;
        const th2 = ch - 2;
        const rim = tone(base, b, hiRGB);
        ctx.fillStyle = rgbStr(rim[0], rim[1], rim[2]);
        ctx.fillRect(x + 0.5, y + 1, tw, th2);
        const face = tone(base, b * FACE, hiRGB);
        ctx.fillStyle = rgbStr(face[0], face[1], face[2]);
        ctx.fillRect(x + 1.5, y + 2.2, tw - 2, th2 - 2.4);
        const gsel = hash(sx * 3 + f * 17, sy * 5, (lt / 3) | 0);
        const ch0 = isHi ? HI_GLYPHS[Math.floor(gsel * HI_GLYPHS.length)] : GLYPHS[Math.floor(gsel * GLYPHS.length)];
        const baseLum = (0.299 * base[0] + 0.587 * base[1] + 0.114 * base[2]) / 255;
        const ink = baseLum > 0.3 || b > 0.72 ? tone(base, b * 0.3, hiRGB) : tone(base, Math.max(1.2, b * 1.9), hiRGB);
        ctx.fillStyle = rgbStr(ink[0], ink[1], ink[2]);
        ctx.fillText(ch0, x + cw / 2, y + ch / 2 + 0.5);
      }
    }

    // Bubbles at the mouths.
    ctx.strokeStyle = rgbStr(bubRGB[0], bubRGB[1], bubRGB[2], 0.9);
    ctx.lineWidth = 1.2;
    const ring = (c: number, r: number) => {
      if (c < 0 || r < 0 || c >= cols || r >= rows) return;
      if (owner[r * cols + c] >= 0) return;
      ctx.beginPath();
      ctx.arc(c * cw + cw / 2, r * ch + ch / 2 + 1, Math.min(cw, ch) * 0.2, 0, 6.2832);
      ctx.stroke();
    };
    for (let f = 0; f < NF; f++) {
      sampleLoop(D.poses[f], 5, keys[f], ft / KEY, pose, 2);
      const nb = hash(f, lt, 21) < 0.55 ? 1 : hash(f, lt, 22) < 0.4 ? 2 : 0;
      for (let b = 0; b < nb; b++) {
        const along = -14 + 26 * hash(f, lt, 30 + b);
        const side = (hash(f, lt, 40 + b) - 0.5) * 2 * BUB_SIDE[f];
        const wx = pose[0] - Math.cos(pose[2]) * along - Math.sin(pose[2]) * side;
        const wy = pose[1] - Math.sin(pose[2]) * along + Math.cos(pose[2]) * side;
        ring(Math.floor((ox + wx * sc) / cw), Math.floor((oy + wy * sc) / ch));
      }
    }
  };

  return { resize, draw };
}
