import * as T from "./editor-vendor/three.module.js";
import { OrbitControls } from "./editor-vendor/OrbitControls.js";
import { TransformControls } from "./editor-vendor/TransformControls.js";
import { GLTFLoader } from "./editor-vendor/GLTFLoader.js";
import { GLTFExporter } from "./editor-vendor/GLTFExporter.js";
import { OBJLoader } from "./editor-vendor/OBJLoader.js";
import { FBXLoader } from "./editor-vendor/FBXLoader.js";
import {
  validateObject,
  effective,
  COMPOSITION,
  advanceFrame,
  centerPivot,
  dimensions,
  resizeDimension,
  duplicateRow,
  sceneState,
  restoreSceneState,
  objectCategory,
  objectLabel,
  editorStyle,
  EDITOR_COLORS,
} from "./editor-model.js";
const $ = (id) => document.getElementById(id),
  viewport = $("viewport");
const scene = new T.Scene(), helperScene = new T.Scene();
scene.background = new T.Color("#10141b");
const renderer = new T.WebGLRenderer({
  antialias: true,
  powerPreference: "low-power",
});
renderer.setPixelRatio(Math.min(devicePixelRatio, 1));
viewport.prepend(renderer.domElement);
const ownedNodes = new Set();
const root = new T.Group();
root.name = "Space";
scene.add(root);
const solidMaterials = new Map(), solidRecords = [], ledGuides = new Map(), guideGeometry = new Map();
const ledGuideMaterial = new T.LineBasicMaterial({color: 0x78c8bb, transparent: true, opacity: .22, depthTest: false, depthWrite: false});
function dropGuide(node) {
  const guide = ledGuides.get(node); if (!guide) return;
  helperScene.remove(guide.line);
  if (guide.source) { const cached = guideGeometry.get(guide.source); if (--cached.refs === 0) { cached.edges.dispose(); guideGeometry.delete(guide.source); } }
  else { guide.line.geometry.dispose(); guide.line.material.dispose(); }
  ledGuides.delete(node);
}
function syncEditorStyles() {
  const alive = new Set(), counted = new Set(); let budget = 0;
  solidRecords.length = 0;
  root.traverse(node => {
    if (!node.isMesh) return;
    const style = editorStyle(node);
    if (!solidMaterials.has(style.color)) solidMaterials.set(style.color, new T.MeshStandardMaterial({color: style.color, roughness: .85, metalness: 0, side: T.DoubleSide}));
    solidRecords.push({node, material: solidMaterials.get(style.color), original: null});
    if (objectCategory(node) !== "LEDs") return;
    alive.add(node); const geometry = node.geometry, count = geometry.getAttribute("position")?.count || 0;
    const existing = ledGuides.get(node); if (existing && existing.geometry !== geometry) dropGuide(node);
    let precise = count <= 20000 && (counted.has(geometry) || budget + count <= 200000);
    if (!counted.has(geometry)) { counted.add(geometry); budget += count; }
    if (!ledGuides.has(node)) {
      let line;
      if (precise) {
        if (!guideGeometry.has(geometry)) guideGeometry.set(geometry, {edges: new T.EdgesGeometry(geometry, 20), refs: 0});
        const cached = guideGeometry.get(geometry); cached.refs++; line = new T.LineSegments(cached.edges, ledGuideMaterial); line.matrixAutoUpdate = false;
      } else {
        // shortcut: very dense LED meshes use bounds; use simplified topology for a detailed contour.
        line = new T.BoxHelper(node, 0x78c8bb); line.material.transparent = true; line.material.opacity = .25; line.material.depthTest = false;
      }
      line.renderOrder = 100; helperScene.add(line); ledGuides.set(node, {line, geometry, source: precise ? geometry : null});
    }
  });
  for (const node of ledGuides.keys()) if (!alive.has(node)) dropGuide(node);
}
function updateLedGuides() {
  root.updateWorldMatrix(true, true);
  for (const [node, guide] of ledGuides) {
    guide.line.visible = !preview && $("ledOutlines").checked && effective(node, "editorVisible");
    if (!guide.line.visible) continue;
    if (guide.source) guide.line.matrix.copy(node.matrixWorld); else guide.line.setFromObject(node);
  }
}
function renderEditorScene() {
  const solid = !preview && $("shading").value === "solid";
  if (solid) for (const record of solidRecords) { record.original = record.node.material; record.node.material = record.material; }
  try { renderer.render(scene, camera); }
  finally { if (solid) for (const record of solidRecords) { record.node.material = record.original; record.original = null; } }
}
const selectionBox = new T.BoxHelper(undefined, 0xff920a);
selectionBox.material.depthTest = false; selectionBox.material.transparent = true; selectionBox.renderOrder = 10000; selectionBox.visible = false;
helperScene.add(selectionBox);
let selectionEdges = null;
function updateSelectionOutline() {
  selectionBox.visible = !!selected && !preview && effective(selected, "editorVisible");
  if (selectionBox.visible) { selected.updateWorldMatrix(true, true); selectionBox.setFromObject(selected); }
  if (selectionEdges) { selectionEdges.visible = selectionBox.visible; selectionEdges.matrix.copy(selected.matrixWorld); }
}

const grid = new T.GridHelper(20, 40, 0x52677f, 0x283443);
helperScene.add(grid);
scene.add(new T.HemisphereLight(0xe2efff, 0x68717c, 2));
const key = new T.DirectionalLight(0xffffff, 2);
key.position.set(4, 8, 5);
scene.add(key);
const perspective = new T.PerspectiveCamera(45, 1, 0.01, 2000),
  ortho = new T.OrthographicCamera(-6, 6, 6, -6, 0.01, 2000);
let camera = perspective;
camera.position.set(6, 4, 8);
let orbit, transform;
const target = new T.Vector3();
let selected = null,
  preview = false,
  dirty = false,
  renderNeeded = true;
let history = [],
  future = [],
  transaction = null,
  viewName = "Perspective",
  fixtures = [];
const video = document.createElement("video");
video.muted = true;
video.playsInline = true;
const black = document.createElement("canvas");
black.width = black.height = 2;
const blackContext = black.getContext("2d");
blackContext.fillStyle = "#000";
blackContext.fillRect(0, 0, 2, 2);
const videoTexture = new T.VideoTexture(video),
  blackTexture = new T.CanvasTexture(black),
  sourceUniform = { value: blackTexture };
