// Compress the built GLBs with Draco, validate them and write cinema/manifest.json.
// Usage: node tools/cinema/pack.mjs [DIRECTORY]   (run after tools/cinema/build.py)
import { createRequire } from 'node:module';
import { readdir, readFile, rename, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const require = createRequire(join(root, 'tools/cinema/package.json'));
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS, KHRDracoMeshCompression } = require('@gltf-transform/extensions');
const { resample, prune, dedup } = require('@gltf-transform/functions');
const draco = require('draco3dgltf');
const { validateBytes } = require('gltf-validator');

const args = process.argv.slice(2);
const again = args.includes('--again');
const directory = resolve(args.find((a) => !a.startsWith('--')) ?? join(root, 'cinema'));
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'draco3d.encoder': await draco.createEncoderModule(),
  'draco3d.decoder': await draco.createDecoderModule(),
});
const models = [];
for (const file of (await readdir(directory)).filter((f) => f.endsWith('.glb') && !f.endsWith('.packing.glb')).sort()) {
  const path = join(directory, file);
  const doc = await io.read(path);
  const packed = doc.getRoot().listExtensionsUsed().some((e) => e.extensionName === 'KHR_draco_mesh_compression');
  if (!packed || again) {
    // Clips are sampled every frame; this drops the keys a straight line already covers.
    await doc.transform(resample({ tolerance: 0.0006 }), dedup(), prune());
    doc.createExtension(KHRDracoMeshCompression).setRequired(true).setEncoderOptions({
      method: KHRDracoMeshCompression.EncoderMethod.EDGEBREAKER,
      quantizationBits: { POSITION: 14, NORMAL: 10, TEX_COORD: 12, GENERIC: 12 },
    });
    const packedPath = path.replace(/\.glb$/u, '.packing.glb');
    await io.write(packedPath, doc);
    await rename(packedPath, path);
  }
  const bytes = await readFile(path);
  const report = await validateBytes(new Uint8Array(bytes), { maxIssues: 0 });
  if (report.issues.numErrors) {
    throw new Error(file + '\n' + JSON.stringify(report.issues.messages.filter((i) => i.severity === 0).slice(0, 10)));
  }
  let meta = {};
  try {
    meta = JSON.parse(await readFile(join(directory, '.meta', file.replace(/\.glb$/u, '.json')), 'utf8'));
  } catch {
    meta = { id: file.replace(/\.glb$/u, ''), animations: doc.getRoot().listAnimations().map((a) => a.getName()) };
  }
  models.push({ file, bytes: bytes.length, ...meta, animation: meta.animations?.[0] ?? null });
  console.log(file, bytes.length, 'bytes', packed ? '(already packed)' : 'packed', '· valid');
}
await writeFile(
  join(directory, 'manifest.json'),
  JSON.stringify({ license: 'LicenseRef-Ruralive-Models-1.0', generator: 'tools/cinema', models }, null, 1) + '\n',
);
console.log(models.length, 'models,', (models.reduce((n, m) => n + m.bytes, 0) / 1e6).toFixed(1), 'MB');
