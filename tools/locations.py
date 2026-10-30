"""Environment v2 location specs (room-template dicts consumed by rooms.py). Coordinates: x along the back wall, y toward camera."""

def long_table(x, y, skip=()):
    out = [('cafe_table_long', x, y, 'SW')]
    for i in range(3):
        if ('n', i) not in skip: out.append(('cafe_chair', x + i, y - 1, 'SW'))
        if ('s', i) not in skip: out.append(('cafe_chair', x + i, y + 1, 'NE'))
    return out
def two_top(x, y, chair='rest_chair', skip=()):
    out = [('rest_table_2top', x, y, 'SW')]
    if 'n' not in skip: out.append((chair, x, y - 1, 'SW'))
    if 's' not in skip: out.append((chair, x, y + 1, 'NE'))
    return out

ROOMS = {}
def room(**kw): ROOMS[kw['id']] = kw; return kw

# ---------------------------------------------------------------- AIT (Arroyo Institute of Technology) cafeteria
room(id='ait_cafeteria', name='AIT Cafeteria (Arroyo Institute of Technology)', kind='interior', size=[12, 9],
     floor=[[0, 0, 12, 9, 'floor_cafe_lino']],
     walls=dict(back=[[0, 12, 'cafe']], left=[[0, 9, 'cafe']], front_cut='cafe', right_cut='cafe', front_gaps=[5, 6]),
     slots=dict(back={8: 'window_day', 9: 'window_day', 10: 'window_day', 11: 'window_day'}),
     items=[('cafe_food_line', 1, 0, 'SW'), ('cafe_menu_board', 1.5, 0, 'SW'), ('ait_crest_banner', 5, 0, 'SW'),
            ('cafe_drink_station', 6, 0, 'SW'), ('cafe_trash_bin', 7, 0, 'SW'),
            ('cafe_vending_snack', 0, 1, 'SE'), ('cafe_vending_drink', 0, 2, 'SE'), ('cafe_vending_coffee', 0, 3, 'SE'),
            ('cafe_bulletin_board', 0, 5, 'SE'), ('off_door', 0, 6, 'SE', 'closed'), ('poster_particles', 0, 7, 'SE'),
            ('gen_potted_palm', 11, 1, 'SW')]
           + long_table(3, 3, skip=(('s', 2),)) + long_table(3, 6, skip=(('n', 1), ('s', 0))) + long_table(8, 3, skip=(('s', 1),)) + long_table(8, 6, skip=(('n', 2),)),
     lights=[dict(pos=[9.9, 0.8], r=1.5, kind='window', src='windows')],
     chars=[dict(cid='sheldon', mode='sit', hook=['cafe_table_long', 0, 'seat0']), dict(cid='howard', mode='sit', hook=['cafe_table_long', 0, 'seat1']),
            dict(cid='raj', mode='sit', hook=['cafe_table_long', 0, 'seat2']),
            dict(cid='leonard', mode='stand', hook=['cafe_food_line', 0, 'queue2'], dir='NE'),
            dict(cid='penny', mode='stand', pos=[6.6, 5.0], dir='NW', anim='walk', k=1)],
     zones={'dining': [0, 0, 12, 9]},
     spawns={'from_physics': [1.5, 6.5], 'from_quad': [5.5, 8.5], 'food_line': [2.5, 1.5]},
     doors=[dict(item='off_door', tile=[0, 6], to='ait_physics', facing='SE')],
     exits=[dict(id='to_physics', tiles=[[0, 6]], to='ait_physics', to_spawn='from_cafeteria', via='door'),
            dict(id='to_quad', tiles=[[5, 8], [6, 8]], to='street_exterior', to_spawn='from_campus', via='car', note='campus quad / parking stub; the guys carpool home')])