let videoFileUrl = null;
video.loop = true;
let media = null,
  testPattern = false;
const previewMaterials = new Map();
let lastFrame = 0;
let restoring = false,
  ready = false,
  draftTimer = null,
  draftBusy = false,
  draftTopology = "",
  viewTimer = null,
  sourceMode = "black";
const stateKey =
  "apc40-view:" +
  (new URLSearchParams(location.search).get("space") || "default");
function storeView() {
  if (restoring || !ready) return;
  clearTimeout(viewTimer);
  viewTimer = setTimeout(() => {
    try {
      sessionStorage.setItem(
        stateKey,
        JSON.stringify({
          pos: camera.position.toArray(),
          target: orbit.target.toArray(),
          view: viewName.toLowerCase(),
          span: camera.isOrthographicCamera
            ? [
                camera.left,
                camera.right,
                camera.top,
                camera.bottom,
                camera.zoom,
              ]
            : null,
          snap: $("snapEnabled").checked,
          step: Number($("snapStep").value),
          up: camera.up.toArray(),
          selected: selected?.userData.apcEditorId,
          mode: sourceMode,
          time: Number.isFinite(video.currentTime) ? video.currentTime : 0,
        }),
      );
    } catch {}
  }, 100);
}
function topology() {
  const ids = [];
  root.traverse((n) => {
    if (n !== root)
      ids.push(
        (n.userData.apcEditorId || n.uuid) + ":" + (n.geometry?.uuid || ""),
      );
  });
  return ids.join("|");
}
let draftPromise = null;
function saveDraft() {
  if (!draftPromise)
    draftPromise = performDraft().finally(() => (draftPromise = null));
  return draftPromise;
}
async function performDraft() {
  if (restoring || !ready || draftBusy || preview) return;
  draftBusy = true;
  const signature = topology();
  try {
    if (signature !== draftTopology) {
      const base = await exportGLB();
      if (signature !== topology()) return;
      await window.apcLocalStore("recovery-base", base);
      draftTopology = signature;
    }
    await window.apcLocalStore("recovery-state", sceneState(root));
    $("recoveryStatus").textContent = "Recovery saved locally";
  } catch (error) {
    $("recoveryStatus").textContent =
      "Recovery unavailable — use Save project: " + error.message;
  } finally {
    draftBusy = false;
    if (signature !== topology()) queueDraft();
  }
}
function queueDraft() {
  if (!ready || restoring) return;
  clearTimeout(draftTimer);
  draftTimer = setTimeout(saveDraft, 1800);
  $("recoveryStatus").textContent = "Saving local recovery…";
}

function message(text) {
  $("message").textContent = text;
}
function pruneResources() {
  const keep = new Set();
  root.traverse((node) => keep.add(node));
  for (const state of [...history, ...future])
    for (const record of state) keep.add(record.node);
  const retained = new Set(),
    unused = new Set();
  for (const node of ownedNodes) {
    const resources = keep.has(node) ? retained : unused;
    if (node.geometry) resources.add(node.geometry);
    for (const material of node.material
      ? Array.isArray(node.material)
        ? node.material
        : [node.material]
      : []) {
      resources.add(material);
      for (const value of Object.values(material))
        if (value?.isTexture) resources.add(value);
    }
  }
  for (const resource of unused)
    if (
      !retained.has(resource) &&
      resource !== videoTexture &&
      resource !== blackTexture
    )
      resource.dispose();
  for (const node of ownedNodes) if (!keep.has(node)) ownedNodes.delete(node);
}
function changed() {
  pruneResources();
  syncEditorStyles();
  dirty = true;
  queueDraft();
  storeView();
  renderNeeded = true;
  $("status").textContent =
    "Unsaved changes · save a GLB project to keep your work";
}
function meta(node) {
  node.userData.apcEditorId ||= node.uuid;
  if (node.isMesh || node.isLine) ownedNodes.add(node);
  const defaults = {
    type: "room",
    editorVisible: node.visible,
    active: true,
    source: "composition",
    pixels: 32,
    rows: 1,
  };
  let data = node.userData.apcEditor;
  if (!data || typeof data !== "object" || Array.isArray(data)) data = defaults;
  try {
    validateObject(data);
  } catch {
    data = defaults;
  }
  node.userData.apcEditor = data;
  return data;
}

