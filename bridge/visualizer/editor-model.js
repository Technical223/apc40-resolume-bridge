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
  if (!node.parent) throw Error("Select a scene object first.");
  node.updateWorldMatrix(true, true);
  const box = new T.Box3().setFromObject(node);
  if (box.isEmpty()) throw Error("This object has no geometry to center.");
  const center = box.getCenter(new T.Vector3());
  if (node.userData.apcPivot) {
    const offset = node.worldToLocal(center.clone());
    const next = node.parent.worldToLocal(center.clone());
    node.position.copy(next);
    for (const child of node.children) child.position.sub(offset);
    node.updateWorldMatrix(true, true);
    return node;
  }
  const parent = node.parent,
    pivot = new T.Group();
  pivot.name = (node.name || "Object") + " · pivot";
  pivot.userData.apcPivot = true;
  pivot.position.copy(parent.worldToLocal(center));
  parent.add(pivot);
  pivot.updateWorldMatrix(true, false);
  pivot.attach(node);
  return pivot;
}

export function dimensions(node, T) {
  node.updateWorldMatrix(true, true);
  const inverse = node.matrixWorld.clone().invert(),
    box = new T.Box3();
  node.traverse((child) => {
    if (!child.geometry) return;
    child.geometry.computeBoundingBox();
    if (child.geometry.boundingBox)
      box.union(
        child.geometry.boundingBox
          .clone()
          .applyMatrix4(inverse.clone().multiply(child.matrixWorld)),
      );
  });
  if (box.isEmpty()) return new T.Vector3();
  const size = box.getSize(new T.Vector3()),
    matrix = new T.Matrix3().setFromMatrix4(node.matrixWorld);
  for (const [index, axis] of ["x", "y", "z"].entries())
    size[axis] *= new T.Vector3()
      .setComponent(index, 1)
      .applyMatrix3(matrix)
      .length();
  return size;
}
export function resizeDimension(node, axis, meters, T) {
  if (
    !["x", "y", "z"].includes(axis) ||
    !Number.isFinite(meters) ||
    meters < 0.001 ||
    meters > 10000
  )
    throw Error("Dimension must be 0.001–10000 meters.");
  const current = dimensions(node, T)[axis];
  if (current < 1e-8)
    throw Error("A flat surface has no thickness on this axis.");
  node.scale[axis] *= meters / current;
  node.updateWorldMatrix(true, true);
}
export function duplicateRow(node, axis, count, spacing, T) {
  if (
    !node.parent ||
    !["x", "y", "z"].includes(axis) ||
    !Number.isInteger(count) ||
    count < 2 ||
    count > 32 ||
    !Number.isFinite(spacing) ||
    spacing < 0.001 ||
    spacing > 1000
  )
    throw Error("Use 2–32 objects and spacing of 0.001–1000 meters.");
  node.updateWorldMatrix(true, true);
  const origin = node.getWorldPosition(new T.Vector3());
  const direction = new T.Vector3()
    .setComponent(["x", "y", "z"].indexOf(axis), 1)
    .transformDirection(node.matrixWorld);
  const copies = [];
  for (let index = 1; index < count; index++) {
    const copy = node.clone(true);
    copy.traverse((child) => (child.userData.apcEditorId = child.uuid));
    copy.name = (node.name || "Object") + " " + (index + 1);
    copy.position.copy(
      node.parent.worldToLocal(
        origin.clone().addScaledVector(direction, spacing * index),
      ),
    );
    node.parent.add(copy);
    copies.push(copy);
  }
  return copies;
}

