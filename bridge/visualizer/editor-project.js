// GLB project extras are interpreted only by the preview; Arena is never changed.
window.applyAPCEditorProject = function (root, api) {
  const records = [];
  root.traverse((node) => {
    const data = node.userData?.apcEditor;
    if (!data) return;
    let active = true;
    for (let parent = node; parent; parent = parent.parent)
      if (parent.userData?.apcEditor?.active === false) active = false;
    node.visible = active && node.userData.apcPreviewExcluded !== true;
    if (
      !node.isMesh ||
      data.type === "room" ||
      !["projection", "panel", "strip"].includes(data.type)
    )
      return;
    const fixture = (api.fixtures || []).find(
      (item) => item.sliceUid === data.source,
    );
    if (data.source && data.source !== "composition" && !fixture) {
      node.visible = false;
      console.warn("Project slice missing:", data.source);
      return;
    }
    const quad = fixture?.uv || [
      [0, 1],
      [1, 1],
      [1, 0],
      [0, 0],
    ];
    const columns = Math.max(1, Math.min(4096, Number(data.pixels) || 1)),
      rows = Math.max(
        1,
        Math.min(Math.floor(4096 / columns), Number(data.rows) || 1),
      );
    const uniforms = {
      map: api.map,
      crop: api.crop,
      columns: { value: data.type === "projection" ? 0 : columns },
      rows: { value: rows },
    };
    quad.forEach(
      (v, i) => (uniforms["q" + i] = { value: new api.Vector2(...v) }),
    );
    const original = node.material;
    node.material = new api.Material({
      uniforms,
      side: api.side,
      toneMapped: false,
      vertexShader:
        "varying vec2 v;void main(){v=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}",
      fragmentShader:
        "uniform sampler2D map;uniform vec4 crop;uniform vec2 q0,q1,q2,q3;uniform float columns,rows;varying vec2 v;void main(){vec2 p=vec2(v.x,1.-v.y);if(columns>0.){vec2 count=vec2(columns,rows);vec2 cell=fract(p*count);if(any(lessThan(cell,vec2(.08)))||any(greaterThan(cell,vec2(.92))))discard;p=(floor(p*count)+.5)/count;}vec2 uv=mix(mix(q0,q1,p.x),mix(q3,q2,p.x),p.y);gl_FragColor=texture2D(map,crop.xy+uv*crop.zw);}",
    });
    records.push({ node, original });
  });
  return records;
};

window.apcLocalStore = async function (name, value) {
  const key = new URLSearchParams(location.search).get("space") || "default";
  const storageKey = name === "project" ? key : key + ":" + name;
  return new Promise((resolve, reject) => {
    const open = indexedDB.open("apc40-space-projects", 1);
    open.onupgradeneeded = () => open.result.createObjectStore("projects");
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const db = open.result,
        tx = db.transaction(
          "projects",
          value === undefined ? "readonly" : "readwrite",
        ),
        store = tx.objectStore("projects");
      const request =
        value === undefined
          ? store.get(storageKey)
          : store.put(value, storageKey);
      let result;
      request.onsuccess = () => (result = request.result);
      tx.oncomplete = () => {
        db.close();
        resolve(result);
      };
      tx.onerror = () => {
        db.close();
        reject(tx.error);
      };
    };
  });
};

window.apcProjectStore = (value) => window.apcLocalStore("project", value);

