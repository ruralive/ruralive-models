#!/usr/bin/env python3
"""Downloads the listed models from their sources and packs each into one .glb file."""
import base64, json, os, struct, urllib.parse, urllib.request

AGENT = 'RuraliveModels/1.0 (https://github.com/ruralive/ruralive-models)'
KHRONOS = 'https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/8f492390ddc7a2ae221a1369ef560589cf8c70fb/Models/'
MAX_BYTES = 95 * 1024 * 1024  # GitHub refuses files of 100 MiB.

POLY_HAVEN = {
    'trees': ['pine_tree_01', 'fir_tree_01', 'jacaranda_tree', 'island_tree_01', 'quiver_tree_01', 'tree_small_02', 'dead_tree_trunk', 'tree_stump_01'],
    'plants': ['fern_02', 'shrub_01', 'shrub_02', 'moss_01', 'nettle_plant', 'dandelion_01', 'flower_gazania', 'potted_plant_01'],
    'grass': ['grass_medium_01', 'grass_medium_02', 'grass_bermuda_01'],
    'rocks': ['boulder_01', 'rock_moss_set_01', 'rock_face_01', 'namaqualand_boulder_02', 'coastal_cliff_01', 'mountainside', 'moon_rock_01', 'moon_rock_02'],
    'ground': ['pine_roots', 'bark_debris_01', 'sand_rocks_small_01'],
    'animals': ['street_rat'],
}
NASA = 'https://raw.githubusercontent.com/nasa/NASA-3D-Resources/11ebb4ee043715aefbba6aeec8a61746fad67fa7/3D%20Models/'
NASA_MODELS = {
    'astronaut': ('Astronaut', 'Astronaut'),
    'z2-spacesuit': ('Z2 Spacesuit', 'Z2 Spacesuit'),
    'mark-3-spacesuit': ('Mark III Spacesuit', 'Mark III Spacesuit'),
    'gemini-spacesuit': ('Gemini Spacesuit', 'Gemini Spacesuit'),
    'mercury-spacesuit': ('Mercury Spacesuit', 'Mercury Spacesuit'),
    'perseverance-rover': ('Perseverance Rover', 'Mars 2020 Perseverance Rover'),
    'ingenuity-helicopter': ('Ingenuity Helicopter', 'Ingenuity Mars Helicopter'),
    'viking-lander': ('Viking Lander', 'Viking Lander'),
    'apollo-lunar-module': ('Apollo Lunar Module', 'Apollo Lunar Module'),
    'saturn-v': ('Saturn V', 'Saturn V'),
    'space-shuttle': ('Space Shuttle', 'Space Shuttle (A)'),
    'space-station': ('International Space Station', 'International Space Station (ISS) (A)'),
    'hubble': ('Hubble Telescope', 'Hubble Space Telescope (A)'),
    'james-webb': ('James Webb Telescope', 'James Webb Space Telescope (A)'),
    'voyager': ('Voyager Probe', 'Voyager Probe (A)'),
    'cassini': ('Cassini-Huygens', 'Cassini-Huygens (A)'),
    'mission-control': ('Mission Control Room', 'JSC Mission Control Room'),
}
KHRONOS_MODELS = {
    'barramundi_fish': {'name': 'Barramundi Fish', 'category': 'animals', 'folder': 'BarramundiFish', 'license': 'CC0-1.0', 'authors': 'Microsoft'},
}


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': AGENT})
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def fetch_json(url):
    return json.loads(fetch(url))