# ---------------------------------------------------------------- AIT physics: Sheldon's office (x0-6) + shared/Howard lab (x7-15)
room(id='ait_physics', name="AIT Physics: Sheldon's office + shared lab", kind='interior', size=[16, 8],
     floor=[[0, 0, 7, 8, 'floor_office_carpet'], [7, 0, 16, 8, 'floor_lab_vinyl']],
     walls=dict(back=[[0, 7, 'office'], [7, 16, 'lab']], left=[[0, 8, 'office']], front_cut='office', right_cut='lab',
                partitions=[dict(side='bl', line=7, span=[0, 8], mat='lab', gaps=[5])]),
     slots=dict(back={5: 'window_day', 14: 'window_high', 15: 'window_high'}),
     items=[('off_whiteboard_wall', 1, 0, 'SW', 'equations_a'), ('off_whiteboard_wall', 3, 0, 'SW', 'equations_b'),
            ('poster_award', 6, 0, 'SW'),
            ('off_bookshelf', 0, 1, 'SE'), ('off_filing_cabinet', 0, 3, 'SE'), ('off_door', 0, 5, 'SE', 'closed'), ('poster_diploma', 0, 4, 'SE'),
            ('poster_journal', 0, 7, 'SE'),
            ('off_desk', 3, 3, 'SW', 'on'), ('4a_office_chair', 4, 4, 'NE'), ('cafe_chair', 1, 4, 'NE'),
            ('lab_bench_electronics', 8, 0, 'SW', 'on'), ('lab_pegboard', 8.5, 0, 'SW'), ('lab_stool', 9, 1, 'SW'),
            ('lab_3d_printer', 11, 0, 'SW', 'printing'), ('lab_laser_sign', 12, 0, 'SW'), ('lab_tool_chest', 13, 0, 'SW'),
            ('lab_robot_arm', 15, 1, 'SE'), ('lab_optical_table', 12, 3, 'SW', 'on'), ('lab_rover', 9, 5, 'SE'),
            ('poster_neutrino', 10, 0, 'SW', None, 0.25), ('lab_bench_electronics', 12, 6, 'SW', 'off'), ('lab_stool', 13, 5, 'SW'), ('lab_stool', 8, 3, 'SW')],
     lights=[dict(pos=[4.0, 3.3], r=0.9, kind='screen'), dict(pos=[9.5, 0.9], r=1.0, kind='screen'), dict(pos=[5.5, 1.0], r=1.4, kind='window'),
             dict(pos=[13.0, 3.6], r=1.2, kind='lamp', src='laser')],
     chars=[dict(cid='sheldon', mode='stand', hook=['off_whiteboard_wall', 0, 'write'], dir='NE'),
            dict(cid='leonard', mode='stand', hook=['lab_optical_table', 0, 'align'], dir='NE'),
            dict(cid='howard', mode='stand', pos=[10.2, 2.3], dir='SW', anim='idle')],
     zones={'office_sheldon': [0, 0, 7, 8], 'lab_shared': [7, 0, 9, 8]},
     spawns={'from_cafeteria': [1.5, 5.5], 'office_desk': [4.5, 4.4], 'lab_door': [7.5, 5.5]},
     doors=[dict(item='off_door', tile=[0, 5], to='ait_cafeteria', facing='SE'), dict(item='(doorway gap)', tile=[7, 5], connects=['office_sheldon', 'lab_shared'])],
     exits=[dict(id='to_cafeteria', tiles=[[0, 5]], to='ait_cafeteria', to_spawn='from_physics', via='door')])

