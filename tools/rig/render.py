"""Compositor: rasterises a character's body-part primitives (ellipsoids + sphere-swept limb chains) with an
orthographic z-buffer, then turns the result into pixel art:
  * 4-tone cel ramp per material (hi / base / shade / deep) from a fixed top-front light, far-side limbs one tone
    darker, hue-shifted ramps (palette.py)
  * dark selective outline on the silhouette, contact lines where a nearer part overlaps a farther one
  * 2D face decals (eyes, brows, mouth) placed at projected 3D landmarks of the head
  * clean-up with the project's pixfix rules (holes, islands, spurs, specks) -- measured by tools/v2/audit.py
Every primitive belongs to a named part (head, torso, upper_arm_R, ...), so parts can also be drawn alone."""
import os, sys, math
import numpy as np
from skeleton import K, PIVOT, CAM_S, CAM_U, CAM_V, project
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'v2'))
import pixfix as PF

N = 128
LIGHT = np.array([-0.30, 0.62, 0.72]); LIGHT /= np.linalg.norm(LIGHT)
_yy, _xx = np.mgrid[0:N, 0:N]
SX = _xx + 0.5; SY = _yy + 0.5
DIR = -CAM_V                                    # ray direction (into the screen); depth == ray t


class Canvas:
    def __init__(self):
        self.z = np.full((N, N), np.inf); self.mat = np.full((N, N), -1, int); self.part = np.full((N, N), -1, int)
        self.n = np.zeros((N, N, 3)); self.tone = np.zeros((N, N), int); self.tex = np.zeros((N, N))
        self.parts = []; self.mats = []

    def fill_pinholes(self, rounds=3):
        """a lone pixel of an under-layer showing through an outer shell (a rasterisation gap at a cut edge)
        takes the surrounding shell's surface, so it doesn't turn into a dark contact-line speck"""
        for _ in range(rounds):
            nbs = [(np.roll(np.roll(self.part, dy, 0), dx, 1), np.roll(np.roll(self.z, dy, 0), dx, 1), dy, dx)
                   for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))]
            p0 = nbs[0][0]
            same = np.ones_like(self.part, bool)
            for pn, zn, _, _ in nbs: same &= (pn == p0) & (zn < self.z - 1.0)
            hole = same & (self.part >= 0) & (p0 >= 0) & (p0 != self.part)
            occ = self.part >= 0
            nocc = sum(np.roll(np.roll(occ, dy, 0), dx, 1).astype(int) for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)))
            up = (np.roll(occ, 1, 0) & np.roll(occ, -1, 0)) | (np.roll(occ, 1, 1) & np.roll(occ, -1, 1))
            hole |= ~occ & (nocc >= 3) & up          # an empty pinhole inside the body
            if not hole.any(): break
            ys, xs = np.nonzero(hole); sy, sx = (ys - 1) % N, xs   # copy from the pixel above (same shell)
            sx2 = xs; sy2 = (ys + 1) % N
            self.z[ys, xs] = 0.5 * (self.z[sy, sx] + self.z[sy2, sx2])
            n = self.n[sy, sx] + self.n[sy2, sx2]; self.n[ys, xs] = n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
            for a in (self.mat, self.part, self.tone, self.tex): a[ys, xs] = a[sy, sx]

    def _id(self, lst, k):
        if k not in lst: lst.append(k)
        return lst.index(k)

    def _write(self, ys, xs, t, nrm, mat, part, tone_bias, tex):
        cur = self.z[ys, xs]; w = t < cur
        if not w.any(): return
        ys, xs, t, nrm = ys[w], xs[w], t[w], nrm[w]
        self.z[ys, xs] = t; self.n[ys, xs] = nrm
        self.mat[ys, xs] = self._id(self.mats, mat); self.part[ys, xs] = self._id(self.parts, part)
        self.tone[ys, xs] = tone_bias if np.isscalar(tone_bias) else tone_bias[w]; self.tex[ys, xs] = tex if np.isscalar(tex) else tex[w]

    def ellipsoid(self, c, A, mat, part, keep=None, tone=0, tex=0.0):
        """A: 3x3, columns = semi-axis vectors (world cm).  keep(q) -> bool mask on unit-space hit points."""
        c = np.asarray(c, float); A = np.asarray(A, float)
        cx, cy, _ = project(c)
        hx = K * np.linalg.norm(A.T @ CAM_S) + 1; hy = K * np.linalg.norm(A.T @ CAM_U) + 1
        x0, x1 = max(0, int(cx - hx)), min(N, int(cx + hx) + 2); y0, y1 = max(0, int(cy - hy)), min(N, int(cy + hy) + 2)
        if x0 >= x1 or y0 >= y1: return
        Ai = np.linalg.inv(A)
        sx = SX[y0:y1, x0:x1].ravel(); sy = SY[y0:y1, x0:x1].ravel()
        P0 = np.outer((sx - PIVOT[0]) / K, CAM_S) + np.outer((PIVOT[1] - sy) / K, CAM_U)
        q0 = (P0 - c) @ Ai.T; qd = Ai @ DIR
        a = qd @ qd; b = 2 * q0 @ qd; cc = (q0 * q0).sum(1) - 1
        disc = b * b - 4 * a * cc; hit = disc >= 0
        if not hit.any(): return
        sq = np.sqrt(np.maximum(disc, 0))
        t = (-b - sq) / (2 * a); q = q0 + np.outer(t, qd)
        if keep is not None:
            ok = keep(q)
            t2 = (-b + sq) / (2 * a); q2 = q0 + np.outer(t2, qd); ok2 = keep(q2)
            use2 = hit & ~ok & ok2
            t = np.where(use2, t2, t); q = np.where(use2[:, None], q2, q)
            hit &= (ok | ok2)
            back = use2
        else: back = np.zeros_like(hit)
        if not hit.any(): return
        nw = q @ Ai                                 # gradient direction (Ai^T q) in world coords
        nw = nw / np.linalg.norm(nw, axis=1, keepdims=True)
        nw[back] *= -1
        nc = np.stack([nw @ CAM_S, nw @ CAM_U, nw @ CAM_V], 1)
        ys = (sy[hit] - 0.5).astype(int); xs = (sx[hit] - 0.5).astype(int)
        tx = tex if np.isscalar(tex) else tex(q)[hit]
        self._write(ys, xs, t[hit], nc[hit], mat, part, tone + back[hit].astype(int), tx)

    def sphere(self, c, r, mat, part, tone=0, tex=0.0, axis=None):
        c = np.asarray(c, float); cx, cy, cd = project(c); rp = r * K
        x0, x1 = max(0, int(cx - rp - 1)), min(N, int(cx + rp) + 2); y0, y1 = max(0, int(cy - rp - 1)), min(N, int(cy + rp) + 2)
        if x0 >= x1 or y0 >= y1: return
        dx = (SX[y0:y1, x0:x1] - cx) / K; dy = (cy - SY[y0:y1, x0:x1]) / K
        d2 = dx * dx + dy * dy; hit = d2 < r * r
        if not hit.any(): return
        h = np.sqrt(r * r - d2[hit])
        t = cd - h
        nc = np.stack([dx[hit], dy[hit], h], 1) / r
        if axis is not None:             # inside a limb sweep: cylindrical normal (no per-sphere ripples)
            a = np.array([axis @ CAM_S, axis @ CAM_U, axis @ CAM_V]); a /= max(np.linalg.norm(a), 1e-9)
            nc = nc - np.outer(nc @ a, a); nn = np.linalg.norm(nc, axis=1, keepdims=True)
            nc = np.where(nn > 0.2, nc / np.maximum(nn, 1e-9), np.stack([dx[hit], dy[hit], h], 1) / r)
        ys, xs = np.nonzero(hit)
        self._write(ys + y0, xs + x0, t, nc, mat, part, tone, tex)

    def chain(self, p0, p1, r0, r1, mat, part, tone=0, tex=0.0, t0=0.0, t1=1.0, bulge=None):
        """tapered capsule p0->p1 as a sweep of spheres (radius r0->r1), optionally only the t0..t1 portion"""
        p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
        L = np.linalg.norm(p1 - p0); n = max(2, int(L * (t1 - t0) / max(0.35 * min(r0, r1), 0.4)) + 1)
        for t in np.linspace(t0, t1, n):
            r = r0 + (r1 - r0) * t
            if bulge is not None: r += bulge(t)
            ax = (p1 - p0) / max(L, 1e-9) if 0.12 < t < 0.88 or (t0 > 0 or t1 < 1) else None
            self.sphere(p0 + (p1 - p0) * t, r, mat, part, tone, tex, axis=ax)