function snapshot() {
  const records = [];
  root.traverse((node) => {
    if (node === root) return;
    records.push({
      node,
      parent: node.parent,
      position: node.position.toArray(),
      rotation: node.rotation.toArray(),
      scale: node.scale.toArray(),
      name: node.name,
      data: { ...meta(node) },
    });
  });
  return records;
}
function remember() {
  history.push(snapshot());
  if (history.length > 30) history.shift();
  future = [];
}
function restore(records) {
  select(null);
  clearPreviewMaterials();
  const current = [];
  root.traverse((node) => {
    if (node !== root) current.push(node);
  });
  for (const node of current) node.removeFromParent();
  for (const record of records) {
    const node = record.node;
    node.position.fromArray(record.position);
    node.rotation.fromArray(record.rotation);
    node.scale.fromArray(record.scale);
    node.name = record.name;
    node.userData.apcEditor = { ...record.data };
    record.parent.add(node);
  }
  refresh();
  changed();
}
function setupControls() {
  orbit?.dispose();
  if (transform) {
    transform.detach();
    helperScene.remove(transform);
    transform.dispose();
  }
  orbit = new OrbitControls(camera, renderer.domElement);
  orbit.target.copy(target);
  orbit.enableDamping = false;
  orbit.mouseButtons = {
    LEFT: null,
    MIDDLE: T.MOUSE.ROTATE,
    RIGHT: T.MOUSE.PAN,
  };
  orbit.addEventListener("change", () => {
    target.copy(orbit.target);
    storeView();
    renderNeeded = true;
  });
  transform = new TransformControls(camera, renderer.domElement);
  transform.setSpace("local");
  applySnaps();
  helperScene.add(transform);
  transform.addEventListener(
    "dragging-changed",
    (e) => (orbit.enabled = !e.value),
  );
  transform.addEventListener("mouseDown", () => (transaction = snapshot()));
  transform.addEventListener("mouseUp", () => {
    if (transaction) {
      history.push(transaction);
      if (history.length > 30) history.shift();
      future = [];
      transaction = null;
      changed();
      fillProperties();
    }
  });
  transform.addEventListener("change", () => (renderNeeded = true));
  if (selected && !preview) transform.attach(selected);
}
setupControls();
function resize() {
  const w = viewport.clientWidth,
    h = viewport.clientHeight;
  renderer.setSize(w, h);
  perspective.aspect = w / h;
  perspective.updateProjectionMatrix();
  const span = (ortho.top - ortho.bottom) / 2 / ortho.zoom;
  ortho.left = (-span * w) / h;
  ortho.right = (span * w) / h;
  ortho.top = span;
  ortho.bottom = -span;
  ortho.zoom = 1;
  ortho.updateProjectionMatrix();
  renderNeeded = true;
}
new ResizeObserver(resize).observe(viewport);
function setView(name) {
  const distance = Math.max(3, camera.position.distanceTo(target));
  const directions = {
    front: [0, 0, 1],
    back: [0, 0, -1],
    left: [-1, 0, 0],
    right: [1, 0, 0],
    top: [0, 1, 0],
    bottom: [0, -1, 0],
  };
  camera = name === "perspective" ? perspective : ortho;
  camera.up.set(0, 1, 0);
  if (name === "top") camera.up.set(0, 0, -1);
  if (name === "bottom") camera.up.set(0, 0, 1);
  camera.position
    .copy(target)
    .add(
      new T.Vector3(...(directions[name] || [0.7, 0.5, 1]))
        .normalize()
        .multiplyScalar(distance),
    );
  camera.lookAt(target);
  viewName = name[0].toUpperCase() + name.slice(1);
  $("viewLabel").textContent = viewName + " · meters";
  grid.rotation.set(0, 0, 0);
  if (name === "front" || name === "back") grid.rotation.x = Math.PI / 2;
  if (name === "left" || name === "right") grid.rotation.z = Math.PI / 2;
  setupControls();
  resize();
}
document
  .querySelectorAll("[data-view]")
  .forEach((b) => (b.onclick = () => setView(b.dataset.view)));
