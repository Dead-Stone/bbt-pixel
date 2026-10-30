"""Seated placement used by the sim (and mirrored by viewer.js): the world export (harness/export_world.py ->
tools/seating.py) stamps every sit/perch hook with
  seat [x, y]  butt contact point on the seat surface      seat_z  seat surface height (m)
  sit_dir      facing of the sitter (hook facing)           sit_key depth key of a sitter on this hook
The viewer draws the sit frame with its frame.seat anchor on scr(seat x, seat y, seat_z), and draws the hook's occluder
sprites (chair/booth backs in front of the sitter) only while the hook is occupied."""
import math

def seat_place(h):
    if 'seat' in h:
        return dict(pos=list(h['seat']), z=h['seat_z'], dir=h['sit_dir'], key=h['sit_key'], hook=h['id'])
    x, y = h['pos']     # legacy scene.json without seat data
    return dict(pos=[x, y], z=0.45, dir=h['facing'], key=math.floor(x) + math.floor(y) + 1.5, hook=h.get('id'))
