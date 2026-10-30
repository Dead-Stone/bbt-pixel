"""Buffers from char_rig.render -> palette-indexed RGBA frame, with per-character decals and
projected face overlays (eyes / brows / mouth / glasses) applied after the outline pass."""
import numpy as np, math
import char_rig as R

def seg_dist(px, py, a, b):
    ax, ay = a; bx, by = b; dx, dy = bx-ax, by-ay
    h = np.clip(((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy), 0, 1)
    return np.hypot(px-ax-h*dx, py-ay-h*dy)
def segs_dist(a, w, segs):
    d = np.full(a.shape, 9e9)
    for s in segs:
        for i in range(len(s)-1): d = np.minimum(d, seg_dist(a, w, s[i], s[i+1]))
    return d

# ---- Sheldon emblem (original atom-bolt-in-circle) ----
EMB_C = (0.0, 63.0); EMB_R = 3.9
BOLT = [(1.3, 2.9), (-0.9, 0.2), (0.9, -0.1), (-1.3, -2.9)]
def emblem_code(a, w):
    da, dw = a-EMB_C[0], w-EMB_C[1]; r = np.hypot(da, dw)
    code = np.zeros(a.shape, int); code[r < EMB_R] = 1; code[(r >= EMB_R-0.85) & (r < EMB_R)] = 2
    code[(r < EMB_R-0.6) & (segs_dist(da, dw, [BOLT]) < 0.62)] = 3
    return code
FOLDS_FRONT = [[(-10.2, 50.6), (-7.6, 52.4), (-5.0, 54.9)], [(9.6, 50.0), (6.6, 51.8)], [(-1.5, 49.2), (1.8, 50.4)]]
FOLDS_BACK = [[(-5.0, 49.6), (-3.2, 52.6), (-2.6, 56.0)], [(6.0, 50.4), (4.0, 53.6)]]

def put(img, mask, name):
    img[mask, :3] = R.C[name]

def face_overlays(B, pose, yaw, eyes='open', glasses_dz=0.0):
    """returns list of (row, col, colour-name) in SOURCE orientation"""
    out = []
    hr = np.array(R.DIM['head']); tag, mat = B['tag'], B['mat']
    skin_i, hair_i = R.MATS.index('skin'), R.MATS.index('hair')
    head = (tag == 99) & (mat >= 0)
    skin = head & (mat == skin_i)
    op = mat >= 0; opp = np.pad(op, 1)
    edge = op & ~(opp[:-2,1:-1] & opp[2:,1:-1] & opp[1:-1,:-2] & opp[1:-1,2:])
    def surf(x, z, lift=0.0):
        s = 1 - (x/hr[0])**2 - (z/hr[2])**2
        return np.array([x, hr[1]*math.sqrt(max(s, 0.02)) + lift, z])
    def proj(q):
        c, r, _ = R.project_local(R.head_to_local(np.array(q, float), pose), yaw); return c, r
    def facing(q):
        n = np.array(q, float) / hr**2; n /= np.linalg.norm(n); return float(R.head_facing(n, pose, yaw))
    hc_col, _ = proj([0, 0, 0])
    def snap_in(r, c, allow_hair=False, gap=False):
        """move a feature pixel inward (toward head centre column) off the outline / off non-head pixels;
        gap=True also keeps one skin pixel between the feature and the outline (far eye in 3/4 views)"""
        step = 1 if c < hc_col else -1
        for _ in range(4):
            ok = 0 <= r < 128 and 0 <= c < 128 and (skin[r, c] or (allow_hair and head[r, c])) and not edge[r, c]
            if ok and gap: ok = not edge[r, c - step] and op[r, c - step]
            if ok: return r, c
            c += step
        return None
    is_leo = (R.CID == 'leonard')
    glas = R.CID in ('leonard', 'bernadette', 'amy')
    brow = pose.get('brow'); mouth = pose.get('mouth')
    eyes_info = []
    EZ = 1.2 if glas else 0.0
    for sx in (-3.9, 3.9):
        q = surf(sx, EZ); f = facing(q)
        if f < -0.02: continue
        c, r = proj(q); eyes_info.append((sx, f, c, r))
    if eyes_info:
        row_mean = int(math.floor(sum(e[3] for e in eyes_info) / len(eyes_info)))   # keep the eye line level
    if glas:
        out += glasses(B, pose, yaw, eyes_info, row_mean, facing, proj, surf, head, edge, eyes, glasses_dz) if eyes_info else []
        eyes_info = []
    for sx, f, c, r in eyes_info:
        c0, r0 = int(math.floor(c)), row_mean
        w = 2 if f > 0.72 else 1
        cols = [c0] if w == 1 else ([c0-1, c0] if (c - c0) < 0.5 else [c0, c0+1])
        far = f < 0.5
        rows = [r0-1, r0] if not is_leo else [r0]
        pix = []
        for cc in cols:
            p = snap_in(r0, cc, gap=far)
            if p: pix.append(p[1])
        pix = sorted(set(pix))
        if not pix: continue
        if is_leo:
            if eyes == 'open': out += [(r0, cc, 'ink_2') for cc in pix]
            elif eyes == 'half': out += [(r0, cc, 'skin_sh') for cc in pix]
        else:
            if eyes == 'open': out += [(rr, cc, 'ink_2') for rr in rows for cc in pix]
            elif eyes == 'half': out += [(rows[0], cc, 'skin_sh') for cc in pix] + [(rows[1], cc, 'ink_2') for cc in pix]
            else: out += [(rows[1], cc, 'skin_sh') for cc in pix]
            outward = pix[-1] + 1 if (c > hc_col) else pix[0] - 1
            br = rows[0] - 2 - (1 if brow == 'up' else 0)
            for cc in sorted(set(pix + [outward])):
                p = snap_in(br, cc, allow_hair=True)
                if p and p[1] == cc: out.append((br, cc, 'hair_sh'))
    # mouth
    q = surf(0.3, -3.4 if is_leo else (-5.0 if glas else -5.7)); f = facing(q)
    if f > 0.05:
        c, r = proj(q); c0, r0 = int(math.floor(c)), int(math.floor(r))
        n = 3 if f > 0.75 else 2
        cols = range(c0-1, c0+2) if n == 3 else ([c0-1, c0] if c < hc_col + 0.5 else [c0, c0+1])
        mcol = 'lips' if R.CID == 'penny' else 'skin_sh'
        if mouth in ('open', 'scowl'): mcol = 'ink_2'
        drawn = []
        for cc in cols:
            p = snap_in(r0, cc)
            if p and p[1] == cc: out.append((r0, cc, mcol)); drawn.append(cc)
        if drawn and mouth in ('smile', 'scowl', 'open'):
            ends = [drawn[0] - 1, drawn[-1] + 1] if n == 3 else ([drawn[-1] + 1] if c > hc_col else [drawn[0] - 1])
            if mouth == 'open':
                for cc in drawn[:2] if n == 3 else drawn[:1]:
                    p = snap_in(r0 + 1, cc)
                    if p and p[1] == cc: out.append((r0 + 1, cc, 'ink_2'))
            else:
                dr = -1 if mouth == 'smile' else 1
                for cc in ends:
                    p = snap_in(r0 + dr, cc)
                    if p and p[1] == cc: out.append((r0 + dr, cc, 'skin_sh' if mouth == 'smile' else 'ink_2'))
    return out

def glasses(B, pose, yaw, eyes_info, row_mean, facing, proj, surf, head, edge, eyes, dz):
    """Leonard: thick black frames drawn as a screen-space pixel template around each projected eye
    (cleaner than projecting a 3-D rectangle at 1x). Also draws his eyes inside the lenses."""
    hair_i = R.MATS.index('hair')
    skin = head & (B['mat'] == R.MATS.index('skin'))
    op = B['mat'] >= 0
    hc_col, _ = proj([0, 0, 0])
    lift = int(round(dz))                     # glasses_push: frame rides up 1 px on the push frame
    r0 = row_mean; fr = r0 - lift
    frame, out = set(), []
    lenses = []
    for sx, f, c, r in eyes_info:
        wi = 3 if f > 0.72 else (2 if f > 0.40 else 1)
        cc = int(math.floor(c))
        if wi == 3: ci = [cc-1, cc, cc+1]
        elif wi == 2: ci = [cc-1, cc] if (c - cc) < 0.5 else [cc, cc+1]
        else: ci = [cc]
        # keep interior on the face (shift inward if it would sit on the silhouette edge)
        step = 1 if cc < hc_col else -1
        for _ in range(3):
            if all(0 <= x < 128 and op[r0, x] and not edge[r0, x] for x in ci) and op[r0, ci[0]-1] and op[r0, ci[-1]+1]: break
            ci = [x + step for x in ci]
        lenses.append((sx, f, ci))
        rnd = (R.CID == 'bernadette')            # round frames: drop the box corners
        for x in range(ci[0]-1, ci[-1]+2):
            if rnd and x in (ci[0]-1, ci[-1]+1) and len(ci) >= 2: continue
            frame.add((fr-2, x)); frame.add((fr+1, x))
        for y in (fr-1, fr):
            frame.add((y, ci[0]-1)); frame.add((y, ci[-1]+1))
        if pose.get('brow') == 'angry':          # scowl: brows slant down toward the nose, above the frame
            inner_left = (c > hc_col)            # this lens sits right of the nose -> its inner end is on the left
            xs = list(range(ci[0]-1, ci[-1]+2))
            for j, x in enumerate(xs):
                k = j if inner_left else len(xs) - 1 - j       # 0 = inner end
                out.append((fr-3 if k == 0 else fr-4, x, 'hair_sh'))
        # eye
        ec = ci if wi == 1 else ([ci[1]] if wi == 3 and False else (ci[1:] if (wi == 3 and sx * (1 if c > hc_col else -1) < 0) else ci[:2] if wi == 3 else ci[:1] if f < 0.6 else ci))
        if wi == 3: ec = [ci[1], ci[2]] if c < hc_col else [ci[0], ci[1]]   # 2-px eye toward the nose
        elif wi == 2: ec = [ci[0]] if c > hc_col else [ci[1]]
        if eyes == 'open': out += [(r0, x, 'ink_2') for x in ec]
        elif eyes == 'half': out += [(r0, x, 'ink_2') for x in ec] + [(r0-1, x, 'skin_sh') for x in ec]
        else: out += [(r0, x, 'skin_sh') for x in ec]
        # glint: upper-outer interior pixel (only when the lens is wide enough to keep the eye clear)
        if wi >= 2:
            gx = ci[0] if c < hc_col else ci[-1]
            gl = 'lens_glint' if 'lens_glint' in R.C else 'white_hi'
            if gx not in ec or eyes != 'open': out.append((fr-1, gx, gl))
            else: out.append((fr-1, gx, gl))
    # bridge between the two lenses (one row, upper half of the frame)
    if len(lenses) == 2:
        a, b = sorted(lenses, key=lambda L: L[2][0])
        for x in range(a[2][-1] + 2, b[2][0] - 1): frame.add((fr-1, x))
    # temple arm toward the ear on the camera-facing side (3/4 and profile views)
    for sx, f, ci in lenses:
        if f > 0.75: continue
        # direction away from the nose
        dirn = -1 if (proj(surf(sx, 0.0))[0] < proj(surf(0, 0.0))[0]) else 1
        if abs(proj(surf(sx, 0.0))[0] - proj(surf(0, 0.0))[0]) < 0.6: continue
        x = (ci[-1] + 2) if dirn > 0 else (ci[0] - 2)
        for _ in range(9):
            if not (0 <= x < 128) or not head[fr-1, x] or edge[fr-1, x]: break
            frame.add((fr-1, x)); x += dirn
    res = [(y, x, 'glasses') for (y, x) in frame if 0 <= y < 128 and 0 <= x < 128 and head[y, x]]
    res += [(y, x, n) for (y, x, n) in out if 0 <= y < 128 and 0 <= x < 128 and head[y, x] and (y, x) not in frame]
    return res

def compose(B, pose, yaw, mirror=False, eyes='open', glasses_dz=0.0):
    overlays = face_overlays(B, pose, yaw, eyes, glasses_dz)
    B = {k: v.copy() for k, v in B.items()}
    if mirror:
        for k in B: B[k] = B[k][:, ::-1].copy()
        B['uv'][..., 0] *= -1; B['hq'][..., 0] *= -1
        overlays = [(r, 127 - c, n) for r, c, n in overlays]
    C, RAMP, MATS = R.C, R.RAMP, R.MATS
    mat, tone = B['mat'], B['tone'].copy(); tag = B['tag']; q = B['hq']
    op = mat >= 0; H, W = mat.shape
    key = np.where(op, mat*4+tone, -1)
    kp = np.pad(key, 1, constant_values=-1)
    nb = np.stack([kp[:-2,1:-1], kp[2:,1:-1], kp[1:-1,:-2], kp[1:-1,2:]], -1)
    for y, x in zip(*np.where(op)):
        n = nb[y, x]
        if (n != key[y, x]).all():
            vals, cnt = np.unique(n, return_counts=True)
            if cnt.max() >= 3 and vals[cnt.argmax()] >= 0 and vals[cnt.argmax()]//4 == mat[y, x]:
                tone[y, x] = vals[cnt.argmax()] % 4
    img = np.zeros((H, W, 4), np.uint8)
    for mi, m in enumerate(MATS):
        for ti in range(3):
            w = op & (mat == mi) & (tone == ti); img[w, :3] = C[RAMP[m][ti]]
    img[op, 3] = 255
    M = {m: op & (mat == MATS.index(m)) for m in MATS}
    hair = M['hair'] & (tag == 99)
    # fringe shadow
    under = np.zeros_like(op); under[1:] = hair[:-1]
    put(img, under & M['skin'] & (tag == 99), 'skin_sh')
    # ---- hair texture ----
    qx, qy, qz = q[..., 0], q[..., 1], q[..., 2]
    if R.CID == 'sheldon':
        PX = -3.9
        side = np.where(qx > PX, 1.0, -1.0)
        s = qy * 0.85 + 0.35 * side * (qx - PX) - 0.12 * qz
        fr = (s / 3.6) % 1.0
        far_part = np.abs(qx - PX) > 1.6
        put(img, hair & far_part & (fr < 0.15) & (tone == 1) & (qz > 1.5), 'hair_sh')
        put(img, hair & far_part & (fr > 0.40) & (fr < 0.62) & (B['up'] > 0.6) & (tone <= 1) & (qz > 4), 'hair_hi')
        put(img, hair & (np.abs(qx - PX) < 0.75) & (qz > 6.5) & (qy > -5), 'hair_sh')          # the part line
    elif R.CID == 'penny':
        PX = -3.4
        ang = np.arctan2(qx, -qy)                       # around the vertical axis (0 = straight back)
        strand = np.sin(ang * 11.0 + 0.10 * qz + 0.8 * np.sin(qz * 0.25))
        put(img, hair & (strand < -0.80) & (tone >= 1) & (qz < 6), 'hair_sh')
        put(img, hair & (strand > 0.85) & (tone == 1) & (qz < 2) & (qz > -18), 'hair_hi')
        # crown sheen band + the LEFT side part line (decal, re-evaluated in true orientation on mirrors)
        put(img, hair & (B['up'] > 0.55) & (tone <= 1) & (np.abs(qx - PX) > 1.4) & (((qz + 0.35*qy) % 4.2) < 1.2) & (qz > 5), 'hair_hi')
        put(img, hair & (np.abs(qx - PX) < 0.7) & (qz > 7.0) & (qy > -4.5), 'hair_sh')
        put(img, hair & (qz < -20.5) & (tone >= 1), 'hair_sh')         # darker ends
    elif R.CID in R.NEW_CAST:
        cast_hair_tex(img, B, hair, tone, qx, qy, qz)
    else:
        v = (np.sin(1.25*qx + 1.1*np.sin(1.05*qz + 0.4)) * np.sin(1.25*qz + 1.1*np.sin(1.1*qy)) *
             np.sin(1.2*qy + 0.9*np.sin(0.9*qx) + 0.5))
        put(img, hair & (v > 0.30) & (tone <= 1) & (B['up'] > 0.15), 'hair_hi')
        put(img, hair & (v < -0.42) & (tone >= 1), 'hair_sh')
    # ---- torso decals (uv evaluated in TRUE orientation, so they never read backwards) ----
    uv = B['uv']; valid = op & ~np.isnan(uv[..., 0]); a = np.nan_to_num(uv[..., 0]); w_ = np.nan_to_num(uv[..., 1]); fac = np.nan_to_num(uv[..., 2])
    front = valid & (fac > 0.35); back = valid & (fac < -0.35)
    decal = np.zeros((H, W), bool)
    if R.CID == 'sheldon':
        code = np.zeros((H, W), int); code[front] = emblem_code(a[front], w_[front])
        put(img, code == 1, 'emblem'); put(img, code == 2, 'emblem_sh'); put(img, code == 3, 'tee_sh')
        decal |= code > 0
        fd = np.where(front, segs_dist(a, w_, FOLDS_FRONT), 9e9); bd = np.where(back, segs_dist(a, w_, FOLDS_BACK), 9e9)
        fold = (op & M['tee'] & ((fd < 0.55) | (bd < 0.55))) & ~decal
        put(img, fold & (tone < 2), 'tee_sh'); put(img, fold & (tone == 2), 'tee_xsh')
    elif R.CID == 'penny':
        D = R.DIM; tz, th = D['torso_z'], D['torso'][2]
        # scoop neckline (skin) on the front, hem shadow line over the denim
        neck = front & ((a / 3.4) ** 2 + ((w_ - (tz + th + 0.6)) / 2.6) ** 2 < 1.0)
        put(img, neck & (tone <= 1), 'skin'); put(img, neck & (tone == 2), 'skin_sh')
        hem = valid & (w_ < tz - th - 0.6) & M['top']
        put(img, hem & (tone <= 1), 'top_sh')
        decal |= neck
        # soften the neck: only the row directly under the jaw stays in shadow (avoids a 'beard' read)
        nk = M['skin'] & (tag == 0) & (tone == 2)
        jaw = np.zeros_like(nk); jaw[1:] = (M['skin'] & (tag == 99))[:-1]
        put(img, nk & ~jaw, 'skin')
        # boots: darker sole/heel line
        foot = M['shoes'] & (tag == 4)
        put(img, foot & (qz < -0.7), 'boots_sh')
        # jeans: centre seam hint on the pelvis front
    elif R.CID in R.NEW_CAST:
        decal |= cast_decals(img, B, M, tone, tag, q, front, back, valid, a, w_)
    else:
        D = R.DIM; tz, th = D['torso_z'], D['torso'][2]
        strip = front & (np.abs(a) < 3.0) & (w_ > tz - th - 1.5)
        put(img, strip & (tone <= 1), 'tee'); put(img, strip & (tone == 2), 'tee_sh')
        zipe = front & (np.abs(a) >= 3.0) & (np.abs(a) < 3.8)
        put(img, zipe, 'hoodie_sh')
        # original tee graphic: a little 'd-pad + two buttons' game motif, centred on the strip
        da, dw = a - 0.0, w_ - (tz + 1.0)
        dpad = strip & (((np.abs(da) < 0.55) & (np.abs(dw) < 1.65)) | ((np.abs(dw) < 0.55) & (np.abs(da) < 1.65)))
        put(img, dpad, 'paper')
        # zip pull on the character's LEFT panel edge (asymmetric decal, re-evaluated on mirrors)
        zp = front & (a > 3.0) & (a < 4.3) & (np.abs(w_ - (tz + 5.5)) < 1.0)
        put(img, zp, 'grey_lt')
        hem = valid & (w_ < tz - th + 0.2) & ~strip & M['hoodie']
        put(img, hem, 'hoodie_sh')
        decal |= strip | zipe | zp
        # sneakers: white sole + toe cap
        foot = M['shoes'] & (tag == 4)
        put(img, foot & ((qz < -0.6) | (qy > 4.4)), 'shoe_toe')
        # corduroy wale hint: sparse vertical darker lines on the trouser fronts
    # interior depth lines
    dep = B['depth']; dp = np.pad(dep, 1, constant_values=1e9)
    near_nb = np.minimum.reduce([dp[:-2,1:-1], dp[2:,1:-1], dp[1:-1,:-2], dp[1:-1,2:]])
    occl = op & (dep - near_nb > 3.5) & ~decal
    for mi, m in enumerate(MATS):
        put(img, occl & (mat == mi), RAMP[m][3])
    # silhouette outline + sel-out
    opp = np.pad(op, 1)
    edge = op & ~(opp[:-2,1:-1] & opp[2:,1:-1] & opp[1:-1,:-2] & opp[1:-1,2:])
    img[edge, :3] = C['ink']
    sel = edge & (B['up'] > 0.55)
    for m in MATS:
        if m in ('shoes',): continue
        put(img, sel & M[m], RAMP[m][3])
    # projected face overlays last
    for r, c, n in overlays:
        if 0 <= r < H and 0 <= c < W and img[r, c, 3]: img[r, c, :3] = C[n]
    return img


# ================= cast v1 (Howard, Raj, Bernadette, Amy) =================
def cast_hair_tex(img, B, hair, tone, qx, qy, qz):
    up = B['up']; cid = R.CID
    sheen = hair & (up > 0.55) & (tone <= 1) & (((qz + 0.35*qy) % 4.4) < 1.1) & (qz > 5)
    if cid == 'howard':
        put(img, hair & (qy > 2.5) & (qz < 6.5) & (np.sin(qx*1.55 + 0.4) > 0.72) & (tone <= 1), 'hair_sh')   # bang strands
        put(img, sheen, 'hair_hi')
    elif cid == 'raj':
        PX = -3.6; side = np.where(qx > PX, 1.0, -1.0)
        s = qy * 0.85 + 0.35 * side * (qx - PX) - 0.12 * qz; fr = (s / 3.4) % 1.0
        far = np.abs(qx - PX) > 1.6
        put(img, hair & far & (fr < 0.15) & (tone == 1) & (qz > 1.5), 'hair_sh')
        put(img, hair & far & (fr > 0.42) & (fr < 0.62) & (up > 0.55) & (tone <= 1) & (qz > 4), 'hair_hi')
        put(img, hair & (np.abs(qx - PX) < 0.75) & (qz > 6.5) & (qy > -5), 'hair_sh')
    else:
        PX = -2.8 if cid == 'bernadette' else -2.4
        ang = np.arctan2(qx, -qy)
        if cid == 'bernadette':
            strand = np.sin(ang * 9.0 + 0.12 * qz + 1.1 * np.sin(qz * 0.55))
            put(img, hair & (strand < -0.78) & (tone >= 1) & (qz < 6), 'hair_sh')
            put(img, hair & (strand > 0.85) & (tone == 1) & (qz < 3) & (qz > -12), 'hair_hi')
            put(img, hair & (qz < -11.0) & (tone >= 1), 'hair_sh')
        else:
            strand = np.sin(ang * 13.0 + 0.02 * qz)
            put(img, hair & (strand < -0.82) & (tone >= 1) & (qz < 6), 'hair_sh')
            put(img, hair & (strand > 0.90) & (tone == 1) & (qz < 2) & (qz > -18), 'hair_hi')
        put(img, sheen & (np.abs(qx - PX) > 1.4), 'hair_hi')
        put(img, hair & (np.abs(qx - PX) < 0.7) & (qz > 6.5) & (qy > -4.5), 'hair_sh')     # part line (her left)
        if cid == 'amy':   # hair clip on the part side (decal; head-local so mirrored views keep it on her left)
            clip = hair & (qx < -5.4) & (qx > -9.5) & (np.abs(qz - 5.2) < 1.0) & (qy > -0.5) & (qy < 6.0)
            put(img, clip, 'hair_clip')

def cast_decals(img, B, M, tone, tag, q, front, back, valid, a, w):
    D = R.DIM; tz, th = D['torso_z'], D['torso'][2]; top = tz + th; cid = R.CID
    H, W = tone.shape; dec = np.zeros((H, W), bool)
    t01 = tone <= 1; t2 = tone == 2
    if cid == 'howard':
        v = front & M['shirt'] & (w > top - 6.0) & (np.abs(a) < 0.62 * (w - (top - 6.0)))
        put(img, v & t01, 'dickey'); put(img, v & t2, 'dickey_sh'); dec |= v
        plk = front & M['shirt'] & (np.abs(a) < 0.45) & (w <= top - 6.0)
        put(img, plk, 'shirt_sh'); dec |= plk
        pin = front & M['shirt'] & (a > 3.0) & (a < 5.0) & (np.abs(w - (top - 2.4)) < 0.95)     # alien pin, his LEFT collar
        put(img, pin, 'alien_pin'); dec |= pin
        pz, ph = D['pelvis']; bz = pz + ph[2] - 0.6
        bk = front & M['belt'] & (np.abs(a) < 3.0) & (np.abs(w - bz) < 1.7)
        put(img, bk, 'buckle'); put(img, bk & (a > 0.4) & (a < 2.2) & (w > bz), 'buckle_hi'); dec |= bk
        put(img, M['shoes'] & (tag == 4) & (q[..., 2] < -0.7), 'boots_sh')
    elif cid == 'raj':
        strip = front & M['jacket'] & (np.abs(a) < 4.0) & (w > tz - th + 1.0)
        vn = strip & (w > top - 6.5) & (np.abs(a) < 0.62 * (w - (top - 6.5)) + 0.3)
        vest = strip & ~vn
        u = (a + w) / 2.4; vv = (a - w) / 2.4
        chk = ((np.floor(u) + np.floor(vv)) % 2) == 0
        put(img, vest & t01 & chk, 'vest'); put(img, vest & t01 & ~chk, 'vest_hi'); put(img, vest & t2, 'vest_sh')
        put(img, vest & ((u % 1.0) < 0.22) & ((vv % 1.0) < 0.22), 'argyle')
        put(img, vn & t01, 'shirt'); put(img, vn & t2, 'shirt_sh')
        lap = front & M['jacket'] & (np.abs(a) >= 4.0) & (np.abs(a) < 5.0) & (w > tz - 2)
        put(img, lap, 'jacket_sh')
        dec |= strip | lap
    elif cid == 'bernadette':
        bl = front & M['cardigan'] & (np.abs(a) < 2.7) & (w > tz - th + 1.6)
        put(img, bl & t01, 'floral_a'); put(img, bl & t2, 'grey_lt'); dec |= bl
        br = front & M['cardigan'] & (a > 3.0) & (a < 4.6) & (np.abs(w - (top - 3.2)) < 0.8)    # brooch, her LEFT
        put(img, br, 'floral_b'); dec |= br
        sk = M['skirt'] & valid
        f1 = sk & (np.sin(a * 1.9 + 0.3) * np.sin(w * 1.7 + a * 0.6) > 0.80) & t01
        f2 = sk & (np.sin(a * 1.7 + 2.1) * np.sin(w * 1.9 - a * 0.5 + 1.3) > 0.86) & t01 & ~f1
        put(img, f1, 'floral_a'); put(img, f2, 'floral_b'); dec |= f1 | f2
    elif cid == 'amy':
        bl = front & M['cardigan'] & (np.abs(a) < 2.9) & (w > tz - th + 0.4)
        put(img, bl & t01, 'blouse'); put(img, bl & t2, 'blouse_sh')
        inner = bl & (w > top - 2.6) & (np.abs(a) < 1.4)                 # layered top: light under-collar
        put(img, inner, 'stripe'); dec |= bl
        cardi = valid & M['cardigan'] & ~bl
        band = cardi & ((np.abs(w - (tz - th + 1.6)) < 0.55) | (np.abs(w - (tz + 2.5)) < 0.55)) & t01
        put(img, band, 'stripe'); dec |= band
        put(img, M['skirt'] & valid & (w < D['skirt'][1] + 1.0) & t01, 'skirt_sh')   # hem shadow
    # neck: only the row directly under the jaw stays in shadow
    nk = M['skin'] & (tag == 0) & (tone == 2)
    jaw = np.zeros_like(nk); jaw[1:] = (M['skin'] & (tag == 99))[:-1]
    put(img, nk & ~jaw, 'skin')
    return dec
