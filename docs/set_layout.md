# 4th floor set layout (4A · hall · 4B)

This doc explains how the floor4 location maps the TV show's standing sets onto the 128x64 iso grid
(64 px/m, `scr(x,y,z)=((x-y)*64,(x+y)*32-z*64)`). The art comes from the ChatGPT environment sheets in
`refs_ai/chatgpt/env/`; the prompts are in `docs/chatgpt_prompts/`.

## Sources (researched Oct 31, 2026)

* Big Bang Theory fandom wiki: *Apartment 4A*, *Sheldon's Spot*, *Apartment 4B*
  (https://bigbangtheory.fandom.com/wiki/Apartment_4A, .../Sheldon%27s_Spot, .../Apartment_4B)
* Wikimedia Commons, *File:Tbbt_apartment.jpg* (photo of the 4A set, CC BY-SA 3.0)
* RoomSketcher blog, *The Big Bang Theory apartments* floor plans
  (https://www.roomsketcher.com/blog/the-big-bang-theory-apartments/)
* Live Home 3D fan floor plan of 4A/4B (livehome3d.com) and sheldon-cooper.de set notes

## What the sources agree on

* **Camera:** the audience sees both apartments through a removed fourth wall. In 4A the TV sits on
  that fourth wall, and the couch faces it (and the camera). Sheldon's spot is the end of the couch
  nearest the door/kitchen side.
* **Hall:** the stairwell (with an out-of-order elevator) sits between the two units. The 4A and 4B
  front doors **face each other** across a short landing.
* **4A:** the front door opens into the living room. The kitchen (counter, stove, fridge, island with
  stools) is on the side away from the couch. The desks sit under the back windows. Bookcases, the
  whiteboards, and the telescope fill the walls. A short hallway at the back leads to the bedrooms and
  bathroom.
* **4B:** the front door opens into a living room with a couch, patterned armchair, and coffee table.
  The kitchen with its bar and stools is on the far side. There is a small round dining table. The
  bedroom door is at the back. The place is always cluttered (laundry pile).

## How the game maps it

* **Camera = TV camera.** The iso camera looks from the front (y=8) toward the back walls (y=0).
  The front edge is the fourth wall and is drawn as a cut-away with no wall. The 4A TV sits near the
  front edge and faces back, so the couch faces the camera like in the show.
* **Zones:** x 0–7 is 4B, x 8–11 is the hall and stair landing, and x 12–22 is 4A.
* **Doors:** the 4B door is on partition x=8 and the 4A door is on partition x=12, both at y=4. They
  face each other across the 4-tile hall, and the stair flight drops toward the camera between them.
  The elevator is on the hall's back wall.
* **4A:** the couch is at x13–15, y2, facing the camera, with Sheldon's spot (seat0) on the door-side
  end. The coffee table is in front of it, then the rug, then the TV stand at the front edge. The
  armchair is at x17. The desk (with office chair) and telescope sit under the back windows at x15–17.
  The bookcases and a whiteboard are on the back wall behind the couch, with a second whiteboard near
  the TV. The kitchen (counter, stove, fridge) is at the far end (x19–22), with the island and stools
  in front of it. The bedroom-hall doorway is on the back wall at x=18.
* **4B:** the kitchen counter and fridge are at the far (left) end, with the bar and two stools in
  front. The couch, coffee table, and rug are near the door, with the patterned armchair beside them.
  The round dining table is by the windows. The laundry pile and bedroom door are on the back wall.

## Deliberate deviations (grid and gameplay constraints)

* The real 4A kitchen opens off the living room on the entry side. Here it sits at the far end (x19–22)
  because the 11-tile-wide strip can't fit the kitchen beside the door without blocking the path from
  the door to the couch. It still reads as an open-plan kitchen with an island.
* 4A's bedroom hallway is a single dark doorway in the back wall (x=18), not a full corridor.
* 4B is mirrored relative to 4A (kitchen at the far left end), as on the show, but it is compressed to
  8 tiles.
* The stairs keep the procedural down-flight because the sheet's staircase goes up.
* All room ids, item ids, hooks, and activities are unchanged from the previous build. Only positions,
  facings, and art changed.

## Layout diagrams (top-down, back wall at top, camera/fourth wall at bottom)

Before (procedural layout, commit f712f3f):

```
     x: 01234567890123456789012
  zone: 44444444hhhhAAAAAAAAAAA
  back wall y=0 (windows: 2,3,21,22)
   y=0: .b..KKKF.LL.FKKKBBCCCDD
   y=1: ...A.............l....o
   y=2: l....II......II...TT.A.
   y=3: C.T..ss.E...Ess.......t
   y=4: C.T...............VV...
   y=5: C..RR.u..|##........nWW
   y=6: ...RR....|##...........
   y=7: .p.......|##...........
  front (fourth wall / camera side) y=8
  legend: C=couch A=armchair T=coffee_table V=tv_stand D=desk o=office_chair K=kitchen_counter I=kitchen_island I=kitchen_bar s=bar_stool F=fridge W=whiteboard B=bookcase t=telescope l=floor_lamp E=front_door b=bedroom_door L=elevator #=stair_flight |=stair_rail R=dining u=laundry p=plant n=dna
```

After (show layout + ChatGPT sheet art):

```
     x: 01234567890123456789012
  zone: 44444444hhhhAAAAAAAAAAA
  back wall y=0 (windows: 4,5,15,16,17)
   y=0: KKK....b.LL.BBWDDt.KKKF
   y=1: ....RRu.........o......
   y=2: .II.RR.......CCC.A.II..
   y=3: .ss.........l.TT...ss..
   y=4: F..CCCl.E...E..........
   y=5: ....TTA..|##...........
   y=6: .........|##.W........n
   y=7: .p.......|##..VV.......
  front (fourth wall / camera side) y=8
  legend: C=couch A=armchair T=coffee_table V=tv_stand D=desk o=office_chair K=kitchen_counter I=kitchen_island I=kitchen_bar s=bar_stool F=fridge W=whiteboard B=bookcase t=telescope l=floor_lamp E=front_door b=bedroom_door L=elevator #=stair_flight |=stair_rail R=dining u=laundry p=plant n=dna
```

Rendered before/after: `env/renders/env_ai/before_after_floor4.png`.
