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