def shade(cv, ramps, mats_order, tex_fn=None):
    """-> index image into the global palette: ramps[mat] = list of 5 palette indices (hi, base, sh, deep, outline)"""
    out = np.full((N, N), -1, int)
    op = cv.mat >= 0
    if not op.any(): return out, op
    lam = np.einsum('ijk,k->ij', cv.n, LIGHT)
    tone = np.where(lam > 0.80, 0, np.where(lam > 0.30, 1, np.where(lam > -0.15, 2, 3)))
    tone = np.clip(tone + cv.tone, 0, 3)
    # texture (hair streaks etc.): tex in [0,1) shifts one tone where set
    tone = np.where(op & (cv.tex > 0.5) & (cv.tex < 2.5) & (tone < 3), tone + 1, tone)
    tone = np.where(op & (cv.tex < -0.5) & (tone > 0), tone - 1, tone)
    # an isolated deep-tone pixel inside one material is a crease where two volumes meet, not a shadow: lift it
    d3 = op & (tone == 3)
    nb3 = sum(np.roll(np.roll(d3 & (cv.mat == np.roll(np.roll(cv.mat, -dy, 0), -dx, 1)), dy, 0), dx, 1).astype(int)
              for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)))
    tone = np.where(d3 & (nb3 == 0), 2, tone)
    for mi, m in enumerate(cv.mats):
        sel = cv.mat == mi
        r = ramps[m]
        out[sel] = np.array(r)[tone[sel]]
        if m + '_alt' in ramps:          # tex >= 2.5 marks a second material painted on the same surface (logo, dots, buckle)
            alt = sel & (cv.tex > 2.5); out[alt] = np.array(ramps[m + '_alt'])[np.minimum(tone[alt], 2)]
    # contact lines: a pixel whose 4-neighbour belongs to a different part and is clearly nearer -> deep tone
    z = np.where(op, cv.z, np.inf)
    line = np.zeros_like(op)
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        zn = np.roll(np.roll(z, dy, 0), dx, 1); pn = np.roll(np.roll(cv.part, dy, 0), dx, 1)
        line |= op & (zn < z - 3.2) & (pn != cv.part) & (pn >= 0)
    for mi, m in enumerate(cv.mats):
        sel = line & (cv.mat == mi); out[sel] = ramps[m][3]
    return out, op