# ---------------------------------------------------------------- THE AMBER SLICE (Penny's restaurant; original name)
room(id='rest_amber_slice', name='The Amber Slice (restaurant)', kind='interior', size=[14, 9],
     floor=[[0, 0, 14, 9, 'floor_rest_wood_*'], [9, 0, 14, 2, 'floor_rest_tile']],
     walls=dict(back=[[0, 14, 'rest']], left=[[0, 9, 'rest']], front_cut='rest', right_cut='rest'),
     slots=dict(left={1: 'window_day', 2: 'window_day', 6: 'window_day', 7: 'window_day'}),
     items=[('rest_booth', 1, 0, 'SW'), ('rest_booth', 4, 0, 'SW'), ('rest_wall_sign', 2, 0, 'SW', None, 0.45),
            ('rest_kitchen_door', 7, 0, 'SW', 'closed'), ('rest_back_bar', 9, 0, 'SW'), ('rest_server_station', 12, 0, 'SW'), ('rest_cake_display', 13, 0, 'SW'),
            ('rest_bar_counter', 9, 2, 'SW')] + [('rest_bar_stool', 9 + i, 3, 'SW') for i in range(4)] +
           [('lobby_glass_door', 0, 4, 'SE', 'closed'), ('rest_host_stand', 1, 5, 'SE'), ('gen_potted_palm', 0, 8, 'SW'), ('gen_potted_palm', 7, 1, 'SW'),
            ('rest_column', 8, 5, 'SW'), ('rest_stage', 11, 6, 'SW')]
           + two_top(3, 4) + two_top(5, 4) + two_top(3, 7, skip=('s',)) + two_top(6, 7, skip=('s',)) +
           [('rest_pendant_lamp', 1.5, 0.5, 'SW', 'on'), ('rest_pendant_lamp', 4.5, 0.5, 'SW', 'on'), ('rest_pendant_lamp', 3, 4, 'SW', 'on'),
            ('rest_pendant_lamp', 5, 4, 'SW', 'on'), ('rest_pendant_lamp', 10.5, 2, 'SW', 'on')],
     lights=[dict(pos=[2.0, 1.0], r=0.8, kind='pendant'), dict(pos=[5.0, 1.0], r=0.8, kind='pendant'), dict(pos=[3.5, 4.5], r=0.7, kind='pendant'),
             dict(pos=[5.5, 4.5], r=0.7, kind='pendant'), dict(pos=[11.0, 2.5], r=1.1, kind='pendant')],
     chars=[dict(cid='sheldon', mode='sit', hook=['rest_booth', 0, 'seat0']), dict(cid='leonard', mode='sit', hook=['rest_booth', 0, 'seat1']),
            dict(cid='penny', mode='stand', hook=['rest_booth', 0, 'take_order'], dir='NW')],
     zones={'dining': [0, 0, 9, 9], 'bar': [9, 0, 5, 6], 'stage': [11, 6, 3, 2]},
     spawns={'from_street': [1.5, 4.5], 'from_kitchen': [7.5, 1.5], 'behind_bar': [10.5, 1.5]},
     doors=[dict(item='lobby_glass_door', tile=[0, 4], to='street_exterior', facing='SE', note='front door (glass)'),
            dict(item='rest_kitchen_door', tile=[7, 0], to='kitchen (stub)', facing='SW')],
     exits=[dict(id='to_street', tiles=[[0, 4]], to='street_exterior', to_spawn='from_restaurant', via='sidewalk'),
            dict(id='to_kitchen', tiles=[[7, 0]], to='kitchen_stub', to_spawn='', via='door')])

