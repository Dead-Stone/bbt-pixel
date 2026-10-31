"""The GenerateImage prompts used for refs_ai/gen/<cid>_walk4_<dir>.jpg (kept so strips can be regenerated).
References passed with each prompt: the single still for that direction (cut from the turnaround, 3x, on
magenta) and refs_ai/turn_<cid>.png (the character's turnaround row).
Usage: python3 tools/ai_import/prompts.py <cid> <dir>"""
import sys

OUTFIT = dict(
    sheldon='tall and thin, short neat brown hair, red t-shirt with a yellow lightning-bolt logo over a long-sleeve dark red shirt, khaki trousers, brown shoes',
    leonard='curly dark brown hair, black thick-rimmed glasses, green zip hoodie with a grey hood over an olive graphic t-shirt, brown trousers, white sneakers',
    penny='long wavy blonde hair, pink fitted top, blue jeans, brown ankle boots',
    howard='dark bowl-cut hair, royal blue long-sleeve top, large silver belt buckle, tight magenta trousers, brown shoes',
    raj='swept black hair, brown sweater vest over a white collared shirt, dark grey trousers, brown shoes',
    bernadette='short and petite, curly blonde hair, glasses, pink cardigan over a white collared blouse, navy polka-dot skirt, dark tights, dark shoes',
    amy='long straight brown hair, glasses, purple cardigan over a patterned blouse, khaki pleated skirt, dark tights, dark shoes')

FACING = {
    'S': 'FACE THE VIEWER (front view, walking straight toward the camera)',
    'SW': 'are in three-quarter FRONT view, walking toward the viewer and toward the lower-left (face visible, body turned to our left)',
    'W': 'face LEFT in strict side profile (walking toward the left edge of the image)',
    'NW': 'are in three-quarter BACK view, walking away from the viewer toward the upper-left (back of the head visible, face not visible)',
    'N': 'are seen directly FROM BEHIND (back view, walking straight away from the viewer); the face is never visible',
}
POSES = {
    'S': 'figure 1 = stride with the LEFT leg forward (that foot lower on the image and bigger, the other foot higher and partly hidden, knee bent), right arm swung forward; figure 2 = passing pose, legs straight and together, arms at the sides; figure 3 = stride with the RIGHT leg forward, left arm swung forward; figure 4 = passing pose, legs together',
    'N': 'figure 1 = stride with the LEFT leg forward (that foot higher on the image and partly hidden) and the right leg back with its heel lifted showing the sole; figure 2 = passing pose, legs straight and together, arms at the sides; figure 3 = stride with the RIGHT leg forward and the left heel lifted; figure 4 = passing pose, legs together',
}
SIDE = ('figure 1 = long stride, near leg forward and far leg back (back heel lifted), far arm forward; figure 2 = passing pose, legs '
        'straight and together under the body, back foot lifted slightly beside the standing leg, arms at the sides; figure 3 = long '
        'stride with the far leg forward and the near leg back, near arm forward; figure 4 = passing pose again with the other foot lifted')


def walk_prompt(cid, d):
    name = cid.capitalize()
    return (f'Pixel-art sprite strip of the SAME character as the reference images ({name}: {OUTFIT[cid]}), same pixel-art style, '
            f'palette, outline and SAME CHUNKY PROPORTIONS as the references (large head, about one sixth of the body height; '
            f'same shoulder width; do not make the figure slimmer or more realistic). ONE horizontal row of exactly 4 full-body '
            f'figures, evenly spaced, same size, feet on one shared baseline, solid flat magenta (#FF00FF) background. All 4 '
            f'figures {FACING[d]}, exactly like the first reference image. The 4 figures are 4 DIFFERENT key poses of a walk and '
            f'must look clearly different from each other: {POSES.get(d, SIDE)}. No floor, no shadows, no text, no labels, no border.')


if __name__ == '__main__':
    print(walk_prompt(sys.argv[1], sys.argv[2]))