document.querySelectorAll("[data-tool]").forEach(
  (button) =>
    (button.onclick = () => {
      transform.setMode(button.dataset.tool);
      document
        .querySelectorAll("[data-tool]")
        .forEach((item) =>
          item.setAttribute("aria-pressed", String(item === button)),
        );
    }),
);
function frame() {
  const box = new T.Box3().setFromObject(selected || root);
  if (box.isEmpty()) return;
  box.getCenter(target);
  const radius = Math.max(0.2, box.getSize(new T.Vector3()).length() / 2);
  const direction = camera.position.clone().sub(orbit.target).normalize();
  camera.position.copy(target).addScaledVector(direction, radius * 3);
  ortho.top = radius * 1.4;
  ortho.bottom = -ortho.top;
  ortho.left = (-ortho.top * viewport.clientWidth) / viewport.clientHeight;
  ortho.right = -ortho.left;
  ortho.zoom = 1;
  ortho.updateProjectionMatrix();
  orbit.target.copy(target);
  orbit.update();
  renderNeeded = true;
}
$("frame").onclick = frame;
function select(node) {
  if (selectionEdges) { helperScene.remove(selectionEdges); selectionEdges.geometry.dispose(); selectionEdges.material.dispose(); selectionEdges = null; }
  selected = node;
  if (node?.isMesh && node.geometry.getAttribute("position").count <= 20000) {
    selectionEdges = new T.LineSegments(new T.EdgesGeometry(node.geometry, 30), new T.LineBasicMaterial({ color: 0xff920a, depthTest: false, transparent: true }));
    selectionEdges.matrixAutoUpdate = false; selectionEdges.renderOrder = 10001; helperScene.add(selectionEdges);
  }
  $("selectionBadge").textContent = node ? "Selected: " + objectLabel(node) : "No object selected";
  updateSelectionOutline();
  transform.detach();
  if (node && !preview) transform.attach(node);
  fillProperties();
  renderTree();
  drawSliceMap();
  storeView();
  renderNeeded = true;
}
const collectionStateKey = "apc40-tree-folds:" + (new URLSearchParams(location.search).get("space") || "default");
let collectionState = {Environment:true, LEDs:true, Surfaces:true};
try { const saved=JSON.parse(localStorage.getItem(collectionStateKey)||"null");if(saved&&typeof saved==="object")for(const key of ["Environment","LEDs","Surfaces","Objects","Helpers"])if(typeof saved[key]==="boolean")collectionState[key]=saved[key]; } catch {}
function selectable(node) {
  return effective(node, "editorVisible") &&
    ($("showHelpers").checked || objectCategory(node) !== "Helpers") &&
    ($("selectionScope").value === "All" || objectCategory(node) === $("selectionScope").value);
}
function renderTree() {
  const tree = $("tree"), categories = ["Environment", "LEDs", "Surfaces", "Objects", "Helpers"], nodes = [];
  const query = $("treeSearch").value.trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  root.traverse(node => { if (node !== root && (node.isMesh || node.userData.apcPivot || node.parent === root)) nodes.push(node); });
  tree.replaceChildren();
  for (const category of categories) {
    if ($("selectionScope").value !== "All" && $("selectionScope").value !== category) continue;
    const members = nodes.filter(node => objectCategory(node) === category);
    const visible = members.filter(node => !query || (objectLabel(node) + " " + category + " " + (Array.isArray(node.material) ? node.material : [node.material]).map(m => m?.name || "").join(" ")).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().includes(query));
    if (!visible.length) continue;
    const section = document.createElement("details"), summary = document.createElement("summary");
    section.className = "collection"; section.open = collectionState[category] === true;
    summary.textContent = category + " · " + members.length;
    const hide = document.createElement("button"); hide.textContent = "Eye"; hide.title = "Show / hide " + category;
    hide.style.cssText = "float:right;padding:0 5px;font-size:11px";
    hide.onclick = event => { event.preventDefault(); event.stopPropagation(); remember(); const show = !members.some(n => effective(n,"editorVisible")); for (const n of members) meta(n).editorVisible = show; refresh(); changed(); };
    summary.append(hide); section.append(summary);
    summary.onclick = event => { if(event.target.closest("button,input,select"))return;event.preventDefault();section.open=!section.open;collectionState[category]=section.open;try{localStorage.setItem(collectionStateKey,JSON.stringify(collectionState));}catch{} };
    for (const node of visible) {
      const data = meta(node), row = document.createElement("div");
      row.className = "tree-row" + (selected === node ? " selected" : ""); row.setAttribute("role","treeitem"); row.setAttribute("aria-selected",String(selected === node));
      const label = document.createElement("button"); label.textContent = objectLabel(node); label.title = node.name || "Object"; label.onclick = () => select(node); row.append(label);
      for (const [property, symbol, title] of [["editorVisible","◉","Visible in editor"],["active","⏻","Include in preview"]]) {
        const button = document.createElement("button"); button.textContent = symbol; button.title = title;
        button.setAttribute("aria-label", title + " — " + label.textContent); button.setAttribute("aria-pressed", String(data[property] !== false));
        button.onclick = () => { remember(); data[property] = data[property] === false; refresh(); changed(); }; row.append(button);
      }
      section.append(row);
    }
    tree.append(section);
  }
}
$("treeSearch").oninput = renderTree;
$("ledOutlines").onchange = () => { renderNeeded = true; };
for (const [name,color] of Object.entries(EDITOR_COLORS)) {
  const label = document.createElement("span"), swatch = document.createElement("i");
  swatch.style.background = "#" + color.toString(16).padStart(6,"0"); label.append(swatch, name); $("editorLegend").append(label);
}
$("selectionScope").onchange = () => { if (selected && !selectable(selected)) select(null); renderTree(); };
$("showHelpers").onchange = () => { refresh(); if (selected && !selectable(selected)) select(null); };
$("shading").onchange = () => { $("editorLegend").hidden = preview || $("shading").value !== "solid"; renderNeeded = true; };
for (const property of ["position", "rotation", "scale"]) {
  const label = document.createElement("label");
  label.textContent =
    property === "rotation"
      ? "Rotation · degrees"
      : property === "position"
        ? "Position · meters"
        : "Scale";
  $("transforms").append(label);
  const group = document.createElement("div");
  group.className = "xyz";
  for (const axis of ["x", "y", "z"]) {
    const l = document.createElement("label");
    l.textContent = axis.toUpperCase();
    const input = document.createElement("input");
    input.type = "number";
    input.step = property === "rotation" ? "1" : ".1";
    input.id = property + "-" + axis;
    input.onchange = () => {
      if (!selected) return;
      const value = Number(input.value);
      if (
        !Number.isFinite(value) ||
        Math.abs(value) > 100000 ||
        (property === "scale" && Math.abs(value) < 0.0001)
      ) {
        fillProperties();
        return;
      }
      remember();
      selected[property][axis] =
        property === "rotation" ? T.MathUtils.degToRad(value) : value;
      changed();
    };
    l.append(input);
    group.append(l);
  }
  $("transforms").append(group);
}
for (const axis of ["x", "y", "z"]) {
  const label = document.createElement("label");
  label.textContent = axis.toUpperCase();
  const input = document.createElement("input");
  input.id = "dimension-" + axis;
  input.type = "number";
  input.min = ".001";
  input.step = ".1";
  input.setAttribute(
    "aria-label",
    "Dimension " + axis.toUpperCase() + " meters",
  );
  input.onchange = () => {
    if (!selected || preview) return;
    try {
      remember();
      resizeDimension(selected, axis, Number(input.value), T);
      fillProperties();
      changed();
    } catch (error) {
      message(error.message);
      fillProperties();
    }
  };
  label.append(input);
  $("dimensions").append(label);
}
$("makeRow").onclick = () => {
  if (!selected || preview) return;
  try {
    remember();
    const copies = duplicateRow(
      selected,
      $("rowAxis").value,
      Number($("rowCount").value),
      Number($("rowSpacing").value),
      T,
    );
    select(copies[copies.length - 1]);
    refresh();
    changed();
  } catch (error) {
    message(error.message);
  }
};
function fillProperties() {
  $("empty").hidden = !!selected;
  $("fields").hidden = !selected;
  if (!selected) return;
  const size = dimensions(selected, T);
  for (const axis of ["x", "y", "z"]) {
    const field = $("dimension-" + axis);
    field.value = size[axis].toFixed(3);
    field.disabled = preview || size[axis] < 1e-8;
  }
  const data = meta(selected);
  $("name").value = selected.name;
  $("kind").value = data.type;
  $("kind").disabled = !selected.isMesh;
  $("visible").checked = data.editorVisible !== false;
  $("active").checked = data.active !== false;
  $("source").value = data.source || "composition";
  $("pixels").value = data.pixels;
  $("rows").value = data.rows;
  for (const property of ["position", "rotation", "scale"])
    for (const axis of ["x", "y", "z"])
      $(property + "-" + axis).value = (
        property === "rotation"
          ? T.MathUtils.radToDeg(selected[property][axis])
          : selected[property][axis]
      ).toFixed(3);
}
$("name").onchange = () => {
  if (selected) {
    remember();
    selected.name = $("name").value.trim() || "Object";
    renderTree();
    changed();
  }
};
for (const [id, key] of [
  ["visible", "editorVisible"],
  ["active", "active"],
  ["kind", "type"],
  ["source", "source"],
  ["pixels", "pixels"],
  ["rows", "rows"],
])
  $(id).onchange = () => {
    if (!selected) return;
    try {
      const before = { ...meta(selected) },
        value = ["visible", "active"].includes(id)
          ? $(id).checked
          : ["pixels", "rows"].includes(id)
            ? Number($(id).value)
            : $(id).value;
      if (
        id === "kind" &&
        value !== "room" &&
        !selected.geometry?.getAttribute("uv")
      )
        throw Error(
          "This mesh has no UV coordinates. Add a new projection surface or panel instead.",
        );
      validateObject({ ...before, [key]: value });
      remember();
      meta(selected)[key] = value;
      refresh();
      drawSliceMap();
      changed();
    } catch (error) {
      message(error.message);
      fillProperties();
    }
  };
