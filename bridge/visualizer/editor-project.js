// GLB project extras are interpreted only by the preview; Arena is never changed.
window.applyAPCEditorProject = function (root, api) {
  const records = [];
  root.traverse((node) => {
    const data = node.userData?.apcEditor;
    if (!data) return;
    let active = true;
    for (let parent = node; parent; parent = parent.parent)
      if (parent.userData?.apcEditor?.active === false) active = false;
    node.visible = active;
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

window.apcProjectStore = async function (value) {
  const key = new URLSearchParams(location.search).get("space") || "default";
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
        value === undefined ? store.get(key) : store.put(value, key);
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
