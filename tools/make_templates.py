"""Pixel-exact guide templates: 128x128 character frame guide and 128x64 iso tile/wall guides."""
import os
from PIL import Image, ImageDraw
OUT = os.path.join(os.path.dirname(__file__), "..", "templates")
os.makedirs(OUT, exist_ok=True)
HEIGHTS = {"sheldon":100,"raj":90,"penny":88,"leonard":86,"howard":86,"amy":86,"bernadette":78}
PIVOT = (64,116)
# frame guide (native 128x128, plus 4x preview)
g = Image.new("RGBA",(128,128),(0,0,0,0)); d = ImageDraw.Draw(g)
d.rectangle([0,0,127,127],outline=(255,0,255,90))
d.rectangle([4,4,123,123],outline=(0,200,255,90))           # 4px safe margin
for name,h in HEIGHTS.items():
    y = PIVOT[1]-h; d.line([(40,y),(88,y)],fill=(255,200,0,140))
d.line([(64,8),(64,123)],fill=(0,255,0,70))                   # center line
d.ellipse([44,111,84,121],outline=(120,120,255,160))          # 40x10 shadow footprint
d.point(PIVOT,fill=(255,0,0,255))
g.save(os.path.join(OUT,"frame_guide_128.png"))
g.resize((512,512),Image.NEAREST).save(os.path.join(OUT,"frame_guide_128_preview4x.png"))
# iso floor tile 128x64 (2:1), pixel-stepped edges (2 across, 1 down)
t = Image.new("RGBA",(128,64),(0,0,0,0)); td = ImageDraw.Draw(t)
for y in range(32):
    x0 = 64-2*(y+1); x1 = 63+2*(y+1)
    td.line([(x0,y),(x1,y)],fill=(216,199,163,255)); td.line([(x0,63-y),(x1,63-y)],fill=(216,199,163,255))
t.save(os.path.join(OUT,"iso_floor_tile_128x64.png"))
# wall guides: back-left wall segment (1 tile long, 192px tall) + 16px cutaway stub
for name,hgt in (("iso_wall_backright_full_128x224.png",192),("iso_wall_backright_cutaway_128x48.png",16)):
    w = Image.new("RGBA",(64,hgt+32),(0,0,0,0)); wd = ImageDraw.Draw(w)
    for x in range(64):
        top = 32 - (x//2) - 1 + 0  # rises 1px per 2px going right->left mirrored below
        top = (x//2)
        wd.line([(x,top),(x,top+hgt)],fill=(185,165,127,255))
    w.save(os.path.join(OUT,name.replace("128x","64x")))
print(os.listdir(OUT))