// Optional room cut is shared by preview/editor; only runtime geometry is cloned.
window.apcOpenFront = function (root, cut, api) {
  if (!cut) return 0;
  if (!["x", "y", "z"].includes(cut.axis) || !Number.isFinite(cut.min))
    throw Error("Invalid room front cut");
  root.updateMatrixWorld(true);
  let removed = 0;
  const wall = (material) => /stena|wall/.test(
    (material?.name || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase(),
  );
  root.traverse((node) => {
    if (!node.isMesh) return;
    const geometry = node.geometry, position = geometry?.getAttribute("position");
    if (!position) return;
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    if (!materials.some(wall)) return;
    const groups = geometry.groups.length ? geometry.groups : [
      {start: 0, count: geometry.index?.count || position.count, materialIndex: 0},
    ];
    const indices = [], kept = [];
    let count = 0;
    for (const group of groups) {
      const start = indices.length;
      for (let offset = group.start; offset < group.start + group.count; offset += 3) {
        const ids = [0, 1, 2].map(i => geometry.index ? geometry.index.getX(offset + i) : offset + i);
        const points = ids.map(id => new api.Vector3().fromBufferAttribute(position, id).applyMatrix4(node.matrixWorld));
        const normal = new api.Vector3().subVectors(points[1], points[0])
          .cross(new api.Vector3().subVectors(points[2], points[0])).normalize();
        if (wall(materials[materials.length === 1 ? 0 : (group.materialIndex || 0)]) &&
            points.every(p => p[cut.axis] > cut.min) && Math.abs(normal[cut.axis]) > .9) {
          count++;
          continue;
        }
        indices.push(...ids);
      }
      if (indices.length > start)
        kept.push({start, count: indices.length - start, materialIndex: group.materialIndex || 0});
    }
    if (count) {
      const copy = geometry.clone();
      copy.setIndex(indices);
      copy.clearGroups();
      kept.forEach(group => copy.addGroup(group.start, group.count, group.materialIndex));
      node.geometry = copy;
      removed += count;
    }
  });
  return removed;
};
if (typeof document !== "undefined") {
  const theme = document.createElement("style");
  theme.textContent = `
    :root {
      color-scheme: dark;
      --bg: #12161c; --panel: #1d232c; --line: #333e4c;
      --text: #eef3f9; --muted: #9aa7b8; --mute: #9aa7b8;
      --accent: #69e5b5; --acc: #69e5b5;
    }
    body { font-family: "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif; }
    button, input, select { font-family: inherit; }
    button, select, input:not([type=range]):not([type=checkbox]) {
      background-color: #252e3a; border-color: var(--line); border-radius: 7px;
    }
    button { transition: background-color .14s, border-color .14s, color .14s; letter-spacing: .01em; }
    button:hover:not(:disabled) { background-color: #303d4c; border-color: #668176; }
    button:active:not(:disabled) { background-color: #203b35; }
    button:disabled { cursor: default; }
    button:focus-visible, input:focus-visible, select:focus-visible, summary:focus-visible {
      outline: 2px solid var(--accent); outline-offset: 2px;
    }
    input[type=checkbox], input[type=range] { accent-color: var(--accent); }
    input[type=number] { appearance: textfield; }
    input::-webkit-inner-spin-button { appearance: none; }
    #visualizerNav, body > header { background: #121922 !important; border-bottom: 1px solid var(--line); }
    #visualizerNav a, #visualizerNav button, body > header button { font-weight: 600; border-radius: 7px; }
    #visualizerNav strong { margin-right: 12px; letter-spacing: -.02em; }
    body > header button[aria-current=page] {
      opacity: 1; color: var(--accent); border-color: #356454; background: #203b35;
    }
    #panel, #properties, main > aside, #mappingEditor { background: var(--panel); }
    #panel { backdrop-filter: none; box-shadow: 0 12px 36px #0004; }
    #mappingEditor { border-color: var(--line); box-shadow: 0 12px 36px #0004; }
    #tree .tree-row > button, .fixtureRow { transition: background-color .12s; }
    #tree .tree-row.selected > button:first-child { color: #ffbd7d; background: #493423; }
    .collection { border-bottom: 1px solid #333e4c88; }
    #views { box-shadow: 0 4px 18px #0003; }
    #editVisibility { line-height: 1.5; }
    #showHidden { border-color: #c39450; color: #efcc91; }
    * { scrollbar-width: thin; scrollbar-color: #4b5969 #171e27; }
    @media (prefers-reduced-motion: no-preference) {
      #panel, #mappingEditor, main > aside { animation: panel-in .16s ease-out; }
      @keyframes panel-in { from { opacity: .6; transform: translateY(3px); } to { opacity: 1; transform: none; } }
    }
    @media (prefers-reduced-motion: reduce) { button, #tree .tree-row > button, .fixtureRow { transition: none; } }
  `;
  document.head.append(theme);
}