function refresh() {
  root.traverse((node) => {
    node.visible =
      effective(node, preview ? "active" : "editorVisible") &&
      ($("showHelpers").checked || objectCategory(node) !== "Helpers") &&
      !(
        preview &&
        node.isMesh &&
        meta(node).type !== "room" &&
        !sourceQuad(meta(node).source)
      );
  });
  syncEditorStyles();
  renderTree();
  fillProperties();
  renderNeeded = true;
}
function add(type) {
  remember();
  const object = new T.Mesh(
    type === "room"
      ? new T.BoxGeometry(1, 1, 1)
      : new T.PlaneGeometry(
          type === "strip" ? 2 : 2,
          type === "strip" ? 0.03 : 1.125,
        ),
    new T.MeshStandardMaterial({
      color: type === "room" ? 0x66788b : 0x72d9bc,
      side: T.DoubleSide,
      roughness: 0.8,
    }),
  );
  object.name = {
    room: "Box",
    projection: "Projection surface",
    panel: "LED panel",
    strip: "LED strip",
  }[type];
  object.userData.apcEditor = {
    type,
    active: true,
    editorVisible: true,
    source: "composition",
    pixels: type === "panel" ? 32 : type === "strip" ? 60 : 1,
    rows: type === "panel" ? 18 : 1,
  };
  object.position.copy(target);
  root.add(object);
  select(object);
  changed();
}
$("addRoom").onclick = () => add("room");
$("addProjection").onclick = () => add("projection");
$("addPanel").onclick = () => add("panel");
$("addStrip").onclick = () => add("strip");
$("centerPivot").onclick = () => {
  if (!selected || preview) return;
  try {
    remember();
    select(centerPivot(selected, T));
    refresh();
    changed();
  } catch (error) {
    message(error.message);
  }
};
$("duplicate").onclick = () => {
  if (!selected) return;
  remember();
  const copy = selected.clone(true);
  copy.traverse((n) => {
    n.userData.apcEditorId = n.uuid;
    if (n.geometry) n.geometry = n.geometry.clone();
    if (n.material)
      n.material = Array.isArray(n.material)
        ? n.material.map((m) => m.clone())
        : n.material.clone();
  });
  copy.name += " copy";
  copy.position.x += 0.3;
  selected.parent.add(copy);
  select(copy);
  changed();
};
$("delete").onclick = () => {
  if (!selected) return;
  remember();
  const old = selected;
  select(null);
  old.removeFromParent();
  renderTree();
  changed();
};
$("undo").onclick = () => {
  if (!history.length) return;
  future.push(snapshot());
  restore(history.pop());
};
$("redo").onclick = () => {
  if (!future.length) return;
  history.push(snapshot());
  restore(future.pop());
};
function applySnaps() {
  const enabled = $("snapEnabled").checked,
    step = Number($("snapStep").value);
  if (!Number.isFinite(step) || step < 0.001 || step > 100) return;
  transform.setTranslationSnap(enabled ? step : null);
  transform.setRotationSnap(enabled ? Math.PI / 12 : null);
  transform.setScaleSnap(enabled ? 0.1 : null);
  storeView();
}
$("snapEnabled").onchange = applySnaps;
$("snapStep").onchange = applySnaps;
function drawSliceMap() {
  const canvas = $("sliceMap"),
    ctx = canvas.getContext("2d"),
    w = canvas.width,
    h = canvas.height,
    source = selected?.userData.apcEditor?.source;
  ctx.fillStyle = "#080c12";
  ctx.fillRect(0, 0, w, h);
  for (const item of fixtures) {
    if (item.uv?.length !== 4) continue;
    ctx.strokeStyle = item.sliceUid === source ? "#74e6c1" : "#8194ac";
    ctx.lineWidth = item.sliceUid === source ? 3 : 1;
    ctx.beginPath();
    item.uv.forEach(([u, v], i) =>
      i ? ctx.lineTo(u * w, (1 - v) * h) : ctx.moveTo(u * w, (1 - v) * h),
    );
    ctx.closePath();
    ctx.stroke();
  }
  if (
    source &&
    source !== "composition" &&
    !fixtures.some((f) => f.sliceUid === source)
  )
    message("Missing source slice — choose a replacement.");
}
$("sliceMap").onclick = (event) => {
  const box = $("sliceMap").getBoundingClientRect(),
    u = (event.clientX - box.left) / box.width,
    v = 1 - (event.clientY - box.top) / box.height;
  const hit = [...fixtures].reverse().find((item) => {
    let inside = false;
    const p = item.uv || [];
    for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
      if (
        p[i][1] > v !== p[j][1] > v &&
        u <
          ((p[j][0] - p[i][0]) * (v - p[i][1])) / (p[j][1] - p[i][1]) + p[i][0]
      )
        inside = !inside;
    }
    return inside;
  });
  if (!hit) return;
  const objects = [];
  root.traverse((n) => {
    if (n.userData.apcEditor?.source === hit.sliceUid) objects.push(n);
  });
  if (objects.length) select(objects[0]);
  message(
    (hit.screen || "Output") +
      " / " +
      (hit.slice || hit.sliceUid) +
      " · " +
      objects.length +
      " assigned objects" +
      (objects.length ? "" : " — assign via Video source slice"),
  );
};
function sourceQuad(id) {
  if (!id || id === "composition") return COMPOSITION;
  const fixture = fixtures.find((f) => f.sliceUid === id);
  return fixture?.uv || null;
}
function clearPreviewMaterials() {
  for (const [node, old] of previewMaterials) {
    node.material.dispose();
    node.material = old;
  }
  previewMaterials.clear();
}
function setPreview(value) {
  clearPreviewMaterials();
  preview = value;
  $("editorLegend").hidden = preview || $("shading").value !== "solid";
  updateSelectionOutline();
  transform.detach();
  grid.visible = !preview;
  $("views").hidden = preview;
  $("previewBadge").hidden = !preview;
  $("mode").textContent = preview ? "Edit scene" : "Scene preview";
  for (const id of [
    "import",
    "addRoom",
    "addProjection",
    "addPanel",
    "addStrip",
    "undo",
    "redo",
    "duplicate",
    "delete",
  ])
    $(id).disabled = preview;
  $("fields").inert = preview;
  if (preview) {
    root.traverse((node) => {
      const data = meta(node);
      if (!node.isMesh || data.type === "room") return;
      const quad = sourceQuad(data.source);
      if (!quad) {
        message(
          "A saved source slice is missing. Choose a replacement in Edit scene.",
        );
        return;
      }
      const uniforms = {
        map: sourceUniform,
        columns: { value: data.type === "projection" ? 0 : data.pixels },
        rows: { value: data.rows },
      };
      quad.forEach(
        (v, i) => (uniforms["q" + i] = { value: new T.Vector2(...v) }),
      );
      previewMaterials.set(node, node.material);
      node.material = new T.ShaderMaterial({
        side: T.DoubleSide,
        uniforms,
        vertexShader:
          "varying vec2 v;void main(){v=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}",
        fragmentShader:
          "uniform sampler2D map;uniform vec2 q0,q1,q2,q3;uniform float columns,rows;varying vec2 v;void main(){vec2 p=vec2(v.x,1.-v.y);if(columns>0.){vec2 count=vec2(columns,rows);vec2 cell=fract(p*count);if(any(lessThan(cell,vec2(.08)))||any(greaterThan(cell,vec2(.92))))discard;p=(floor(p*count)+.5)/count;}vec2 uv=mix(mix(q0,q1,p.x),mix(q3,q2,p.x),p.y);gl_FragColor=texture2D(map,uv);}",
        toneMapped: false,
      });
    });
  } else if (selected) transform.attach(selected);
  refresh();
}
$("mode").onclick = async () => {
  if (!preview) await saveDraft();
  setPreview(!preview);
};
const manager = new T.LoadingManager();
manager.setURLModifier((url) => {
  if (
    /^(data:|blob:)/.test(url) ||
    url.startsWith(
      location.origin +
        location.pathname.slice(0, location.pathname.lastIndexOf("/") + 1),
    ) ||
    (!/^[a-z]+:|^\//i.test(url) && !url.split("/").includes(".."))
  )
    return url;
  throw Error(
    "External model resources are blocked. Use a GLB with embedded textures.",
  );
});
const loader = new GLTFLoader(manager);
async function parseGLB(data) {
  if (new DataView(data).getUint32(0, true) !== 0x46546c67)
    throw Error("Not a GLB file.");
  const gltf = await loader.parseAsync(data, "");
  return gltf.scene;
}
async function loadFile(file, consent = false) {
  if (file.size > 256 * 1024 * 1024)
    throw Error("Choose a model under 256 MiB.");
  const ext = file.name.split(".").pop().toLowerCase();
  if (ext === "blend" && !consent) {
    pendingBlend = file;
    $("blenderHelp").showModal();
    return;
  }
  message("Importing " + file.name + "…");
  let object;
  if (ext === "glb") object = await parseGLB(await file.arrayBuffer());
  else if (ext === "obj")
    object = new OBJLoader(manager).parse(await file.text());
  else if (ext === "fbx")
    object = new FBXLoader(manager).parse(await file.arrayBuffer(), "");
  else if (ext === "blend") {
    const reply = await fetch("convert-model", {
      method: "POST",
      headers: {
        "X-Model-Extension": ".blend",
        "X-Conversion-Consent": "yes",
        "Content-Type": "application/octet-stream",
      },
      body: file,
    });
    if (!reply.ok)
      throw Error(
        "Converter unavailable. Reopen Space Studio from the updated Bridge app.",
      );
    if (reply.headers.get("Content-Type").includes("json"))
      throw Error((await reply.json()).error);
    object = await parseGLB(await reply.arrayBuffer());
  } else throw Error("Supported models: GLB, OBJ, FBX and optional BLEND.");
  remember();
  let project = false;
  object.traverse((node) => {
    if (node.userData.apcProject?.version === 1) project = true;
  });
  if (project) {
    select(null);
    root.clear();
  }
  object.name = file.name;
  object.traverse((node) => {
    meta(node);
    if (node.isMesh) {
      for (const m of Array.isArray(node.material)
        ? node.material
        : [node.material]) {
        m.emissive?.setRGB(0, 0, 0);
        m.emissiveIntensity = 0;
      }
    }
  });
  root.add(object);
  select(object);
  refresh();
  frame();
  changed();
  message(
    "Imported locally. Save project to keep a converted GLB. OBJ/FBX sidecar textures are not imported.",
  );
}
let pendingBlend = null;
$("convertBlend").onclick = async () => {
  const file = pendingBlend;
  pendingBlend = null;
  $("blenderHelp").close();
  try {
    await loadFile(file, true);
  } catch (error) {
    message(error.message);
  }
};
$("cancelBlend").onclick = () => {
  pendingBlend = null;
  $("blenderHelp").close();
};
$("import").onclick = () => $("file").click();
$("file").onchange = async () => {
  const file = $("file").files[0];
  $("file").value = "";
  if (!file) return;
  $("import").disabled = true;
  try {
    await loadFile(file);
  } catch (error) {
    message(error.message);
  } finally {
    $("import").disabled = false;
  }
};
async function exportGLB() {
  root.userData.apcProject = {
    version: 1,
    camera: { pos: camera.position.toArray(), target: orbit.target.toArray() },
  };
  return new GLTFExporter().parseAsync(root, {
    binary: true,
    onlyVisible: false,
    includeCustomExtensions: false,
  });
}
$("apply").onclick = async (event) => {
  const returnToMapping = event?.currentTarget?.id === "outputMapping";
  const button = $("apply");
  button.disabled = true;
  const wasPreview = preview;
  if (wasPreview) setPreview(false);
  try {
    await saveDraft();
    const glb = await exportGLB();
    await window.apcProjectStore(glb);
    await window.apcLocalStore("recovery-base", glb);
    await window.apcLocalStore("recovery-state", sceneState(root));
    clearTimeout(draftTimer);
    clearTimeout(viewTimer);
    try {
      sessionStorage.setItem(
        stateKey,
        JSON.stringify({
          pos: camera.position.toArray(),
          target: orbit.target.toArray(),
          view: viewName.toLowerCase(),
          span: camera.isOrthographicCamera
            ? [
                camera.left,
                camera.right,
                camera.top,
                camera.bottom,
                camera.zoom,
              ]
            : null,
          snap: $("snapEnabled").checked,
          step: Number($("snapStep").value),
          up: camera.up.toArray(),
          selected: selected?.userData.apcEditorId,
          mode: sourceMode,
          time: video.currentTime || 0,
        }),
      );
    } catch {}
    dirty = false;
    location.href = "preview.html" + location.search + (returnToMapping ? "#mapping" : "");
  } catch (error) {
    message(
      "Could not store project locally: " +
        error.message +
        " Save GLB instead.",
    );
    if (wasPreview) setPreview(true);
    button.disabled = false;
  }
};
$("save").onclick = async () => {
  const button = $("save");
  button.disabled = true;
  const wasPreview = preview;
  if (wasPreview) setPreview(false);
  try {
    const glb = await exportGLB();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(
      new Blob([glb], { type: "model/gltf-binary" }),
    );
    link.download = "APC40-space.glb";
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 5000);
    dirty = false;
    message("GLB project downloaded.");
    $("status").textContent =
      "Project exported · keep the downloaded GLB to reopen your scene";
  } catch (error) {
    message(error.message);
  } finally {
    if (wasPreview) setPreview(true);
    button.disabled = false;
  }
};
async function openVideoFile(file) {
  stopMedia();
  const url = URL.createObjectURL(file);
  videoFileUrl = url;
  sourceMode = "file";
  video.src = url;
  try {
    await video.play();
    if (videoFileUrl !== url) return;
    sourceUniform.value = videoTexture;
    renderNeeded = true;
    if (!restoring)
      window
        .apcLocalStore("video", file.size <= 128 * 1024 * 1024 ? file : null)
        .catch(() =>
          message("Video works, but cannot be kept for the next view."),
        );
    storeView();
    message("Local video loop connected. No upload; audio is muted.");
  } catch (error) {
    if (videoFileUrl !== url) return;
    stopMedia();
    message(
      "This video cannot play in the browser. Use H.264 MP4 or WebM; DXV needs conversion first.",
    );
  }
}
function stopMedia() {
  media?.getTracks().forEach((track) => track.stop());
  media = null;
  video.pause();
  video.srcObject = null;
  video.removeAttribute("src");
  video.load();
  if (videoFileUrl) URL.revokeObjectURL(videoFileUrl);
  videoFileUrl = null;
  blackContext.fillStyle = "#000";
  blackContext.fillRect(0, 0, black.width, black.height);
  blackTexture.needsUpdate = true;
  testPattern = false;
  sourceMode = "black";
  sourceUniform.value = blackTexture;
  renderNeeded = true;
}
async function startMedia(screen) {
  try {
    stopMedia();
    const id = $("cameraChoice").value;
    media = await (screen
      ? navigator.mediaDevices.getDisplayMedia({
          video: { frameRate: { max: 30 } },
          audio: false,
        })
      : navigator.mediaDevices.getUserMedia({
          video: {
            ...(id ? { deviceId: { exact: id } } : {}),
            width: { ideal: 1280 },
            height: { ideal: 720 },
            frameRate: { ideal: 24, max: 30 },
          },
          audio: false,
        }));
    video.srcObject = media;
    await video.play();
    sourceUniform.value = videoTexture;
    sourceMode = screen ? "screen" : "camera";
    storeView();
    media.getVideoTracks()[0].addEventListener("ended", stopMedia);
    if (!screen) {
      const devices = await navigator.mediaDevices.enumerateDevices();
      $("cameraChoice").replaceChildren();
      for (const device of devices.filter((d) => d.kind === "videoinput")) {
        const option = document.createElement("option");
        option.value = device.deviceId;
        option.textContent = device.label || "Camera";
        $("cameraChoice").append(option);
      }
      const used = media.getVideoTracks()[0].getSettings().deviceId;
      if (used) $("cameraChoice").value = used;
    }
    message("Live input connected. Stop releases the camera/capture.");
  } catch (error) {
    stopMedia();
    message(error.message);
  }
}
$("test").onclick = () => {
  stopMedia();
  black.width = black.height = 256;
  testPattern = true;
  sourceMode = "test";
  storeView();
  sourceUniform.value = blackTexture;
  message("TEST PATTERN · generated input, not Arena output");
};
$("camera").onclick = () => startMedia(false);
$("capture").onclick = () => startMedia(true);
$("openVideo").onclick = () => $("videoFile").click();
$("videoFile").onchange = async () => {
  const file = $("videoFile").files[0];
  $("videoFile").value = "";
  if (file) await openVideoFile(file);
};
$("stop").onclick = () => {
  stopMedia();
  storeView();
};
$("back").onclick = () => $("apply").click();
$("outputMapping").onclick = $("apply").onclick;
window.addEventListener("beforeunload", (event) => {
  if (dirty) {
    event.preventDefault();
    event.returnValue = "";
  }
});
window.addEventListener("pagehide", () => {
  stopMedia();
  for (const node of [...ledGuides.keys()]) dropGuide(node);
  ledGuideMaterial.dispose(); for (const material of solidMaterials.values()) material.dispose();
  renderer.dispose();
});
renderer.domElement.addEventListener("pointerdown", (event) => {
  if (event.button !== 0 || preview || transform.axis) return;
  const bounds = renderer.domElement.getBoundingClientRect(),
    mouse = new T.Vector2(
      ((event.clientX - bounds.left) / bounds.width) * 2 - 1,
      1 - ((event.clientY - bounds.top) / bounds.height) * 2,
    ),
    ray = new T.Raycaster();
  ray.setFromCamera(mouse, camera);
  // Back faces must be pickable from inside a room; restore original material sides immediately.
  const sides = new Map();
  root.traverse(n => { for (const material of n.material ? (Array.isArray(n.material) ? n.material : [n.material]) : []) if (!sides.has(material)) { sides.set(material, material.side); material.side = T.DoubleSide; } });
  let hit;
  try { hit = ray.intersectObject(root, true).find(h => selectable(h.object)); }
  finally { for (const [material, side] of sides) material.side = side; }
  select(hit?.object || null);
});
window.addEventListener("keydown", (event) => {
  if (
    /INPUT|SELECT|TEXTAREA/.test(event.target.tagName) ||
    $("blenderHelp").open
  )
    return;
  const key = event.key.toLowerCase();
  if ((event.ctrlKey || event.metaKey) && key === "z") {
    event.preventDefault();
    $(event.shiftKey ? "redo" : "undo").click();
    return;
  }
  if (preview) return;
  if (["g", "r", "s"].includes(key) && selected)
    transform.setMode({ g: "translate", r: "rotate", s: "scale" }[key]);
  if (key === "escape" && transaction) {
    transform.reset();
    transaction = null;
  }
  if (key === "h") {
    if (event.altKey || selected) {
      remember();
      if (event.altKey) root.traverse(n => { if (n !== root && ($("selectionScope").value === "All" || objectCategory(n) === $("selectionScope").value)) meta(n).editorVisible = true; });
      else meta(selected).editorVisible = false;
      refresh(); changed();
    }
  }
  if (key === "f") frame();
  if (event.code === "Numpad1" || key === "1")
    setView(event.ctrlKey ? "back" : "front");
  if (event.code === "Numpad3" || key === "3")
    setView(event.ctrlKey ? "left" : "right");
  if (event.code === "Numpad7" || key === "7")
    setView(event.ctrlKey ? "bottom" : "top");
  if (key === "5")
    setView(camera.isOrthographicCamera ? "perspective" : "front");
  if (key === "delete") $("delete").click();
});
async function heartbeat() {
  try {
    const response = await fetch("heartbeat" + location.search);
    if (!response.ok)
      message(
        "Viewer session expired. Save your project and reopen from Bridge.",
      );
  } catch {
    message("Local viewer is unavailable. Save your project before closing.");
  }
}
setInterval(heartbeat, 20000);
heartbeat();
async function loadInitial() {
  try {
    const response = await fetch("layout" + location.search);
    if (response.ok) {
      fixtures = (await response.json()).outputFixtures || [];
    }
  } catch {}
  const option = document.createElement("option");
  option.value = "composition";
  option.textContent = "Whole composition";
  $("source").append(option);
  for (const fixture of fixtures) {
    const o = document.createElement("option");
    o.value = fixture.sliceUid;
    o.textContent = fixture.screen + " / " + fixture.slice;
    $("source").append(o);
  }
  try {
    const response = await fetch("active-layout.js" + location.search);
    const text = await response.text();
    const layout = JSON.parse(text.slice("window.APC40Layout=".length, -1));
    restoring = true;
    let recovery=null,recoveryBase=null,saved=null;
    try {
      recovery=await window.apcLocalStore('recovery-state');
      recoveryBase=recovery?await window.apcLocalStore('recovery-base'):null;
      saved=recoveryBase||await window.apcProjectStore();
    } catch(error) { $('recoveryStatus').textContent='Local recovery unavailable — use Save project'; }
    const object = saved
      ? await parseGLB(saved)
      : (await loader.loadAsync(layout.space?.model || "room-current.glb"))
          .scene;
    root.add(object);
    root.traverse((n) => meta(n));
    if (recoveryBase)
      try {
        restoreSceneState(root, recovery);
        $("recoveryStatus").textContent = "Recovered local scene";
      } catch (error) {
        message("Recovery could not apply: " + error.message);
      }
    refresh();
    frame();
    draftTopology = recoveryBase ? topology() : "";
    let view = null;
    try {
      view = JSON.parse(sessionStorage.getItem(stateKey) || "null");
    } catch {}
    if (
      view &&
      view.pos?.length === 3 &&
      view.target?.length === 3 &&
      [...view.pos, ...view.target].every(Number.isFinite)
    ) {
      setView(
        ["front", "back", "left", "right", "top", "bottom"].includes(view.view)
          ? view.view
          : "perspective",
      );
      camera.position.fromArray(view.pos);
      if (view.up?.length === 3 && view.up.every(Number.isFinite))
        camera.up.fromArray(view.up);
      orbit.target.fromArray(view.target);
      target.copy(orbit.target);
      orbit.update();
      if (
        camera.isOrthographicCamera &&
        view.span?.length === 5 &&
        view.span.every(Number.isFinite)
      ) {
        [camera.left, camera.right, camera.top, camera.bottom, camera.zoom] =
          view.span;
        camera.updateProjectionMatrix();
      }
      if (Number.isFinite(view.step) && view.step >= 0.001 && view.step <= 100)
        $("snapStep").value = view.step;
      $("snapEnabled").checked = view.snap === true;
      applySnaps();
      const nodes = [];
      root.traverse((n) => {
        if (n.userData.apcEditorId === view.selected) nodes.push(n);
      });
      if (nodes[0]) select(nodes[0]);
      if (view.mode === "file") {
        const file = await window.apcLocalStore("video");
        if (file) {
          await openVideoFile(file);
          if (Number.isFinite(view.time)) video.currentTime = view.time;
        }
      }
      if (view.mode === "test") $("test").click();
      if (view.mode === "camera" || view.mode === "screen")
        message(
          "Reconnect the previous live source using Camera or Capture screen.",
        );
    }
    restoring = false;
    ready = true;
    drawSliceMap();
    renderNeeded = true;
  } catch (error) {
    restoring = false;
    ready = true;
    message("Start an empty space or import a model. " + error.message);
  }
}
loadInitial();
let statsAt = 0,
  rendered = 0,
  sourceFrames = 0;