export function sceneState(root) {
  const objects = [];
  root.traverse((node) => {
    if (node === root) return;
    node.userData.apcEditorId ||= node.uuid;
    objects.push({
      id: node.userData.apcEditorId,
      parent: node.parent === root ? null : node.parent.userData.apcEditorId,
      name: node.name,
      position: node.position.toArray(),
      quaternion: node.quaternion.toArray(),
      scale: node.scale.toArray(),
      data: { ...node.userData.apcEditor },
    });
  });
  return { version: 1, objects };
}
export function restoreSceneState(root, state) {
  if (
    state?.version !== 1 ||
    !Array.isArray(state.objects) ||
    state.objects.length > 20000
  )
    throw Error("Invalid scene recovery data.");
  const nodes = new Map();
  root.traverse((node) => {
    if (node !== root && node.userData.apcEditorId)
      nodes.set(node.userData.apcEditorId, node);
  });
  const records = new Map();
  for (const item of state.objects) {
    if (
      !nodes.has(item.id) ||
      records.has(item.id) ||
      !Array.isArray(item.position) ||
      !Array.isArray(item.quaternion) ||
      !Array.isArray(item.scale) ||
      item.position.length !== 3 ||
      item.quaternion.length !== 4 ||
      item.scale.length !== 3 ||
      ![...item.position, ...item.quaternion, ...item.scale].every(
        Number.isFinite,
      )
    )
      throw Error("Recovery does not match the model.");
    records.set(item.id, item);
  }
  // Validate the hierarchy before changing any objects.
  for (const item of state.objects) {
    const seen = new Set([item.id]);
    let parent = item.parent;
    while (parent !== null) {
      if (seen.has(parent) || !records.has(parent))
        throw Error("Invalid recovery hierarchy.");
      seen.add(parent);
      parent = records.get(parent).parent;
    }
  }
  for (const node of nodes.values()) node.removeFromParent();
  for (const item of state.objects) {
    const node = nodes.get(item.id);
    node.name = String(item.name || "Object");
    node.position.fromArray(item.position);
    node.quaternion.fromArray(item.quaternion);
    node.scale.fromArray(item.scale);
    node.userData.apcEditor = { ...item.data };
    (item.parent === null ? root : nodes.get(item.parent)).add(node);
  }
}

// Collections are a UI view; classification never reparents or edits model geometry.
export function objectCategory(node) {
  const role = node.userData?.apcEditor?.type;
  if (role === "strip" || role === "panel") return "LEDs";
  if (role === "projection") return "Surfaces";
  const materials = Array.isArray(node.material) ? node.material : [node.material];
  const text = [node.name, ...materials.map(m => m?.name || "")].join(" ").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  if (node.isCamera || node.isLight || /mlha|opar|fog|volume|ostreni|meritko|referencni|postava/.test(text)) return "Helpers";
  if (/neon|metrov|dvoumetr|emission|svetlo|led[ _|]/.test(text)) return "LEDs";
  if (/difuz|diffus|projection|screen|pletiv|mesh shell/.test(text)) return "Surfaces";
  if (/stena|wall|podlaha|floor|ceiling|strop|open.room/.test(text)) return "Environment";
  return "Objects";
}
export function objectLabel(node) {
  const materials = Array.isArray(node.material) ? node.material : [node.material];
  const text = [node.name, ...materials.map(m => m?.name || "")].join(" ").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const prefix = /ceiling|strop/.test(text) ? "Ceiling" : /podlaha|floor/.test(text) ? "Floor" : /stena|wall/.test(text) ? "Wall" : "";
  return (prefix ? prefix + " · " : "") + (node.name || "Object");
}

export const EDITOR_COLORS = {
  LEDs: 0x69b6aa, Floor: 0x485565, Walls: 0x515966, Ceiling: 0x3e454f,
  Surfaces: 0x827590, Decor: 0x918378, Rigging: 0x667f8d, Objects: 0x737786,
};
export function editorStyle(node) {
  const category = objectCategory(node), materials = Array.isArray(node.material) ? node.material : [node.material];
  const text = [node.name, ...materials.map(m => m?.name || "")].join(" ").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  let kind = category;
  if (category === "Objects" || category === "Environment") {
    if (/hlava|head|draci|drap|tesak|tlam|pancir|rohovina/.test(text)) kind = "Decor";
    else if (/retez|chain|lanko|cable|kovana/.test(text)) kind = "Rigging";
    else if (/podlaha|floor/.test(text)) kind = "Floor";
    else if (/strop|ceiling/.test(text)) kind = "Ceiling";
    else if (category === "Environment") kind = "Walls";
  }
  return {kind, color: EDITOR_COLORS[kind] ?? EDITOR_COLORS.Objects};
}
