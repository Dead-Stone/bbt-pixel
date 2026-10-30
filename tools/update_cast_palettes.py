"""Cast v1 palettes (Howard, Raj, Bernadette, Amy) aligned to spec section 3 hex values.
Writes palettes/bbt_<id>.gpl + the 'characters' entries of bbt_palettes.json + the swatch sheet.
Does NOT touch Sheldon / Leonard / Penny palettes."""
import json, os, re
import make_palettes as MP
NEW = {
 "Howard": [("skin_hi","#f5d6c0"),("skin","#e3b394"),("skin_sh","#b9826a"),("hair_hi","#3a281c"),("hair","#2e2626"),("hair_sh","#1e1a1a"),
            ("dickey","#f4f1ea"),("dickey_sh","#c9ced6"),("shirt_hi","#5c98e0"),("shirt","#3b7fd1"),("shirt_sh","#2b5f9e"),
            ("pants_hi","#d455a4"),("pants","#b8338a"),("pants_sh","#8a2668"),("belt","#c8362f"),("belt_sh","#8f2620"),
            ("buckle","#c9ced6"),("buckle_hi","#fffdf6"),("alien_pin","#7bd44a"),("boots","#5a3f2b"),("boots_sh","#3a281c")],
 "Raj": [("skin_hi","#c88a60"),("skin","#b47a52"),("skin_sh","#93603f"),("hair_hi","#4a3d3a"),("hair","#2e2626"),("hair_sh","#1e1a1a"),
         ("shirt_hi","#f4ecd8"),("shirt","#eee3c8"),("shirt_sh","#c9bc9a"),("vest_hi","#9a6a42"),("vest","#7a5233"),("vest_sh","#5a3a24"),
         ("argyle","#b08a4a"),("pants_hi","#8a8f5a"),("pants","#6f7442"),("pants_sh","#545832"),("jacket","#5a3f2b"),("jacket_sh","#3a281c"),
         ("shoes","#3a281c")],
 "Bernadette": [("skin_hi","#f5d6c0"),("skin","#e3b394"),("skin_sh","#b9826a"),("hair_hi","#e0b562"),("hair","#c99a45"),("hair_sh","#9a7230"),
                ("glasses","#6b4a33"),("dress_hi","#3e4f80"),("dress","#2c3a66"),("dress_sh","#1f2a4a"),("floral_a","#f4f1ea"),("floral_b","#f2c94c"),
                ("cardigan_hi","#f7aac6"),("cardigan","#f28db2"),("cardigan_sh","#c96a8e"),("shoes","#2b2233")],
 "Amy": [("skin_hi","#f5d6c0"),("skin","#e3b394"),("skin_sh","#b9826a"),("hair_hi","#7a5a3e"),("hair","#5a3f2b"),("hair_sh","#3a281c"),
         ("glasses","#3a281c"),("cardigan_hi","#8a66a3"),("cardigan","#6e4a87"),("cardigan_sh","#523568"),("stripe","#c9b8d6"),
         ("blouse","#7a2a3a"),("blouse_sh","#5a1e2b"),("skirt_hi","#cfa672"),("skirt","#b58a55"),("skirt_sh","#8a663a"),
         ("tights","#5a3d2e"),("shoes","#3a281c"),("hair_clip","#c9b8d6")],
}
if __name__ == '__main__':
    for k, v in NEW.items():
        MP.CHAR[k] = v
        MP.write_gpl(f"BBT {k}", MP.MASTER["Ink & neutrals"] + v, os.path.join(MP.OUT, f"bbt_{k.lower()}.gpl"))
    p = os.path.join(MP.OUT, "bbt_palettes.json"); js = json.load(open(p))
    for k, v in NEW.items(): js["characters"][k] = dict(v)
    json.dump(js, open(p, "w"), indent=2)
    # keep make_palettes.py's CHAR table in sync (only these four lines)
    src = open(MP.__file__).read()
    for k, v in NEW.items():
        line = f' "{k}": ' + json.dumps(v).replace('"', '"').replace('[[', '[(').replace(']]', ')]').replace('], [', '),(').replace(', ', ',') + ','
        src = re.sub(rf'^ "{k}": \[.*\],$', line.replace('\\', '\\\\'), src, flags=re.M)
    open(MP.__file__, 'w').write(src)
    MP.draw_sheet(); print('ok')