# ---------------------------------------------------------------- Street exterior (Los Robles-style, Pasadena)
room(id='street_exterior', name='2311 building entrance + street (Pasadena)', kind='exterior', size=[16, 10], ztop=6.8, sky=False,
     floor=[[0, 0, 16, 3, 'ground_sidewalk'], [0, 3, 16, 4, 'ground_grass'], [0, 4, 16, 5, 'ground_curb'],
            [0, 5, 16, 10, 'ground_asphalt'], [0, 7, 16, 8, 'ground_asphalt_dash'], [6, 3, 10, 4, 'ground_sidewalk']],
     walls={},
     items=[('ext_building_facade', 0, 0, 'SW', None, 0, {'layer': 3}),
            ('ext_entry_steps', 7, 0.3, 'SW'), ('ext_entrance_doors', 7, 0.16, 'SW', None, 0.45),
            ('ext_wall_lantern', 6.2, 0.3, 'SW', None, 0.2), ('ext_wall_lantern', 8.8, 0.3, 'SW', None, 0.2),
            ('ext_hedge', 1, 0.35, 'SW'), ('ext_hedge', 3.6, 0.35, 'SW'), ('ext_hedge', 10.4, 0.35, 'SW'), ('ext_hedge', 13, 0.35, 'SW'),
            ('ext_palm', 2, 3, 'SW'), ('ext_jacaranda', 4.5, 3, 'SW'), ('ext_jacaranda', 11.5, 3, 'SW'), ('ext_palm', 14, 3, 'SW'),
            ('ext_street_lamp', 10, 3, 'SW'), ('ext_hydrant', 6, 3.2, 'SW'), ('ext_street_sign', 15, 2, 'SE'),
            ('ext_mailbox', 12, 2, 'SW'), ('ext_bench', 4, 1.7, 'SW'), ('ext_trash_can', 9.5, 2.1, 'SW'),
            ('ext_car_hatchback', 2, 5, 'SE')],
     chars=[dict(cid='leonard', mode='stand', pos=[7.0, 2.4], dir='SE', anim='walk', k=1),
            dict(cid='penny', mode='stand', pos=[5.4, 2.3], dir='SE', anim='idle'),
            dict(cid='sheldon', mode='stand', pos=[8.3, 1.75], dir='SW', anim='idle')],
     zones={'sidewalk': [0, 0, 16, 3], 'parkway': [0, 3, 16, 1], 'curb': [0, 4, 16, 1], 'street': [0, 5, 16, 5]},
     force_block=[],
     spawns={'from_lobby': [8.0, 1.6], 'from_campus': [5.5, 7.0], 'from_restaurant': [15.5, 1.5], 'from_raj': [5.5, 7.0], 'car_driver': [4.5, 4.6]},
     doors=[dict(item='ext_entrance_doors', tile=[7, 0], to='lobby', facing='SW', note='doors sit at z=0.45 on the entry steps')],
     exits=[dict(id='to_lobby', tiles=[[7, 0], [8, 0]], to='lobby', to_spawn='from_street', via='door'),
            dict(id='drive_campus', tiles=[[3, 4], [4, 4]], to='ait_cafeteria', to_spawn='from_quad', via='car'),
            dict(id='drive_raj', tiles=[[3, 4], [4, 4]], to='raj_apartment', to_spawn='from_street', via='car'),
            dict(id='walk_restaurant', tiles=[[15, 0], [15, 1], [15, 2]], to='rest_amber_slice', to_spawn='from_street', via='sidewalk')])

# ---------------------------------------------------------------- Lobby (ground floor of 2311)
room(id='lobby', name='2311 lobby (ground floor)', kind='interior', size=[8, 6],
     floor=[[0, 0, 8, 6, 'floor_lobby_tile']],
     walls=dict(back=[[0, 8, 'lobby']], left=[[0, 6, 'lobby']], front_cut='lobby', right_cut='lobby'),
     items=[('lobby_mailboxes', 0.6, 0, 'SW'), ('hall_elevator_broken', 3, 0, 'SW'), ('lobby_stair_up', 6, 0, 'SW'),
            ('lobby_glass_door', 0, 3, 'SE', 'closed'), ('lobby_mat', 1, 3, 'SE'), ('lobby_sconce', 2.4, 0, 'SW'), ('lobby_sconce', 0, 1.2, 'SE'),
            ('gen_potted_palm', 0, 5, 'SW')],
     lights=[],  # sconce pools tried: palette step turns the red grout tan -> reads as stray lines; sconces stay emissive only
     chars=[dict(cid='sheldon', mode='stand', hook=['hall_elevator_broken', 0, 'look'], dir='NE'),
            dict(cid='leonard', mode='stand', pos=[6.0, 4.7], dir='NE', anim='walk', k=2)],
     zones={'lobby': [0, 0, 8, 6]}, force_walk=[[6, 3], [7, 3], [6, 2], [7, 2], [6, 1], [7, 1], [6, 0], [7, 0]],
     spawns={'from_street': [1.5, 3.5], 'from_stairs': [6.9, 4.5]},
     doors=[dict(item='lobby_glass_door', tile=[0, 3], to='street_exterior', facing='SE')],
     exits=[dict(id='to_street', tiles=[[0, 3]], to='street_exterior', to_spawn='from_lobby', via='door'),
            dict(id='stairs_up', tiles=[[6, 0], [7, 0]], to='floor4', to_spawn='stairs_top (hall_stair_flight)', via='stairs',
                 note='three flights in the show; collapsed to one link: lobby_stair_up top -> floor4 hall_stair_flight')])

