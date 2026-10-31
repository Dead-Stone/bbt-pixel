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
 'leonard': dict(
    body=dict(leg=0.98, sh=1.0, tw=1.0, td=1.0, hip=0.95, waist=0.96, limb=1.0, arm=1.06, arm_k=0.95, head_k=1.12, neck=0.95, foot=1.0, hand=1.0, slouch=0.15),
    colors=dict(skin=(238, 190, 150), hair=(62, 44, 32), tee=(78, 116, 84), jacket=(104, 132, 172), pants=(112, 74, 46), shoes=(228, 228, 222),
                eye=(40, 30, 26), lip=(196, 124, 112), brow=(52, 36, 28), lash=(40, 28, 22), frame=(112, 104, 112), lens=(214, 228, 236), marker=(52, 84, 196)),
    hair=dict(kind='curly', vol=1.15, part=1, hairline=0.40, face_w=0.85),
    outfit=dict(top=dict(mat='tee', sleeve=0.45, neck='crew'), jacket=dict(mat='jacket', hood=True, hem=0.5, infl=1.1, gap=0.10),
                pants=dict(mat='pants', flare=0.2), shoes=dict(mat='shoes', h=1.15)),
    glasses=True,
    gait=dict(arm=10, elbow=16, bob=1.0, hip_roll=3.0, sway=1.0, twist=5, lean=1.5),
    work='whiteboard', emotes=['gesture', 'glasses_push', 'sigh_shrug']),
 'sheldon': dict(
    body=dict(leg=1.04, sh=0.97, tw=0.85, td=0.84, hip=0.88, waist=0.86, limb=0.84, arm_k=0.86, head_k=1.04, neck=1.12, foot=1.0, hand=0.86),
    colors=dict(skin=(242, 198, 162), hair=(118, 80, 50), tee=(204, 42, 46), tee_alt=(246, 200, 48), under=(44, 64, 124), pants=(198, 178, 132),
                shoes=(108, 70, 42), eye=(82, 112, 150), lip=(200, 128, 116), brow=(100, 66, 40), lash=(52, 36, 26), marker=(40, 40, 46)),
    hair=dict(kind='neat', vol=0.55, part=1, hairline=0.46, face_w=0.85),
    outfit=dict(under=dict(mat='under', sleeve=1.95, neck='crew', part='under'), top=dict(mat='tee', sleeve=0.42, neck='crew', logo=(0.0, 0.05, 0.36)),
                pants=dict(mat='pants', flare=0.1), shoes=dict(mat='shoes', h=1.1)),
    gait=dict(arm=9, elbow=8, bob=0.6, hip_roll=1.8, sway=0.5, twist=2.5, lean=0.0),
    work='whiteboard', emotes=['gesture', 'point_gotcha', 'spot_claim', 'knock_knock_penny']),
 'howard': dict(
    body=dict(leg=1.0, sh=0.88, tw=0.84, td=0.84, hip=0.88, waist=0.84, limb=0.80, arm_k=0.84, head_k=1.12, neck=1.0, foot=0.95, hand=0.95),
    colors=dict(skin=(236, 192, 156), hair=(110, 72, 42), top=(64, 132, 212), dickey=(232, 230, 236), pants=(204, 44, 142), belt=(44, 38, 44),
                belt_alt=(236, 204, 84), shoes=(84, 62, 52), eye=(64, 52, 44), lip=(196, 124, 112), brow=(92, 60, 36), lash=(48, 32, 24), card=(240, 238, 232)),
    hair=dict(kind='bowl', vol=0.9, part=0, hairline=0.40, face_w=0.82),
    outfit=dict(top=dict(mat='top', sleeve=1.95, neck='turtle', collar_mat='dickey', collar=0.75),
                pants=dict(mat='pants', flare=0.0), shoes=dict(mat='shoes', h=1.25), belt='belt'),
    gait=dict(arm=14, elbow=16, bob=1.3, hip_roll=3.5, sway=1.4, twist=5, lean=0.5),
    work='laptop', emotes=['gesture', 'eyebrow_waggle', 'magic_trick']),
 'raj': dict(
    body=dict(leg=1.0, sh=1.0, tw=0.95, td=0.95, hip=0.93, waist=0.92, limb=0.95, arm=1.03, arm_k=0.95, head_k=1.10, neck=1.0, foot=1.0, hand=0.92),
    colors=dict(skin=(178, 122, 84), hair=(30, 24, 24), shirt=(238, 234, 224), vest=(124, 84, 54), pants=(48, 48, 56), shoes=(92, 58, 38),
                eye=(42, 30, 26), lip=(150, 90, 82), brow=(26, 20, 20), lash=(24, 18, 18), marker=(200, 40, 40)),
    hair=dict(kind='side', vol=0.8, part=-1, hairline=0.44, face_w=0.85),
    outfit=dict(top=dict(mat='shirt', sleeve=1.95, neck='crew'), vest=dict(mat='vest'),
                pants=dict(mat='pants', flare=0.1), shoes=dict(mat='shoes', h=1.1)),
    gait=dict(arm=8, elbow=14, bob=0.9, hip_roll=3.0, sway=1.0, twist=3, lean=1.0),
    work='whiteboard', emotes=['gesture', 'astronomy_point', 'shy_hands']),
 'bernadette': dict(
    body=dict(leg=0.96, sh=0.88, tw=0.90, td=0.96, hip=1.0, waist=0.84, limb=1.0, arm=1.03, arm_k=0.98, head_k=1.18, bust=1.0, neck=0.95, foot=0.84, hand=0.88),
    colors=dict(skin=(248, 208, 178), hair=(244, 214, 136), blouse=(246, 244, 238), cardigan=(240, 132, 172), skirt=(36, 46, 94), skirt_alt=(240, 240, 236),
                shoes=(70, 44, 66), eye=(74, 112, 160), lip=(220, 120, 130), brow=(196, 156, 92), lash=(70, 44, 34), frame=(92, 52, 56), lens=(220, 232, 240), pipette=(226, 230, 236), tip=(70, 120, 200), tube=(200, 226, 150)),
    hair=dict(kind='shoulder', length=17.0, part=1, bangs=True, vol=1.05, curl=1.2, hairline=0.42, face_w=0.95),
    outfit=dict(top=dict(mat='blouse', sleeve=0.4, neck='crew'), jacket=dict(mat='cardigan', infl=1.3, hem=0.35, gap=0.2),
                skirt=dict(mat='skirt', length=0.78, flare=1.2, dots=True), shoes=dict(mat='shoes', h=1.0)),
    glasses=True,
    gait=dict(arm=20, elbow=18, bob=1.1, hip_roll=5.0, sway=1.4, twist=6, lean=0.5),
    work='pipette', emotes=['gesture', 'sweet_to_scary', 'hands_on_hips'], feminine=True),
 'amy': dict(
    body=dict(leg=1.0, sh=0.92, tw=0.90, td=0.95, hip=0.98, waist=0.90, limb=0.95, arm_k=0.95, head_k=1.12, bust=0.7, neck=0.95, foot=0.9, hand=0.92, slouch=0.2),
    colors=dict(skin=(240, 202, 172), hair=(98, 62, 40), blouse=(142, 52, 72), cardigan=(112, 72, 142), skirt=(178, 152, 112), tights=(72, 62, 72),
                shoes=(62, 46, 40), eye=(74, 60, 48), lip=(196, 116, 116), brow=(80, 52, 34), lash=(52, 34, 26), frame=(126, 98, 90), lens=(218, 230, 236)),
    hair=dict(kind='shoulder', length=21.0, part=0, bangs=False, vol=0.9, curl=0.3, hairline=0.44, face_w=0.92),
    outfit=dict(top=dict(mat='blouse', sleeve=0.4, neck='crew'), jacket=dict(mat='cardigan', infl=1.4, hem=0.6, gap=0.18),
                skirt=dict(mat='skirt', length=1.6, flare=1.6), tights='tights', shoes=dict(mat='shoes', h=1.3)),
    glasses=True,
    gait=dict(arm=12, elbow=20, bob=0.8, hip_roll=3.0, sway=1.0, twist=4, lean=2.0),
    work='microscope', emotes=['gesture', 'neuro_lecture', 'excited_clap'], feminine=True),
}
