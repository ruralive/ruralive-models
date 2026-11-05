import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import draco from 'draco3dgltf';
import { mkdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';

const output = process.argv[2];
if (!output) throw new Error('Usage: node animations/decode.mjs OUTPUT_DIRECTORY');
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({'draco3d.decoder': await draco.createDecoderModule()});
await mkdir(output, {recursive: true});
for (const entry of JSON.parse(await readFile('models.json', 'utf8'))) {
  const doc = await io.read(entry.file);
  doc.getRoot().listExtensionsUsed().find(e => e.extensionName === 'KHR_draco_mesh_compression')?.dispose();
  await io.write(join(output, entry.id + '.glb'), doc);
}