# ---------------------------------------------------------------- Raj's apartment
room(id='raj_apartment', name="Raj's apartment", kind='interior', size=[10, 8],
     floor=[[0, 0, 10, 8, 'floor_raj_wood_*']],
     walls=dict(back=[[0, 10, 'raj']], left=[[0, 8, 'raj']], front_cut='raj', right_cut='raj'),
     slots=dict(back={6: 'window', 7: 'window', 8: 'window'}),
     items=[('raj_kitchenette', 1, 0, 'SW'), ('raj_bar_cart', 4, 0, 'SW'), ('raj_display_shelf', 4, 0, 'SW'),
            ('raj_telescope_big', 7, 1, 'SW'), ('raj_tapestry_door', 0, 2, 'SE', 'closed'), ('poster_space', 0, 4, 'SE'),
            ('4a_front_door', 0, 6, 'SE', 'closed'), ('raj_rug', 3, 4, 'SW'), ('raj_sofa', 3, 3, 'SW'), ('raj_coffee_oval', 3.5, 4.6, 'SW'),
            ('raj_ufo_lamp', 2, 3, 'SW', 'on'), ('raj_buttercup_chair', 7, 4, 'NW'), ('raj_tv_console', 3, 7, 'NE', 'on'),
            ('raj_dining_round', 7, 6, 'SW'), ('gen_potted_palm', 9, 0, 'SW')],
     lights=[dict(pos=[2.5, 3.5], r=1.7, kind='lamp'), dict(pos=[3.9, 6.3], r=0.95, kind='screen'), dict(pos=[8.0, 7.0], r=0.8, kind='screen', src='crystals')],
     chars=[dict(cid='leonard', mode='stand', hook=['raj_telescope_big', 0, 'look'], dir='NE'),
            dict(cid='penny', mode='sit', hook=['raj_sofa', 0, 'seat1']),
            dict(cid='raj', mode='stand', pos=[5.6, 2.0], dir='SW', anim='idle')],
     zones={'living': [0, 0, 10, 8]},
     spawns={'from_street': [1.5, 6.5], 'telescope': [7.5, 2.4]},
     doors=[dict(item='4a_front_door', tile=[0, 6], to='street_exterior', facing='SE', note='front door (building hallway collapsed)'),
            dict(item='raj_tapestry_door', tile=[0, 2], to='raj_bedroom (stub)', facing='SE')],
     exits=[dict(id='to_street', tiles=[[0, 6]], to='street_exterior', to_spawn='from_raj', via='car'),
            dict(id='to_bedroom', tiles=[[0, 2]], to='raj_bedroom_stub', to_spawn='', via='door')])

WORLD_EDGES = [
    dict(a='street_exterior', b='lobby', via='door', a_exit='to_lobby', b_exit='to_street'),
    dict(a='lobby', b='floor4', via='stairs', a_exit='stairs_up', b_exit='hall_stair_flight (env/maps/floor4_engine.json)'),
    dict(a='street_exterior', b='rest_amber_slice', via='sidewalk', a_exit='walk_restaurant', b_exit='to_street', travel='walk ~5 min'),
    dict(a='street_exterior', b='ait_cafeteria', via='car', a_exit='drive_campus', b_exit='to_quad', travel='drive ~10 min (Leonard drives)'),
    dict(a='street_exterior', b='raj_apartment', via='car', a_exit='drive_raj', b_exit='to_street', travel='drive ~10 min'),
    dict(a='ait_cafeteria', b='ait_physics', via='door', a_exit='to_physics', b_exit='to_cafeteria'),
]
