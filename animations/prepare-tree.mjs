// Keep full alpha-tested foliage islands instead of collapsing their UV cards into one another.
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { prune } from '@gltf-transform/functions';
import { MeshoptSimplifier as simplify } from 'meshoptimizer';

const [input, output] = process.argv.slice(2);
if (!input || !output) throw new Error('Usage: prepare-tree.mjs INPUT.gltf OUTPUT.glb');
await simplify.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const document = await io.read(input);
for (const scene of document.getRoot().listScenes()) {
  const variants = scene.listChildren();
  for (const node of variants.slice(1)) scene.removeChild(node);
}
await document.transform(prune({ keepAttributes: true }));

function foliage(indices, positions, budget, broaden) {
  const count = positions.length / 3;
  const roots = Int32Array.from({ length: count }, (_, i) => i);
  const find = (i) => {
    while (roots[i] !== i) {
      roots[i] = roots[roots[i]];
      i = roots[i];
    }
    return i;
  };
  for (let i = 0; i < indices.length; i += 3) {
    const root = find(indices[i]);
    roots[find(indices[i + 1])] = root;
    roots[find(indices[i + 2])] = root;
  }
  const threshold = budget / indices.length;
  const chosen = new Uint32Array(indices.length);
  let n = 0;
  for (let i = 0; i < indices.length; i += 3) {
    const key = find(indices[i]);
    const hash = Math.imul(key ^ (key >>> 16), 0x45d9f3b);
    const rank = ((hash ^ (hash >>> 16)) >>> 0) / 4294967296;
    if (rank >= threshold) continue;
    chosen[n++] = indices[i]; chosen[n++] = indices[i + 1]; chosen[n++] = indices[i + 2];
  }
  if (broaden) {
    const seen = new Uint8Array(count);
    const centers = new Float32Array(positions.length);
    const members = new Uint32Array(count);
    for (let i = 0; i < n; i++) {
      const vertex = chosen[i];
      if (seen[vertex]) continue;
      seen[vertex] = 1;
      const root = find(vertex);
      members[root]++;
      for (let axis = 0; axis < 3; axis++) centers[root * 3 + axis] += positions[vertex * 3 + axis];
    }
    for (let vertex = 0; vertex < count; vertex++) {
      if (!seen[vertex]) continue;
      const root = find(vertex);
      // Broaden tiny needle islands around their own centers, leaving larger branch groups intact.
      if (members[root] > 120) continue;
      for (let axis = 0; axis < 3; axis++) {
        const center = centers[root * 3 + axis] / members[root];
        positions[vertex * 3 + axis] = center + (positions[vertex * 3 + axis] - center) * broaden;
      }
    }
  }
  return chosen.subarray(0, n);
}

for (const mesh of document.getRoot().listMeshes()) for (const primitive of mesh.listPrimitives()) {
  const indices = Uint32Array.from(primitive.getIndices().getArray());
  const positions = primitive.getAttribute('POSITION').getArray();
  const material = primitive.getMaterial();
  const leafy = /twig|leaves/i.test(material?.getName() ?? '');
  const conifer = /^(pine|fir)_tree_01_twig$/.test(material?.getName() ?? '');
  if (conifer) {
    // These sources model the needles in geometry. The diffuse JPG has no alpha.
    const needles = material.getBaseColorTexture();
    if (needles?.getMimeType() === 'image/jpeg') material.setAlphaMode('OPAQUE');
    // A small colour-matched fill approximates light transmitted through needles.
    material.setEmissiveTexture(needles).setEmissiveFactor([.18, .22, .13]).setNormalScale(.48);
  }
  const budget = conifer ? 1_620_000 : leafy ? 780_000 : 144_999;
  if (indices.length <= budget) continue;
  let retained = leafy ? foliage(indices, positions, budget, conifer ? (material.getName().startsWith('pine') ? 1.85 : 1.45) : 0)
    : simplify.simplify(indices, positions, 3, budget, .018, ['Permissive'])[0];
  if (retained.length < budget / 10 || retained.length > budget * 1.35) {
    retained = simplify.simplifySloppy(indices, positions, 3, null, budget, .12)[0];
  }
  if (!retained.length || retained.length > budget * 2) throw new Error('Could not reduce ' + primitive.getMaterial()?.getName());
  const [map, count] = simplify.compactMesh(retained);
  const index = primitive.getIndices().clone();
  index.setArray(count < 65536 ? Uint16Array.from(retained) : retained);
  primitive.setIndices(index);
  for (const semantic of primitive.listSemantics()) {
    const attr = primitive.getAttribute(semantic), source = attr.getArray(), width = attr.getElementSize();
    const compact = new source.constructor(count * width);
    for (let i = 0; i < map.length; i++) {
      const dest = map[i];
      if (dest === 0xffffffff) continue;
      for (let k = 0; k < width; k++) compact[dest * width + k] = source[i * width + k];
    }
    primitive.setAttribute(semantic, attr.clone().setArray(compact));
  }
  console.log(primitive.getMaterial()?.getName(), indices.length / 3, '→', retained.length / 3, 'triangles');
}
await document.transform(prune({ keepAttributes: true }));
await io.write(output, document);
