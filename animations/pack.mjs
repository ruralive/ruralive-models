import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, KHRDracoMeshCompression } from '@gltf-transform/extensions';
import draco from 'draco3dgltf';
import { readdir, readFile, rename, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { validateBytes } from 'gltf-validator';

const directory = process.argv[2];
if (!directory) throw new Error('Usage: node animations/pack.mjs GLB_DIRECTORY');
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({'draco3d.encoder': await draco.createEncoderModule()});
for (const file of (await readdir(directory)).filter(f => f.endsWith('.glb')).sort()) {
  const path = join(directory, file);
  if ((await stat(path)).size > 50_000_000) {
    const doc = await io.read(path);
    doc.createExtension(KHRDracoMeshCompression).setRequired(true).setEncoderOptions({
      method: KHRDracoMeshCompression.EncoderMethod.SEQUENTIAL,
      quantizationBits: { POSITION: 16, NORMAL: 12, TEX_COORD: 14, GENERIC: 14 },
    });
    await io.write(path + '.tmp.glb', doc);
    await rename(path + '.tmp.glb', path);
  }
  const bytes = await readFile(path);
  if (bytes.length >= 100 * 1024 * 1024) throw new Error(file + ' exceeds GitHub’s file size limit');
  const r = await validateBytes(bytes, {maxIssues: 0});
  if (r.issues.numErrors) throw new Error(file + '\n' + JSON.stringify(r.issues.messages.filter(i => i.severity === 0).slice(0, 20)));
  console.log(file, bytes.length, 'bytes; glTF validation passed');
}
