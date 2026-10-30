"""Generate BBT pixel palettes: swatch PNG, Aseprite .gpl, JSON, and a Markdown table snippet."""
import json, os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "..", "palettes")

MASTER = {
  "Ink & neutrals": [("ink","#1a1420"),("ink_2","#2b2233"),("shadow_violet","#3d3047"),("grey_dk","#5a5866"),("grey","#8c8f94"),("grey_lt","#c9ced6"),("paper","#f4f1ea"),("white_hi","#fffdf6")],
  "Skin ramps": [("skin_a1","#f5d6c0"),("skin_a2","#e3b394"),("skin_a3","#b9826a"),("skin_a4","#8a5a48"),("skin_b1","#c88a60"),("skin_b2","#b47a52"),("skin_b3","#93603f"),("skin_b4","#6e452c")],
  "Hair": [("blonde_1","#f2d98e"),("blonde_2","#d9b45e"),("blonde_3","#a8823c"),("brown_1","#7a5a3e"),("brown_2","#5a3f2b"),("brown_3","#3a281c"),("black_1","#2e2626"),("black_2","#1e1a1a")],
  "Wood & leather (4A)": [("wood_hi","#c99a5e"),("wood","#a8743f"),("wood_dk","#7a4e2c"),("wood_xdk","#5a3820"),("leather_hi","#9a6a42"),("leather","#7a4d2f"),("leather_dk","#5c3a24"),("leather_xdk","#3e2617")],
  "Walls & floors": [("wall_4a_hi","#e6d8b8"),("wall_4a","#d8c7a3"),("wall_4a_dk","#b9a57f"),("stair_wall","#cdb98f"),("stair_wall_dk","#a8946c"),("tile_green","#6f8f5e"),("tile_green_dk","#53704a"),("floor_hall","#8a6a4a")],
  "Accents & signage": [("tape_yellow","#f2c230"),("tape_yellow_dk","#c99a1f"),("marker_blue","#2f5fb3"),("marker_red","#c8463d"),("marker_green","#3f8a4f"),("screen_glow","#9fd8ff"),("lamp_warm","#ffd88a"),("plant_green","#5f9a48")],
  "Location palettes": [("4b_turquoise","#3fb8b0"),("4b_orange","#f08a3c"),("4b_purple","#8a5cb0"),("4b_lime","#a6cf4a"),("ccf_amber","#d79a4a"),("ccf_booth_red","#9b2f2f"),("comic_blue","#3f6fb5"),("comic_red","#c94040"),("comic_yellow","#f2c94c"),("cafe_cream","#e9e1cc"),("cafe_teal","#4f9a9a"),("cafe_steel","#a7adb5")],
}

