from __future__ import annotations

import html
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PALETTE = {
    "root": "#084c47",
    "document": "#3f9f91",
    "chunk_type": "#d49a49",
    "entity": "#cf6557",
    "chunk": "#6f91c9",
    "summary": "#9aa3a0",
}


def render_knowledge_graph_svg(tree: dict[str, Any], max_nodes: int = 520) -> str:
    graph = _build_static_graph(tree, max_nodes=max_nodes)
    width = graph["width"]
    height = graph["height"]
    nodes = graph["nodes"]
    links = graph["links"]
    node_by_id = {node["id"]: node for node in nodes}
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    link_markup = []
    for link in links:
        source = node_by_id.get(link["source"])
        target = node_by_id.get(link["target"])
        if not source or not target:
            continue
        mid_x = (source["x"] + target["x"]) / 2
        link_markup.append(
            f'<path d="M {source["x"]:.1f} {source["y"]:.1f} C {mid_x:.1f} {source["y"]:.1f}, '
            f'{mid_x:.1f} {target["y"]:.1f}, {target["x"]:.1f} {target["y"]:.1f}" />'
        )

    node_markup = []
    for node in nodes:
        color = PALETTE.get(node["kind"], PALETTE["summary"])
        label = _truncate(node["name"], 30)
        count = node.get("chunk_count") or node.get("omitted") or ""
        subtitle = f"{node['kind']}{' | ' + str(count) if count else ''}"
        node_markup.append(
            f'<g class="node {node["kind"]}" transform="translate({node["x"]:.1f},{node["y"]:.1f})">'
            f"<title>{_xml(node['name'])}</title>"
            f'<circle r="{node["radius"]}" fill="{color}" />'
            f'<text class="label" x="{node["radius"] + 10}" y="-4">{_xml(label)}</text>'
            f'<text class="meta" x="{node["radius"] + 10}" y="15">{_xml(subtitle)}</text>'
            "</g>"
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Knowledge graph export">
  <defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#17211d" flood-opacity="0.16" />
    </filter>
  </defs>
  <style>
    .bg {{ fill: #f6f7f3; }}
    .title {{ fill: #17211d; font: 700 34px 'Microsoft YaHei UI', Aptos, sans-serif; }}
    .sub {{ fill: #64736d; font: 500 16px 'Microsoft YaHei UI', Aptos, sans-serif; }}
    .links path {{ fill: none; stroke: rgba(23,33,29,0.20); stroke-width: 1.7; stroke-linecap: round; }}
    .node circle {{ stroke: rgba(23,33,29,0.32); stroke-width: 1.4; filter: url(#shadow); }}
    .node .label {{ fill: #17211d; font: 700 14px 'Microsoft YaHei UI', Aptos, sans-serif; paint-order: stroke; stroke: rgba(255,255,255,0.88); stroke-width: 4px; stroke-linejoin: round; }}
    .node .meta {{ fill: #64736d; font: 500 11px 'Microsoft YaHei UI', Aptos, sans-serif; }}
    .node.root .label {{ fill: #084c47; font-size: 16px; }}
  </style>
  <rect class="bg" width="100%" height="100%" />
  <text class="title" x="72" y="58">Knowledge Graph Export</text>
  <text class="sub" x="72" y="88">Documents: {_xml(str(tree.get("document_count", 0)))} | Chunks: {_xml(str(tree.get("chunk_count", 0)))} | Nodes: {len(nodes)} | Generated: {generated_at}</text>
  <g class="links">
    {"".join(link_markup)}
  </g>
  <g class="nodes">
    {"".join(node_markup)}
  </g>
</svg>
"""


def render_knowledge_graph_html(tree: dict[str, Any]) -> str:
    payload = json.dumps(tree, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dynamic Knowledge Graph</title>
  <style>
    :root {{
      --ink:#17211d; --muted:#64736d; --paper:#f6f7f3; --panel:rgba(255,255,252,.94);
      --line:rgba(23,33,29,.14); --teal:#084c47; --ochre:#b66d2b; --blue:#385f9f;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; color:var(--ink); font-family:"Aptos","Microsoft YaHei UI",sans-serif; background:#f6f7f3; }}
    .shell {{ display:grid; grid-template-rows:auto 1fr auto; min-height:100vh; }}
    header {{ display:flex; align-items:center; justify-content:space-between; gap:16px; padding:14px 18px; border-bottom:1px solid var(--line); background:var(--panel); }}
    h1 {{ margin:0; font-size:18px; letter-spacing:0; }}
    .toolbar {{ display:flex; align-items:center; flex-wrap:wrap; gap:8px; }}
    button,input {{ font:inherit; }}
    input {{ width:min(34vw,420px); min-width:180px; padding:9px 11px; border:1px solid var(--line); border-radius:8px; outline:none; background:white; }}
    button {{ min-height:36px; padding:8px 11px; border:1px solid rgba(8,76,71,.18); border-radius:8px; color:var(--teal); background:#fff; cursor:pointer; font-weight:750; }}
    button:hover {{ color:#fffaf0; background:var(--teal); }}
    #stage {{ width:100%; height:calc(100vh - 122px); touch-action:none; cursor:grab; background:linear-gradient(135deg,#f6f7f3,#eef3f1 58%,#fbf2e7); }}
    #stage.dragging {{ cursor:grabbing; }}
    .link {{ fill:none; stroke:rgba(23,33,29,.18); stroke-width:1.45; vector-effect:non-scaling-stroke; }}
    .node {{ cursor:pointer; outline:none; }}
    .node circle {{ stroke:rgba(23,33,29,.30); stroke-width:1.3; vector-effect:non-scaling-stroke; filter:drop-shadow(0 5px 10px rgba(23,33,29,.12)); }}
    .node:hover circle,.node.selected circle {{ stroke:var(--ink); stroke-width:2.8; }}
    .node.dim {{ opacity:.18; }}
    .node text {{ fill:var(--ink); font-size:13px; font-weight:750; paint-order:stroke; stroke:rgba(255,255,255,.92); stroke-width:4px; stroke-linejoin:round; pointer-events:none; }}
    .node .meta {{ fill:var(--muted); font-size:10px; font-weight:600; }}
    footer {{ display:flex; align-items:center; justify-content:space-between; gap:10px; padding:10px 18px; border-top:1px solid var(--line); color:var(--muted); background:var(--panel); font-size:13px; }}
    @media (max-width:760px) {{ header,footer {{ align-items:flex-start; flex-direction:column; }} input {{ width:100%; }} #stage {{ height:calc(100vh - 178px); }} }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>Dynamic Knowledge Graph</h1>
        <div id="stats">Loading...</div>
      </div>
      <div class="toolbar">
        <input id="search" type="search" placeholder="Search nodes, entities, evidence" />
        <button id="fit">Fit</button>
        <button id="freeze">Freeze</button>
        <button id="expand">Expand</button>
        <button id="collapse">Collapse</button>
        <button id="svgExport">Export SVG</button>
        <button id="pngExport">Export PNG</button>
      </div>
    </header>
    <svg id="stage" role="img" aria-label="Dynamic knowledge graph"></svg>
    <footer>
      <span id="detail">Click a node to zoom into its context. Wheel or drag to move through the graph.</span>
      <span id="zoom">100%</span>
    </footer>
  </div>
  <script>
    const tree = {payload};
    const colors = {json.dumps(PALETTE)};
    const svg = document.querySelector("#stage");
    const search = document.querySelector("#search");
    const stats = document.querySelector("#stats");
    const detail = document.querySelector("#detail");
    const zoomLabel = document.querySelector("#zoom");
    let collapsed = new Set();
    let selected = "";
    let graph = {{ nodes: [], links: [], width: 1600, height: 900 }};
    let viewBox = {{ x: 0, y: 0, width: 1600, height: 900 }};
    let frozen = false;
    let drag = null;

    function idFor(path) {{ return path.length ? path.join("/") : "root"; }}
    function textOf(node) {{ return `${{node.name || ""}} ${{node.kind || ""}} ${{node.preview || ""}}`.toLowerCase(); }}
    function matchNode(node, q) {{ return !q || textOf(node).includes(q); }}
    function hasMatch(node, q) {{
      if (!q || matchNode(node, q)) return true;
      return (node.children || []).some(child => hasMatch(child, q));
    }}
    function seedCollapse(node, path=[], depth=0) {{
      const id = idFor(path);
      const children = node.children || [];
      if ((depth >= 1 && children.length) || (node.kind === "chunk_type" && children.length > 18)) collapsed.add(id);
      children.forEach((child, index) => seedCollapse(child, [...path, index], depth + 1));
    }}
    function buildVisible(node, path=[], depth=0, parent=null, q="") {{
      const id = idFor(path);
      const children = node.children || [];
      const visible = !q && collapsed.has(id) ? [] : children.filter(child => hasMatch(child, q));
      const item = {{
        id, parent, depth,
        name: node.name || "Unnamed",
        kind: node.kind || "node",
        preview: node.preview || "",
        chunk_count: node.chunk_count || 0,
        child_count: children.length,
        collapsed: !q && collapsed.has(id),
        matched: matchNode(node, q),
        radius: node.kind === "root" ? 15 : node.kind === "document" ? 12 : node.kind === "chunk" ? 7 : 9,
      }};
      graph.nodes.push(item);
      if (parent) graph.links.push({{ source: parent, target: id }});
      visible.forEach((child, index) => buildVisible(child, [...path, index], depth + 1, id, q));
    }}
    function layout() {{
      const childMap = new Map();
      graph.nodes.forEach(node => childMap.set(node.id, []));
      graph.links.forEach(link => childMap.get(link.source)?.push(link.target));
      const nodeMap = new Map(graph.nodes.map(node => [node.id, node]));
      let cursor = 0;
      let maxDepth = 0;
      function place(id) {{
        const node = nodeMap.get(id);
        const kids = childMap.get(id) || [];
        maxDepth = Math.max(maxDepth, node.depth);
        if (!kids.length) {{
          node.y = 132 + cursor * 58;
          cursor += 1;
        }} else {{
          kids.forEach(place);
          node.y = (nodeMap.get(kids[0]).y + nodeMap.get(kids[kids.length - 1]).y) / 2;
        }}
        node.x = 88 + node.depth * 340;
      }}
      place("root");
      graph.width = Math.max(1200, 220 + maxDepth * 340);
      graph.height = Math.max(720, 220 + cursor * 58);
    }}
    function render(keepView=false) {{
      if (frozen && keepView === "data") return;
      const q = search.value.trim().toLowerCase();
      graph = {{ nodes: [], links: [], width: 1600, height: 900 }};
      buildVisible(tree, [], 0, null, q);
      layout();
      const nodeMap = new Map(graph.nodes.map(node => [node.id, node]));
      svg.innerHTML = "";
      svg.setAttribute("viewBox", `${{viewBox.x}} ${{viewBox.y}} ${{viewBox.width}} ${{viewBox.height}}`);
      const links = document.createElementNS("http://www.w3.org/2000/svg", "g");
      graph.links.forEach(link => {{
        const s = nodeMap.get(link.source), t = nodeMap.get(link.target);
        if (!s || !t) return;
        const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
        const mid = (s.x + t.x) / 2;
        p.setAttribute("class", "link");
        p.setAttribute("d", `M ${{s.x}} ${{s.y}} C ${{mid}} ${{s.y}}, ${{mid}} ${{t.y}}, ${{t.x}} ${{t.y}}`);
        links.appendChild(p);
      }});
      svg.appendChild(links);
      const nodes = document.createElementNS("http://www.w3.org/2000/svg", "g");
      graph.nodes.forEach(node => {{
        const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
        g.setAttribute("class", `node ${{node.kind}} ${{node.id === selected ? "selected" : ""}} ${{q && !node.matched ? "dim" : ""}}`);
        g.setAttribute("transform", `translate(${{node.x}},${{node.y}})`);
        g.setAttribute("tabindex", "0");
        g.addEventListener("click", () => toggleNode(node));
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = node.name;
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("r", node.radius);
        circle.setAttribute("fill", colors[node.kind] || colors.summary);
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", node.radius + 10);
        label.setAttribute("y", -3);
        label.textContent = truncate(node.name, node.depth <= 1 ? 34 : 26);
        const meta = document.createElementNS("http://www.w3.org/2000/svg", "text");
        meta.setAttribute("class", "meta");
        meta.setAttribute("x", node.radius + 10);
        meta.setAttribute("y", 15);
        meta.textContent = `${{node.kind}}${{node.child_count ? " | " + node.child_count : ""}}${{node.collapsed ? " | collapsed" : ""}}`;
        g.append(title, circle, label, meta);
        nodes.appendChild(g);
      }});
      svg.appendChild(nodes);
      stats.textContent = `${{tree.document_count || 0}} documents | ${{tree.chunk_count || 0}} chunks | ${{graph.nodes.length}} visible nodes`;
      if (!keepView) fitGraph();
      updateZoom();
    }}
    function toggleNode(node) {{
      selected = node.id;
      if (node.child_count) {{
        if (collapsed.has(node.id)) collapsed.delete(node.id);
        else collapsed.add(node.id);
      }}
      detail.textContent = `${{node.name}} | ${{node.kind}}${{node.preview ? " | " + node.preview.slice(0, 160) : ""}}`;
      render(true);
      focus(node.id);
    }}
    function focus(id) {{
      const node = graph.nodes.find(item => item.id === id);
      if (!node) return;
      const descendants = graph.nodes.filter(item => item.id === id || item.id.startsWith(id + "/"));
      const xs = descendants.map(item => item.x), ys = descendants.map(item => item.y);
      const minX = Math.min(...xs) - 110, maxX = Math.max(...xs) + 360;
      const minY = Math.min(...ys) - 90, maxY = Math.max(...ys) + 90;
      const width = Math.max(760, maxX - minX), height = Math.max(420, maxY - minY);
      viewBox = {{ x:minX, y:minY, width, height }};
      applyViewBox();
    }}
    function fitGraph() {{
      viewBox = {{ x:0, y:0, width:graph.width, height:graph.height }};
      applyViewBox();
    }}
    function applyViewBox() {{
      svg.setAttribute("viewBox", `${{viewBox.x}} ${{viewBox.y}} ${{viewBox.width}} ${{viewBox.height}}`);
      updateZoom();
    }}
    function updateZoom() {{ zoomLabel.textContent = `${{Math.round(graph.width / viewBox.width * 100)}}%`; }}
    function truncate(value, max) {{ return String(value || "").length > max ? String(value).slice(0, max - 1) + "..." : String(value || ""); }}
    function point(evt) {{
      const rect = svg.getBoundingClientRect();
      return {{ x: viewBox.x + (evt.clientX - rect.left) / rect.width * viewBox.width, y: viewBox.y + (evt.clientY - rect.top) / rect.height * viewBox.height }};
    }}
    svg.addEventListener("wheel", event => {{
      event.preventDefault();
      const p = point(event), factor = event.deltaY < 0 ? .82 : 1.22;
      const width = viewBox.width * factor, height = viewBox.height * factor;
      viewBox = {{ x: p.x - (p.x - viewBox.x) * factor, y: p.y - (p.y - viewBox.y) * factor, width, height }};
      applyViewBox();
    }}, {{ passive:false }});
    svg.addEventListener("pointerdown", event => {{
      if (event.target.closest && event.target.closest(".node")) return;
      drag = {{ x:event.clientX, y:event.clientY, box:{{...viewBox}} }};
      svg.classList.add("dragging");
      svg.setPointerCapture(event.pointerId);
    }});
    svg.addEventListener("pointermove", event => {{
      if (!drag) return;
      const rect = svg.getBoundingClientRect();
      viewBox = {{ ...drag.box, x: drag.box.x - (event.clientX - drag.x) / rect.width * drag.box.width, y: drag.box.y - (event.clientY - drag.y) / rect.height * drag.box.height }};
      applyViewBox();
    }});
    svg.addEventListener("pointerup", event => {{ drag = null; svg.classList.remove("dragging"); if (svg.hasPointerCapture(event.pointerId)) svg.releasePointerCapture(event.pointerId); }});
    search.addEventListener("input", () => render());
    document.querySelector("#fit").addEventListener("click", fitGraph);
    document.querySelector("#freeze").addEventListener("click", event => {{ frozen = !frozen; event.target.textContent = frozen ? "Unfreeze" : "Freeze"; }});
    document.querySelector("#expand").addEventListener("click", () => {{ collapsed.clear(); render(); }});
    document.querySelector("#collapse").addEventListener("click", () => {{ collapsed.clear(); seedCollapse(tree); render(); }});
    document.querySelector("#svgExport").addEventListener("click", () => download(new Blob([new XMLSerializer().serializeToString(svg)], {{type:"image/svg+xml"}}), "knowledge-graph.svg"));
    document.querySelector("#pngExport").addEventListener("click", async () => {{
      const text = new XMLSerializer().serializeToString(svg);
      const image = new Image();
      const url = URL.createObjectURL(new Blob([text], {{type:"image/svg+xml"}}));
      image.src = url;
      await image.decode();
      const canvas = document.createElement("canvas");
      canvas.width = Math.min(7680, Math.max(2400, Math.round(viewBox.width * 2)));
      canvas.height = Math.min(7680, Math.max(1400, Math.round(viewBox.height * 2)));
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#f6f7f3";
      ctx.fillRect(0,0,canvas.width,canvas.height);
      ctx.drawImage(image,0,0,canvas.width,canvas.height);
      URL.revokeObjectURL(url);
      canvas.toBlob(blob => blob && download(blob, "knowledge-graph.png"), "image/png");
    }});
    function download(blob, filename) {{
      const url = URL.createObjectURL(blob), a = document.createElement("a");
      a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    }}
    seedCollapse(tree);
    render();
  </script>
</body>
</html>"""


def render_knowledge_graph_png(tree: dict[str, Any], output_path: str | Path, max_nodes: int = 360) -> Path:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover - depends on optional runtime
        raise RuntimeError("Pillow is required for PNG graph export. Install requirements-runtime.txt.") from exc

    graph = _build_static_graph(tree, max_nodes=max_nodes)
    scale = min(2.2, 3840 / graph["width"])
    width = int(graph["width"] * scale)
    height = min(16000, int(graph["height"] * scale))
    scale = min(scale, height / graph["height"])
    width = int(graph["width"] * scale)
    height = int(graph["height"] * scale)
    image = Image.new("RGB", (width, height), "#f6f7f3")
    draw = ImageDraw.Draw(image)
    font = _load_font(ImageFont, 24)
    small_font = _load_font(ImageFont, 17)
    title_font = _load_font(ImageFont, 42)
    node_by_id = {node["id"]: node for node in graph["nodes"]}

    def sx(value: float) -> int:
        return int(value * scale)

    draw.text((sx(72), sx(24)), "Knowledge Graph Export", fill="#17211d", font=title_font)
    draw.text(
        (sx(72), sx(76)),
        f"Documents: {tree.get('document_count', 0)} | Chunks: {tree.get('chunk_count', 0)} | Nodes: {len(graph['nodes'])}",
        fill="#64736d",
        font=small_font,
    )
    for link in graph["links"]:
        source = node_by_id.get(link["source"])
        target = node_by_id.get(link["target"])
        if not source or not target:
            continue
        draw.line((sx(source["x"]), sx(source["y"]), sx(target["x"]), sx(target["y"])), fill="#c9cfca", width=max(2, sx(1.2)))
    for node in graph["nodes"]:
        radius = sx(node["radius"])
        x = sx(node["x"])
        y = sx(node["y"])
        fill = PALETTE.get(node["kind"], PALETTE["summary"])
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill, outline="#42504a", width=max(1, sx(1)))
        draw.text((x + radius + sx(10), y - sx(17)), _truncate(node["name"], 28), fill="#17211d", font=font)
        meta = node["kind"]
        if node.get("chunk_count"):
            meta += f" | {node['chunk_count']}"
        draw.text((x + radius + sx(10), y + sx(8)), meta, fill="#64736d", font=small_font)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, "PNG", optimize=True)
    return output


def _build_static_graph(tree: dict[str, Any], max_nodes: int) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, str]] = []
    omitted = 0

    def add_node(node: dict[str, Any], path: list[int], depth: int, parent: str | None) -> str:
        node_id = "root" if not path else "/".join(str(item) for item in path)
        kind = node.get("kind", "node")
        nodes.append(
            {
                "id": node_id,
                "name": str(node.get("name", "Unnamed")),
                "kind": kind,
                "depth": depth,
                "chunk_count": node.get("chunk_count", 0),
                "preview": node.get("preview", ""),
                "radius": 15 if kind == "root" else 12 if kind == "document" else 8 if kind == "chunk" else 10,
            }
        )
        if parent:
            links.append({"source": parent, "target": node_id})
        return node_id

    def walk(node: dict[str, Any], path: list[int], depth: int, parent: str | None) -> None:
        nonlocal omitted
        if len(nodes) >= max_nodes:
            omitted += 1
            return
        node_id = add_node(node, path, depth, parent)
        children = list(node.get("children") or [])
        children.sort(key=lambda item: (0 if item.get("kind") != "chunk" else 1, str(item.get("name", ""))))
        if node.get("kind") == "chunk_type":
            entity_children = [item for item in children if item.get("kind") == "entity"]
            chunk_children = [item for item in children if item.get("kind") == "chunk"]
            other_children = [item for item in children if item.get("kind") not in {"entity", "chunk"}]
            children = entity_children[:32] + other_children[:24] + chunk_children[:28]
        for index, child in enumerate(children):
            walk(child, path + [index], depth + 1, node_id)

    walk(tree, [], 0, None)
    if omitted:
        summary_id = "omitted"
        nodes.append({"id": summary_id, "name": f"{omitted} additional nodes omitted", "kind": "summary", "depth": 1, "omitted": omitted, "radius": 10})
        links.append({"source": "root", "target": summary_id})

    children_by_parent: dict[str, list[str]] = {node["id"]: [] for node in nodes}
    for link in links:
        children_by_parent.setdefault(link["source"], []).append(link["target"])
    node_by_id = {node["id"]: node for node in nodes}
    cursor = 0
    max_depth = 0

    def place(node_id: str) -> float:
        nonlocal cursor, max_depth
        node = node_by_id[node_id]
        kids = children_by_parent.get(node_id, [])
        max_depth = max(max_depth, node["depth"])
        if not kids:
            node["y"] = 132 + cursor * 62
            cursor += 1
        else:
            child_ys = [place(child_id) for child_id in kids if child_id in node_by_id]
            node["y"] = sum(child_ys) / len(child_ys) if child_ys else 132 + cursor * 62
        node["x"] = 76 + node["depth"] * 360
        return node["y"]

    place("root")
    width = int(max(1280, 240 + max_depth * 360))
    height = int(max(820, 190 + cursor * 62))
    return {"nodes": nodes, "links": links, "width": width, "height": height}


def _load_font(image_font: Any, size: int) -> Any:
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return image_font.truetype(candidate, size=size)
    return image_font.load_default()


def _truncate(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _xml(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)
