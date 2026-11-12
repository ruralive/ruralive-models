"""The cast: every person and humanoid animal of the library, as specs for human.build."""
import human
import materials as M


def _hivis(color='#e6d21f'):
    return M.cloth(color, 'hivis', 300, 0.7, 0.2, 'stripes', '#c9ccce', 9)


CAST = {
    # everyday people
    'woman-in-dress': dict(height=1.66, shoulders=0.86, hips=1.04, girth=0.86, bust=0.9,
                           skin='#d9a27e', hair='long', hair_color='#3a2314', top='dress',
                           top_color='#a8324a', hem=0.52, flare=0.13, skirt=True, shoes='shoes',
                           shoe_color='#1b1b1e', lips='#a3434a', necklace=False, eyes='#3d5a3a'),
    'woman-in-workwear': dict(height=1.68, shoulders=0.9, hips=1.02, girth=0.9, bust=0.8,
                              skin='#8d5b3e', hair='bun', hair_color='#16100c', top='shirt',
                              top_color='#39607a', bottom_color='#3c3f45', shoes='boots',
                              shoe_color='#4a3222', belt=True, collar=True, lips='#7d3f3a'),
    'man-in-denim': dict(height=1.8, skin='#c98f6b', hair='short', hair_color='#2a1c14',
                         top='shirt', top_mat_kind='denim', top_color='#5d7ea8',
                         bottom_color='#27395c', belt=True, collar=True, buttons=True,
                         shoe_color='#3a2618', beard='short'),
    'man-in-outdoor-jacket': dict(height=1.82, shoulders=1.05, girth=1.05, skin='#e0b592',
                                  hair='short', hair_color='#6b4a2a', top='jacket',
                                  top_color='#3f5a3a', bottom_color='#4a4338', shoes='boots',
                                  shoe_color='#2e2118', scarf='#8a2f24', beard='short'),
    'cavewoman': dict(height=1.6, shoulders=0.92, hips=1.05, girth=0.95, bust=0.85,
                      skin='#a8744f', hair='wild', hair_color='#1c120c', top='fur', skirt=True,
                      hem=0.62, bottom='fur', shoes='bare', necklace=True, fur_top='#6b4a2e'),
    'caveman': dict(height=1.7, shoulders=1.12, girth=1.15, skin='#9c6a48', hair='wild',
                    hair_color='#20140c', top='fur', skirt=True, hem=0.6, bottom='fur',
                    shoes='bare', beard='long', club=True, fur_top='#4f3a26', jaw=1.15),
    # body types
    'tall-slim-person': dict(height=1.92, shoulders=0.92, hips=0.92, girth=0.82,
                             skin='#e3bd9d', hair='short', hair_color='#b08a4a', top='tshirt',
                             top_color='#c4472f', bottom_color='#2c3b57', shoe_color='#e8e6e1'),
    'plus-size-person': dict(height=1.7, shoulders=1.08, hips=1.2, girth=1.38, belly=1.3,
                             bust=0.9, skin='#c58b62', hair='curly', hair_color='#1e1410',
                             top='shirt', top_color='#5a3f7a', bottom_color='#2a2a2e',
                             shoe_color='#2a1d16', neck=1.15),
    'short-stocky-person': dict(height=1.56, shoulders=1.14, hips=1.08, girth=1.22, belly=1.1,
                                skin='#b07a55', hair='short', hair_color='#3b2a1c',
                                top='tshirt', top_color='#2f6b5a', bottom='shorts',
                                bottom_color='#6a5a44', shoe_color='#30343a', beard='short',
                                neck=1.15, jaw=1.1),
    'tall-athletic-person': dict(height=1.9, shoulders=1.18, hips=0.96, girth=1.0,
                                 skin='#6f452e', hair='short', hair_color='#0e0a08',
                                 top='tank', top_color='#d8d8d6', bottom='shorts',
                                 bottom_color='#1c2a44', shoe_color='#d94f2a', neck=1.1),
    'slim-construction-worker': dict(height=1.78, shoulders=0.94, girth=0.86, skin='#d3a17c',
                                     hair='short', hair_color='#3a2a1c', top='shirt',
                                     top_color='#4a6a8a', vest=True, bottom_color='#3a4a5c',
                                     shoes='boots', shoe_color='#5a3d22', helmet='#f2c21a',
                                     belt=True),
    'plus-size-construction-worker': dict(height=1.76, shoulders=1.12, hips=1.15, girth=1.36,
                                          belly=1.3, skin='#a8704a', hair='short',
                                          hair_color='#1a120c', top='shirt',
                                          top_color='#7a3b2a', vest=True,
                                          bottom_color='#3c3c3a', shoes='boots',
                                          shoe_color='#3d2a1a', helmet='#f08a1c', belt=True,
                                          beard='short', neck=1.15),
    # humanoid animals
    'humanoid-fox': dict(height=1.62, shoulders=0.9, girth=0.88, species='fox', fur='#c5601e',
                         fur2='#efe6d6', ear=0.11, tail_len=0.55, top='jacket',
                         top_color='#2f4a3a', bottom_color='#4a3a2a', shoes='boots',
                         shoe_color='#2a1c14', scarf='#b5892a'),
    'humanoid-rabbit': dict(height=1.5, shoulders=0.86, girth=0.9, species='rabbit',
                            fur='#cfc6ba', fur2='#f3efe8', ear=0.2, tail_len=0.1, top='shirt',
                            top_color='#6a8fb5', bottom='shorts', bottom_color='#6a4a3a',
                            shoes='bare', collar=True),
    'humanoid-bear': dict(height=1.9, shoulders=1.2, hips=1.15, girth=1.35, belly=1.2,
                          species='bear', fur='#5a3b24', fur2='#8a6a48', ear=0.05,
                          tail_len=0.1, top='shirt', top_mat_kind='check', top_color='#9a2f28',
                          bottom_color='#2c3b57', shoes='boots', shoe_color='#2a1c14',
                          belt=True, neck=1.25),
    'humanoid-pig': dict(height=1.58, shoulders=1.05, hips=1.15, girth=1.3, belly=1.3,
                         species='pig', fur='#e0a39a', ear=0.06, tail_len=0.12, top='shirt',
                         top_color='#e8e2d2', vest=True, vest_color='#3a3f5a',
                         bottom_color='#4a4038', shoe_color='#2a1c14', neck=1.2),
    # astronauts: an original suit, not a copy of any agency's
    'cinema-astronaut': dict(height=1.82, eva=True, top_color='#e4e2dc', shoe_color='#c9c7c1',
                             accent='#d9472b', visor_color='#f2b545', suit_kind='white'),
    'cinema-astronaut-black': dict(height=1.82, eva=True, top_color='#1f2126',
                                   shoe_color='#17181b', accent='#35d6ff',
                                   visor_color='#9fd8ff', hard_color='#2a2d33',
                                   suit_kind='dark'),
    'cinema-astronaut-orange': dict(height=1.78, eva=True, top_color='#d9641c',
                                    shoe_color='#2a2b2e', accent='#f4f1ea',
                                    visor_color='#d9dde2', hard_color='#ece9e2',
                                    suit_kind='orange'),
    # more suits, each its own design
    'z2-spacesuit': dict(height=1.8, eva=True, top_color='#8d949c', shoe_color='#2a2d33',
                         accent='#35ffd0', visor_color='#7fe9ff', hard_color='#3a3f47'),
    'mark-3-spacesuit': dict(height=1.84, eva=True, top_color='#ecebe6', shoe_color='#d9d7d0',
                             accent='#2f5fd0', visor_color='#f2b545', girth=1.15,
                             shoulders=1.1),
    'gemini-spacesuit': dict(height=1.76, eva=True, top_color='#f0efe9', shoe_color='#1d1f24',
                             accent='#1d1f24', visor_color='#e9eef2', girth=0.9),
    'mercury-spacesuit': dict(height=1.74, eva=True, top_color='#c4c9cf', shoe_color='#22252a',
                              accent='#c4c9cf', visor_color='#dfe6ec', hard_color='#d9dde1',
                              girth=0.88, suit_kind='silver'),
    # Story Worlds cast
    'lyra': dict(height=1.7, shoulders=0.9, hips=1.0, girth=0.86, bust=0.75, skin='#b98562',
                 hair='ponytail', hair_color='#101018', top='suit', top_color='#d9dde2',
                 bottom_color='#aab2bc', bottom_kind='cloth', shoes='boots',
                 shoe_color='#30343c', visor='#38d6ff', eyes='#2f6f8a'),
    'teo': dict(height=1.8, skin='#8a5a3c', hair='short', hair_color='#0c0a08', top='jacket',
                top_color='#2c3e5a', bottom_color='#22262e', bottom_kind='cloth',
                shoes='boots', shoe_color='#17191d', beard='short'),
    'teo-child': dict(height=1.18, head=1.28, shoulders=0.9, girth=0.95, skin='#8a5a3c',
                      hair='curly', hair_color='#0c0a08', top='tshirt', top_color='#e0a52a',
                      bottom='shorts', bottom_color='#2c3e5a', shoe_color='#e6e2da'),
    'ismael': dict(height=1.74, shoulders=0.98, girth=1.1, belly=1.15, skin='#c9a183',
                   hair='bald', hair_color='#bdb8b0', top='coat', top_color='#5a5046',
                   bottom_color='#33302c', bottom_kind='cloth', shoe_color='#201812',
                   beard='long', glasses=True, beard_color='#c9c5bd'),
    'tanaka-bell': dict(height=1.72, shoulders=0.95, girth=0.92, bust=0.7, skin='#e2bf9f',
                        hair='bun', hair_color='#15151a', top='suit', top_color='#1f2d4a',
                        bottom_color='#1a2438', bottom_kind='cloth', shoes='boots',
                        shoe_color='#101216', collar=True, buttons=True, belt=True),
    'mira': dict(height=1.64, shoulders=0.86, hips=1.0, girth=0.84, bust=0.75, skin='#d6a585',
                 hair='long', hair_color='#5a2a1c', top='jacket', top_color='#c9a23a',
                 bottom_color='#2f3340', shoe_color='#e4e0d8', scarf='#b5462f',
                 eyes='#5a7a3a'),
    'mira-director': dict(height=1.78, shoulders=1.0, girth=1.0, skin='#c58e68',
                          hair='short', hair_color='#3a3a3e', top='jacket',
                          top_color='#2a2a2e', bottom_color='#3a3a40', bottom_kind='cloth',
                          shoe_color='#1a1410', glasses=True, beard='short', clipboard=True),
    'mira-director-child': dict(height=1.2, head=1.28, shoulders=0.9, girth=0.95,
                                skin='#c58e68', hair='short', hair_color='#3a2a1c',
                                top='tshirt', top_color='#3f7ab5', bottom='shorts',
                                bottom_color='#6a5a44', shoe_color='#d94f2a', glasses=True),
    'producer-vale': dict(height=1.84, shoulders=1.06, girth=1.12, belly=1.12, skin='#e6c4a8',
                          hair='short', hair_color='#8a8a8c', top='suit', top_color='#2b2f3a',
                          bottom_color='#2b2f3a', bottom_kind='cloth', shoe_color='#120e0c',
                          collar=True, buttons=True, neck=1.1),
}