def pack_glb(gltf_bytes, files):
    """Turns a .gltf and its separate files into a single binary .glb."""
    gltf = json.loads(gltf_bytes)
    binary = bytearray()

    def add(data):
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        binary.extend(data)
        return offset

    def data_of(uri):
        if uri.startswith('data:'):
            return base64.b64decode(uri.split(',', 1)[1])
        return files[urllib.request.url2pathname(uri).replace(os.sep, '/')]

    offsets = [add(data_of(buffer['uri'])) for buffer in gltf.get('buffers', [])]
    for view in gltf.get('bufferViews', []):
        view['byteOffset'] = view.get('byteOffset', 0) + offsets[view.get('buffer', 0)]
        view['buffer'] = 0
    for image in gltf.get('images', []):
        if 'uri' in image:
            data = data_of(image.pop('uri'))
            kind = 'image/png' if data[:4] == b'\x89PNG' else 'image/webp' if data[8:12] == b'WEBP' else 'image/jpeg'
            image['mimeType'] = kind
            image['bufferView'] = len(gltf['bufferViews'])
            gltf['bufferViews'].append({'buffer': 0, 'byteOffset': add(data), 'byteLength': len(data)})
    while len(binary) % 4:
        binary.append(0)
    gltf['buffers'] = [{'byteLength': len(binary)}]
    text = json.dumps(gltf, separators=(',', ':')).encode()
    text += b' ' * (-len(text) % 4)
    total = 12 + 8 + len(text) + 8 + len(binary)
    return b''.join([struct.pack('<4sII', b'glTF', 2, total), struct.pack('<I4s', len(text), b'JSON'), text,
                     struct.pack('<I4s', len(binary), b'BIN\0'), bytes(binary)])


def main():
    os.makedirs('models', exist_ok=True)
    catalog, skipped = [], []

    def save(key, data, entry):
        if len(data) > MAX_BYTES:
            skipped.append(key + ' (' + str(len(data) // 1048576) + ' MB)')
            return
        with open('models/' + key + '.glb', 'wb') as out:
            out.write(data)
        catalog.append({'id': key, 'file': 'models/' + key + '.glb', 'megabytes': round(len(data) / 1048576, 1), **entry})

    for category, ids in POLY_HAVEN.items():
        for key in ids:
            try:
                info = fetch_json('https://api.polyhaven.com/info/' + key)
                source = fetch_json('https://api.polyhaven.com/files/' + key)['gltf']['1k']['gltf']
                files = {name: fetch(item['url']) for name, item in source['include'].items()}
                save(key, pack_glb(fetch(source['url']), files), {
                    'name': info['name'], 'category': category, 'license': 'CC0-1.0', 'source': 'https://polyhaven.com/a/' + key,
                    'authors': ', '.join(info.get('authors', {})),
                })
            except Exception as error:  # One unavailable model must not stop the others.
                skipped.append(key + ' (' + str(error) + ')')
    for key, (name, folder) in NASA_MODELS.items():
        quoted = urllib.parse.quote(folder)
        save(key, fetch(NASA + quoted + '/' + quoted + '.glb'), {
            'name': name, 'category': 'space', 'license': 'NASA, no copyright (see README)',
            'source': 'https://github.com/nasa/NASA-3D-Resources/tree/master/3D%20Models/' + quoted, 'authors': 'NASA',
        })
    for key, entry in KHRONOS_MODELS.items():
        folder = entry.get('folder', entry['name'])
        path = folder + '/glTF-Binary/' + folder + '.glb'
        save(key, fetch(KHRONOS + path), {'name': entry['name'], 'category': entry['category'], 'license': entry['license'],
                                          'source': 'https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/' + folder, 'authors': entry['authors']})
    catalog.sort(key=lambda item: (item['category'], item['name']))
    with open('models.json', 'w') as out:
        json.dump(catalog, out, indent=1)
    with open('CREDITS.md', 'w') as out:
        out.write('# Credits\n\nGenerated by `tools/build_models.py`. Each model is listed with its source, authors and licence.\n\n')
        out.write('| Model | Category | Authors | Licence | Source |\n|---|---|---|---|---|\n')
        for item in catalog:
            out.write('| {name} | {category} | {authors} | {license} | {source} |\n'.format(**item))
    print('BUILT', len(catalog), 'MB', sum(item['megabytes'] for item in catalog))
    for item in skipped:
        print('SKIPPED', item)


if __name__ == '__main__':
    main()