CHAR = {
 "Sheldon": [("skin_hi","#f2d0b5"),("skin","#dba98a"),("skin_sh","#b07a5e"),("hair_hi","#7a5a3e"),("hair","#5a3f2b"),("hair_sh","#3a281c"),("tee_hi","#e0473c"),("tee","#d23a32"),("tee_sh","#a8282a"),("tee_xsh","#7a1c22"),("emblem","#f5c542"),("emblem_sh","#c9962a"),("undershirt","#3b4f7a"),("undershirt_sh","#2a3a5c"),("pants","#b9a27a"),("pants_sh","#8f7a58"),("shoes","#5b3c27"),("bag_strap","#6b4a33")],
 "Leonard": [("skin_hi","#f0cfb3"),("skin","#d9a789"),("skin_sh","#ad785d"),("hair_hi","#4a3830"),("hair","#3a2a24"),("hair_sh","#1c1412"),("glasses","#1a1420"),("lens_glint","#cfe6f2"),("hoodie_hi","#8494ab"),("hoodie","#6f7f96"),("hoodie_sh","#556377"),("hoodie_xsh","#3d4859"),("tee","#4f8a4a"),("tee_sh","#3a6b38"),("pants","#7a5236"),("pants_sh","#5a3b26"),("shoe","#2b2233"),("shoe_toe","#e9e6df"),("jacket_alt","#7a7a4a"),("jacket_alt_sh","#5c5c36")],
 "Howard": [("skin_hi","#f5d6c0"),("skin","#e3b394"),("skin_sh","#b9826a"),("hair_hi","#3a281c"),("hair","#2e2626"),("hair_sh","#1e1a1a"),("dickey","#f4f1ea"),("dickey_sh","#c9ced6"),("shirt_hi","#5c98e0"),("shirt","#3b7fd1"),("shirt_sh","#2b5f9e"),("pants_hi","#d455a4"),("pants","#b8338a"),("pants_sh","#8a2668"),("belt","#c8362f"),("belt_sh","#8f2620"),("buckle","#c9ced6"),("buckle_hi","#fffdf6"),("alien_pin","#7bd44a"),("boots","#5a3f2b"),("boots_sh","#3a281c")],
 "Raj": [("skin_hi","#c88a60"),("skin","#b47a52"),("skin_sh","#93603f"),("hair_hi","#4a3d3a"),("hair","#2e2626"),("hair_sh","#1e1a1a"),("shirt_hi","#f4ecd8"),("shirt","#eee3c8"),("shirt_sh","#c9bc9a"),("vest_hi","#9a6a42"),("vest","#7a5233"),("vest_sh","#5a3a24"),("argyle","#b08a4a"),("pants_hi","#8a8f5a"),("pants","#6f7442"),("pants_sh","#545832"),("jacket","#5a3f2b"),("jacket_sh","#3a281c"),("shoes","#3a281c")],
 "Penny": [("skin_hi","#f5d6c0"),("skin","#e3b394"),("skin_sh","#b9826a"),("hair_hi","#f2d98e"),("hair","#d9b45e"),("hair_sh","#a8823c"),("top_hi","#f7a6c3"),("top","#ef7fa8"),("top_sh","#c75a83"),("denim_hi","#6f93c2"),("denim","#4f74a8"),("denim_sh","#3a5680"),("boots","#7a4d2f"),("boots_sh","#5c3a24"),("uni_blouse","#f6f4ee"),("uni_vest","#f2c94c"),("uni_vest_sh","#c99a1f"),("uni_apron","#2f5a3a"),("lips","#d0606e")],
 "Bernadette": [("skin_hi","#f5d6c0"),("skin","#e3b394"),("skin_sh","#b9826a"),("hair_hi","#e0b562"),("hair","#c99a45"),("hair_sh","#9a7230"),("glasses","#6b4a33"),("dress_hi","#3e4f80"),("dress","#2c3a66"),("dress_sh","#1f2a4a"),("floral_a","#f4f1ea"),("floral_b","#f2c94c"),("cardigan_hi","#f7aac6"),("cardigan","#f28db2"),("cardigan_sh","#c96a8e"),("shoes","#2b2233")],
 "Amy": [("skin_hi","#f5d6c0"),("skin","#e3b394"),("skin_sh","#b9826a"),("hair_hi","#7a5a3e"),("hair","#5a3f2b"),("hair_sh","#3a281c"),("glasses","#3a281c"),("cardigan_hi","#8a66a3"),("cardigan","#6e4a87"),("cardigan_sh","#523568"),("stripe","#c9b8d6"),("blouse","#7a2a3a"),("blouse_sh","#5a1e2b"),("skirt_hi","#cfa672"),("skirt","#b58a55"),("skirt_sh","#8a663a"),("tights","#5a3d2e"),("shoes","#3a281c"),("hair_clip","#c9b8d6")],
}

def hex2rgb(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))

def draw_sheet():
    sw, lab = 44, 160
    rows = list(MASTER.items()) + [(f"{k} (character)", v) for k,v in CHAR.items()]
    maxn = max(len(v) for _,v in rows)
    W = lab + maxn*sw + 16; H = len(rows)*(sw+18) + 40
    img = Image.new("RGB",(W,H),(36,30,44)); d = ImageDraw.Draw(img)
    try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11); ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except Exception: f = ft = ImageFont.load_default()
    d.text((8,8),"BBT Living Sitcom - Master + Character Palettes (v1)",fill=(244,241,234),font=ft)
    y = 36
    for name, cols in rows:
        d.text((8,y+14),name,fill=(230,220,200),font=f)
        for i,(n,h) in enumerate(cols):
            x = lab + i*sw
            d.rectangle([x,y,x+sw-4,y+sw-4],fill=hex2rgb(h),outline=(20,16,24))
            d.text((x,y+sw-2),h[1:],fill=(200,195,190),font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",8) if f!=ImageFont.load_default() else f)
        y += sw+18
    img.save(os.path.join(OUT,"bbt_palette_swatches.png"))

def write_gpl(name, cols, path):
    with open(path,"w") as fh:
        fh.write(f"GIMP Palette\nName: {name}\nColumns: 8\n#\n")
        for n,h in cols:
            r,g,b = hex2rgb(h); fh.write(f"{r:3d} {g:3d} {b:3d}\t{n}\n")

def main():
    os.makedirs(OUT, exist_ok=True)
    draw_sheet()
    master_flat = [c for _,v in MASTER.items() for c in v]
    write_gpl("BBT Master", master_flat, os.path.join(OUT,"bbt_master.gpl"))
    for k,v in CHAR.items():
        # character palettes include ink/neutral ramp so each .gpl is self-contained for Aseprite
        write_gpl(f"BBT {k}", MASTER["Ink & neutrals"]+v, os.path.join(OUT,f"bbt_{k.lower()}.gpl"))
    json.dump({"master":{g:dict(v) for g,v in MASTER.items()},"characters":{k:dict(v) for k,v in CHAR.items()}},
              open(os.path.join(OUT,"bbt_palettes.json"),"w"), indent=2)
    print(len(master_flat), "master colors")

if __name__ == "__main__": main()
