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
    #panel { box-sizing: border-box; width: var(--apc-viewerWidth,310px); height: var(--apc-viewerHeight,auto); }
    #panel.min { height: auto; }
    #mappingEditor { width: var(--apc-mapperWidth,330px); height: var(--apc-mapperHeight,calc(100dvh - 78px)); bottom: auto; }
    #mappingEditor #mappingList { flex: 1 1 auto; min-height: 80px; max-height: none; }
    .editingMapping #inset {
      left: calc(var(--apc-mapperWidth,330px) + 40px) !important;
      width: min(calc(100vw - var(--apc-mapperWidth,330px) - 70px),calc((100vh - 160px)*var(--mapping-aspect,1.77778))) !important;
    }
    body:has(#viewport) main { position: relative; grid-template-columns: minmax(0,1fr) var(--apc-editorWidth,310px); grid-template-rows: minmax(0,var(--apc-treeRatio,44%)) minmax(0,1fr); }
    .apc-panel-heading { display: flex; align-items: center; gap: 8px; }
    button.apc-panel-expand { margin-left: auto; flex: 0 0 auto; font-size: 11px; font-weight: 500; letter-spacing: normal; text-transform: none; padding: 4px 7px; width: auto; }
    .apc-panel-grip { position: fixed; z-index: 15; touch-action: none; border-radius: 3px; background: transparent; }
    .apc-panel-grip[hidden] { display: none !important; }
    .apc-panel-grip[data-axis=x] { cursor: col-resize; }
    .apc-panel-grip[data-axis=y] { cursor: row-resize; }
    .apc-panel-grip:hover, .apc-panel-grip:focus-visible { background: #69e5b56b; outline: 1px solid #69e5b5; }
    .apc-resizing-x *, .apc-resizing-y * { user-select: none !important; }
    .apc-resizing-x * { cursor: col-resize !important; }.apc-resizing-y * { cursor: row-resize !important; }
    .apc-panel-focus { position: fixed !important; left: var(--apc-focus-left) !important; top: var(--apc-focus-top) !important; width: var(--apc-focus-width) !important; height: var(--apc-focus-height) !important; max-height: none !important; z-index: 30 !important; transform: none !important; }
    .apc-panel-focus[hidden] { display: none !important; }
    .apc-panel-focused #viewport, .apc-panel-focused #inset { visibility: hidden; }
    @media (min-width: 900px) {
      #mappingEditor.apc-panel-focus { display: grid; grid-template-columns: minmax(0,1fr) 300px; grid-template-rows: auto auto auto auto minmax(80px,1fr) auto auto; }
      #mappingEditor.apc-panel-focus > * { grid-column: 1; min-width: 0; }
      #mappingEditor.apc-panel-focus > header { grid-column: 1 / -1; }
      #mappingEditor.apc-panel-focus #mappingList { grid-row: 5; min-height: 0; }
      #mappingEditor.apc-panel-focus #mappingPixelControls { max-height: 35vh; overflow: auto; }
      #mappingEditor.apc-panel-focus #wiringSettings { grid-column: 2; grid-row: 2 / -1; overflow: auto; border-top: 0; border-left: 1px solid var(--line); }
    }

    @media (prefers-reduced-motion: no-preference) {
      #panel, #mappingEditor, main > aside { animation: panel-in .16s ease-out; }
      @keyframes panel-in { from { opacity: .6; transform: translateY(3px); } to { opacity: 1; transform: none; } }
    }
    @media (prefers-reduced-motion: reduce) { button, #tree .tree-row > button, .fixtureRow { transition: none; } }
  `;
  document.head.append(theme);
}


function readPanelLayout() {
  try {
    const saved = JSON.parse(localStorage.getItem("apc40-panel-layout:v1") || "{}");
    const result = {};
    for (const key of ["viewerWidth", "viewerHeight", "mapperWidth", "mapperHeight", "editorWidth", "treeRatio"])
      if (typeof saved?.[key] === "number" && Number.isFinite(saved[key]) && saved[key] > 0)
        result[key] = saved[key];
    return result;
  } catch { return {}; }
}
window.apcPanelLayout = function (onChange = () => {}) {
  if (document.body.dataset.panelLayout) return;
  document.body.dataset.panelLayout = "ready";
  const editor = document.getElementById("viewport"), main = editor?.parentElement;
  const viewer = document.getElementById("panel"), mapper = document.getElementById("mappingEditor");
  const collections = document.getElementById("collections"), properties = document.getElementById("properties");
  const settings = readPanelLayout(), rootStyle = document.documentElement.style;
  const grips = [], panels = [viewer, mapper, collections, properties].filter(Boolean);
  let focused = null, pending = null;
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const save = key => {
    try {
      const latest = readPanelLayout();
      if (settings[key] === undefined) delete latest[key];else latest[key] = settings[key];
      localStorage.setItem("apc40-panel-layout:v1", JSON.stringify(latest));
    } catch {}
  };
  function workRect() {
    if (main) return main.getBoundingClientRect();
    const top = (document.getElementById("visualizerNav")?.getBoundingClientRect().bottom || 48) + 14;
    return {left: 16, top, width: Math.max(1, innerWidth - 32), height: Math.max(1, innerHeight - top - 16)};
  }
  function position() {
    if (focused && (focused.hidden || !focused.getClientRects().length)) { focus(null);return; }
    const area = workRect();
    for (const [key, value] of Object.entries({left: area.left, top: area.top, width: area.width, height: area.height}))
      rootStyle.setProperty("--apc-focus-" + key, value + "px");
    for (const grip of grips) {
      const hidden = focused || !grip.panel.getClientRects().length || grip.panel.hidden || (grip.axis === "y" && grip.panel.classList.contains("min"));
      grip.element.hidden = !!hidden;
      if (hidden) continue;
      const rect = grip.panel.getBoundingClientRect();
      const box = grip.key === "editorWidth" ? main.getBoundingClientRect() : rect;
      Object.assign(grip.element.style, grip.axis === "x" ? {
        left: (grip.side === "left" ? rect.left - 4 : rect.right - 4) + "px", top: box.top + "px", width: "8px", height: box.height + "px",
      } : {left: rect.left + "px", top: (rect.bottom - 4) + "px", width: rect.width + "px", height: "8px"});
      const current = grip.key === "treeRatio" ? Math.round(rect.height / area.height * 100) : Math.round(grip.axis === "x" ? rect.width : rect.height);
      const limits = bounds(grip.key);
      grip.element.setAttribute("aria-valuemin", Math.round(limits[0]));
      grip.element.setAttribute("aria-valuemax", Math.round(limits[1]));
      grip.element.setAttribute("aria-valuenow", current);
    }
  }
  function bounds(key) {
    const area = workRect();
    if (key === "treeRatio") return [Math.min(40, 120 / area.height * 100), Math.max(60, 100 - 120 / area.height * 100)];
    return key.endsWith("Width") ? [Math.min(240, Math.max(120, innerWidth - 120)), Math.max(240, innerWidth - 200)] : [Math.min(180, area.height), area.height];
  }
  function apply() {
    const values = {
      viewerWidth: settings.viewerWidth || 310, mapperWidth: settings.mapperWidth || 330,
      editorWidth: settings.editorWidth || (innerWidth <= 800 ? 250 : innerWidth <= 1000 ? 280 : 310),
      treeRatio: settings.treeRatio || 44,
    };
    for (const key of ["viewerHeight", "mapperHeight"]) if (settings[key]) values[key] = settings[key];
    for (const [key, value] of Object.entries(values)) {
      const [min, max] = bounds(key), suffix = key === "treeRatio" ? "%" : "px";
      rootStyle.setProperty("--apc-" + key, clamp(value, min, max) + suffix);
    }
    for (const key of ["viewerHeight", "mapperHeight"]) if (!settings[key]) rootStyle.removeProperty("--apc-" + key);
    position(); onChange();
  }
  function schedule() {
    if (pending !== null) return;
    pending = requestAnimationFrame(() => { pending = null; apply(); });
  }
  function focus(panel) {
    if (focused) {
      focused.classList.remove("apc-panel-focus");
      const button = focused.querySelector(".apc-panel-expand");button.textContent = "Expand";button.setAttribute("aria-pressed", "false");
    }
    focused = focused === panel ? null : panel;
    if (focused) {
      focused.classList.remove("min");focused.classList.add("apc-panel-focus");
      const button = focused.querySelector(".apc-panel-expand");button.textContent = "Restore";button.setAttribute("aria-pressed", "true");
    }
    for (const panel of panels) panel.inert = !!focused && panel !== focused;
    if (editor) editor.inert = !!focused;
    document.body.classList.toggle("apc-panel-focused", !!focused);
    schedule();
  }
  for (const panel of panels) {
    const heading = panel.querySelector("h1,h2,header");
    if (!heading) continue;
    const button = document.createElement("button");button.type = "button";button.className = "apc-panel-expand";button.textContent = "Expand";
    button.title = "Expand this panel to the workspace · Escape to restore";button.setAttribute("aria-label", "Expand or restore " + (heading.textContent.trim() || "panel"));button.setAttribute("aria-pressed", "false");
    button.onclick = () => focus(panel);heading.classList.add("apc-panel-heading");heading.append(button);
  }
  function separator(panel, key, axis, side = "right") {
    if (!panel) return;
    const element = document.createElement("div");element.className = "apc-panel-grip";element.dataset.axis = axis;element.dataset.panelSize = key;
    element.tabIndex = 0;element.setAttribute("role", "separator");element.setAttribute("aria-orientation", axis === "x" ? "vertical" : "horizontal");
    element.setAttribute("aria-label", "Resize " + key.replace(/([A-Z])/g, " $1").toLowerCase());element.title = "Drag to resize · Arrow keys to adjust · Double-click or Home to reset";
    const grip = {element, panel, key, axis, side};grips.push(grip);document.body.append(element);
    let drag = null;
    const reset = () => { delete settings[key];save(key);schedule(); };
    element.ondblclick = reset;
    element.onpointerdown = event => {
      if (event.button !== 0) return;event.preventDefault();event.stopPropagation();
      const rect = panel.getBoundingClientRect();drag = {pointer: event.pointerId, x: event.clientX, y: event.clientY, width: rect.width, height: rect.height, old: settings[key]};
      element.setPointerCapture(event.pointerId);document.body.classList.add("apc-resizing-" + axis);
    };
    element.onpointermove = event => {
      if (!drag) return;
      let value = axis === "x" ? drag.width + (event.clientX - drag.x) * (side === "left" ? -1 : 1) : drag.height + event.clientY - drag.y;
      if (key === "treeRatio") value = value / workRect().height * 100;
      settings[key] = clamp(value, ...bounds(key));schedule();
    };
    const finish = (cancel = false) => {
      if (!drag) return;
      if (cancel) { if (drag.old === undefined) delete settings[key];else settings[key] = drag.old; }
      const pointer = drag.pointer;drag = null;document.body.classList.remove("apc-resizing-" + axis);
      if (element.hasPointerCapture(pointer)) element.releasePointerCapture(pointer);save(key);schedule();
    };
    element.onpointerup = () => finish();element.onpointercancel = () => finish(true);element.onlostpointercapture = () => finish(true);
    element.onkeydown = event => {
      if (event.key === "Home") { event.preventDefault();event.stopPropagation();reset();return; }
      if (event.key === "Escape") { event.preventDefault();event.stopPropagation();finish(true);return; }
      const direction = axis === "x" ? {ArrowLeft: -1, ArrowRight: 1}[event.key] : {ArrowUp: -1, ArrowDown: 1}[event.key];
      if (!direction) return;event.preventDefault();event.stopPropagation();
      const value = Number(element.getAttribute("aria-valuenow"));
      settings[key] = clamp(value + direction * (axis === "x" && side === "left" ? -1 : 1) * (key === "treeRatio" ? 2 : 16), ...bounds(key));save(key);schedule();
    };
  }
  separator(viewer, "viewerWidth", "x");separator(viewer, "viewerHeight", "y");
  separator(mapper, "mapperWidth", "x");separator(mapper, "mapperHeight", "y");
  separator(collections, "editorWidth", "x", "left");separator(collections, "treeRatio", "y");
  const observer = new ResizeObserver(() => { position();onChange(); });for (const panel of panels) observer.observe(panel);if (main) observer.observe(main);
  addEventListener("resize", schedule);
  document.addEventListener("keydown", event => { if (event.key === "Escape" && focused) { event.preventDefault();event.stopPropagation();focus(null); } }, true);
  document.querySelector("#visualizerNav,body>header")?.addEventListener("click", event => { if (focused && event.target.closest("a,button")) focus(null); });
  addEventListener("pagehide", () => { observer.disconnect();if (pending !== null) cancelAnimationFrame(pending); });
  addEventListener("pageshow", event => {
    if (!event.persisted) return;
    for (const key of Object.keys(settings)) delete settings[key];Object.assign(settings, readPanelLayout());
    for (const panel of panels) observer.observe(panel);if (main) observer.observe(main);apply();
  });
  apply();
};
