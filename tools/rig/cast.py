"""Per-character body + outfit + hair + gait specs for the modular rig.
Heights: real cm (celebheights.com estimates, same table as tools/char_rig.REAL_CM); sprite height = 100*cm/185 px.
Body multipliers (skeleton.Body): leg, arm, sh (shoulder width), tw/td (torso width/depth), hip, waist, limb (leg
thickness), arm_k (arm thickness), head_k, bust, belly, slouch, head_fwd.
Colours: base colour per material; palette.ramp() derives hi/shade/deep/outline."""

REAL_CM = {'sheldon': 185, 'raj': 171, 'penny': 167, 'leonard': 165, 'howard': 164, 'amy': 163, 'bernadette': 149}

CAST = {
 'penny': dict(
    body=dict(leg=1.02, sh=0.92, tw=0.88, td=0.92, hip=0.92, waist=0.84, limb=0.92, arm_k=1.0, head_k=1.14, bust=0.9, neck=1.05, foot=0.86, hand=0.9),
    colors=dict(skin=(246, 196, 152), hair=(236, 200, 118), top=(240, 116, 160), denim=(66, 104, 156), boots=(122, 76, 46),
                eye=(70, 120, 100), lip=(214, 116, 120), brow=(178, 136, 80), lash=(70, 44, 34), tray=(176, 180, 188), glass=(210, 226, 236), wine=(150, 36, 60)),
    hair=dict(kind='long', length=32.0, part=1, bangs=True, vol=0.85, curl=0.6, hairline=0.42, face_w=0.95),
    outfit=dict(top=dict(mat='top', sleeve=0.32, neck='scoop', hem=0.05), pants=dict(mat='denim', flare=0.5), shoes=dict(mat='boots', h=1.25, shaft=0.18)),
    gait=dict(stride=0.30, arm=19, elbow=14, bob=1.0, hip_roll=5.0, sway=1.6, twist=6, lean=1.0),
    work='tray', emotes=['gesture', 'hair_flip', 'wine_sip', 'eye_roll'], feminine=True),
}