def outline(out, cv, ramps):
    op = out >= 0
    edge = op & ~(np.roll(op, 1, 0) & np.roll(op, -1, 0) & np.roll(op, 1, 1) & np.roll(op, -1, 1))
    for mi, m in enumerate(cv.mats):
        sel = edge & (cv.mat == mi); out[sel] = ramps[m][4]
    return out


def finish(out, pal, protect=None):
    sh = PF.Shades(pal)
    out = PF.polish(out, pal, protect=protect)
    for _ in range(3):
        nxt = PF.enforce_outline(audit_fix(PF.despeckle(out, pal, protect), pal), pal, sh)
        if np.array_equal(nxt, out): break
        out = nxt
    return audit_fix(out, pal, rounds=1)


def audit_fix(out, pal, rounds=3):
    """last pass with the project's own audit rules: tiny enclosed holes and near-shade orphan specks take the
    most common neighbouring palette index"""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'v2'))
    import audit as AU
    for _ in range(rounds):
        r = AU.audit_frame(to_rgba(out, pal))
        bad = r['hole'] | r['speck']
        if not bad.any(): break
        nb = np.stack([np.roll(np.roll(out, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx], -1)
        for y, x in np.argwhere(bad):
            v = nb[y, x]; v = v[(v >= 0) & (v != out[y, x])]
            if not len(v): continue
            if r['speck'][y, x] and (out[max(y - 1, 0):y + 2, max(x - 1, 0):x + 2] < 0).any():
                out[y, x] = min(set(v.tolist()), key=lambda i: pal[i] @ (0.299, 0.587, 0.114))   # edge: keep it dark
            else: out[y, x] = np.bincount(v).argmax()
    return out


def to_rgba(idx, pal):
    im = np.zeros((N, N, 4), np.uint8); op = idx >= 0
    im[op, :3] = pal[idx[op]]; im[op, 3] = 255
    return im