def _materials(spec):
    s = dict(spec)
    kind = s.pop('top_mat_kind', None)
    if s.get('eva'):
        s['top_mat'] = M.foil(s['top_color'], 'top', 0.35) if s.get('suit_kind') == 'silver' \
            else M.cloth(s['top_color'], 'top', 150, 0.8, 0.5)
        s['shoes_mat'] = M.cloth(s['shoe_color'], 'shoes', 120, 0.85, 0.5)
        s['glove_mat'] = M.cloth(s['shoe_color'], 'gloves', 200, 0.8, 0.4)
        return s
    color = s.get('top_color', '#b8b2a6')
    if s.get('top') == 'fur':
        s['top_mat'] = M.fur(s.get('fur_top', '#6b4a2e'), name='top', scale=0.6, spots='#3a2616',
                             spot_scale=5)
    elif kind == 'denim':
        s['top_mat'] = M.denim(color, 'top')
    elif kind == 'check':
        s['top_mat'] = M.cloth(color, 'top', pattern='check', color2='#1c1a1a', pattern_scale=26)
    elif s.get('top') in ('jacket', 'coat'):
        s['top_mat'] = M.cloth(color, 'top', 260, 0.74, 0.35)
    elif s.get('top') == 'suit':
        s['top_mat'] = M.cloth(color, 'top', 620, 0.62, 0.15)
    if s.get('bottom_kind') == 'cloth':
        s['bottom_mat'] = M.cloth(s.get('bottom_color', '#333'), 'bottom', 520, 0.7, 0.2)
    if s.get('bottom') == 'shorts':
        s['bottom_mat'] = M.cloth(s.get('bottom_color', '#555'), 'bottom', 300, 0.8, 0.3)
    if s.get('vest'):
        s['vest_mat'] = M.cloth(s['vest_color'], 'vest', 500, 0.6) if s.get('vest_color') \
            else _hivis()
    if s.get('shoe_color', '').lower() in ('#e8e6e1', '#e6e2da', '#e4e0d8', '#d94f2a'):
        s['shoes_mat'] = M.cloth(s['shoe_color'], 'shoes', 200, 0.7, 0.4)
    return s


def make(model_id):
    spec = _materials(dict(CAST[model_id], name=model_id))
    rig, mesh = human.build(spec)
    return rig, mesh


MODELS = {model_id: (lambda i=model_id: make(i)) for model_id in CAST}
ATLAS = {model_id: 2048 for model_id in CAST}
