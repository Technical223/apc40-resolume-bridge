// Shared project validation and mapping, independent of the rendering engine.
export const TYPES = ["room", "projection", "panel", "strip"];
export function validateObject(data) {
  if (!TYPES.includes(data.type)) throw Error("Unknown object type");
  if (!Number.isInteger(data.pixels) || data.pixels < 1 || data.pixels > 4096)
    throw Error("Pixels must be 1–4096");
  if (
    !Number.isInteger(data.rows) ||
    data.rows < 1 ||
    data.rows > 4096 ||
    data.rows * data.pixels > 4096
  )
    throw Error("At most 4096 pixels per object");
  return data;
}
export function effective(node, key) {
  for (let n = node; n; n = n.parent)
    if (n.userData?.apcEditor?.[key] === false) return false;
  return true;
}
export function sampleUV(quad, column, row, columns, rows) {
  const x = (column + 0.5) / columns,
    y = (row + 0.5) / rows;
  return [
    (1 - x) * (1 - y) * quad[0][0] +
      x * (1 - y) * quad[1][0] +
      x * y * quad[2][0] +
      (1 - x) * y * quad[3][0],
    (1 - x) * (1 - y) * quad[0][1] +
      x * (1 - y) * quad[1][1] +
      x * y * quad[2][1] +
      (1 - x) * y * quad[3][1],
  ];
}
export const COMPOSITION = [
  [0, 1],
  [1, 1],
  [1, 0],
  [0, 0],
];

// Preserve the frame clock phase instead of discarding fractional monitor ticks.
export function advanceFrame(now, last) {
  const step = 1000 / 30;
  const ticks = Math.floor((now - last + 0.001) / step);
  return ticks > 0 ? last + ticks * step : null;
}
// A translation-only pivot parent preserves geometry, UVs, skinning and world transforms.
export function centerPivot(node, T) {
  if (!node.parent) throw Error('Select a scene object first.');
  node.updateWorldMatrix(true, true);
  const box = new T.Box3().setFromObject(node);
  if (box.isEmpty()) throw Error('This object has no geometry to center.');
  const center = box.getCenter(new T.Vector3());
  if (node.userData.apcPivot) {
    const offset = node.worldToLocal(center.clone());
    const next = node.parent.worldToLocal(center.clone());
    node.position.copy(next);
    for (const child of node.children) child.position.sub(offset);
    node.updateWorldMatrix(true, true);
    return node;
  }
  const parent = node.parent, pivot = new T.Group();
  pivot.name = (node.name || 'Object') + ' · pivot';
  pivot.userData.apcPivot = true;
  pivot.position.copy(parent.worldToLocal(center));
  parent.add(pivot);
  pivot.updateWorldMatrix(true, false);
  pivot.attach(node);
  return pivot;
}