function animate(time) {
  requestAnimationFrame(animate);
  if (document.hidden) return;
  if (time - statsAt >= 1000) {
    const duration = (time - statsAt) / 1000,
      total = video.getVideoPlaybackQuality?.().totalVideoFrames || 0;
    $("inputInfo").textContent =
      (sourceMode === "file"
        ? "Local video"
        : sourceMode === "test"
          ? "Test pattern"
          : sourceMode === "black"
            ? "No input"
            : sourceMode) +
      " · " +
      (video.videoWidth
        ? video.videoWidth +
          "×" +
          video.videoHeight +
          " · " +
          Math.max(0, Math.round((total - sourceFrames) / duration)) +
          " source FPS · "
        : "") +
      (rendered
        ? Math.round(rendered / duration) + " render FPS"
        : "Static scene");
    sourceFrames = total;
    rendered = 0;
    statsAt = time;
  }
  const nextFrame = advanceFrame(time, lastFrame);
  if (nextFrame === null) return;
  if (testPattern) {
    const g = blackContext.createLinearGradient(0, 0, 256, 256);
    g.addColorStop(0, "hsl(" + ((time / 40) % 360) + ",90%,55%)");
    g.addColorStop(1, "#060a14");
    blackContext.fillStyle = g;
    blackContext.fillRect(0, 0, 256, 256);
    blackTexture.needsUpdate = true;
  }
  if (renderNeeded || media || testPattern || videoFileUrl) {
    updateSelectionOutline();
    updateLedGuides();
    renderEditorScene();
    if (!preview) {
      renderer.autoClear = false;
      renderer.render(helperScene, camera); renderer.autoClear = true;
    }
    rendered++;
    renderNeeded = false;
    lastFrame = nextFrame;
  }
}
requestAnimationFrame(animate);
