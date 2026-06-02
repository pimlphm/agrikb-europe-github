from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
THREAD_ID = "manual-20260523-agrikb"
WORKSPACE = PROJECT_ROOT / "outputs" / THREAD_ID / "presentations" / "agrikb-first-prize"
SLIDES_DIR = WORKSPACE / "slides"
PREVIEW_DIR = WORKSPACE / "preview"
LAYOUT_DIR = WORKSPACE / "layout"
QA_DIR = WORKSPACE / "qa"
OUTPUT_DIR = PROJECT_ROOT / "deliverables" / "AgriKB_DualTrack_FirstPrize_Materials_20260523"


HELPERS = r'''
const C = {
  paper: "#F7F5EC",
  field: "#E7F0DB",
  ink: "#17211D",
  muted: "#63716A",
  green: "#2F7D52",
  deepGreen: "#1F5137",
  ochre: "#B6852D",
  clay: "#8A5132",
  blue: "#416F9F",
  red: "#B14A3C",
  white: "#FFFFFF",
  line: "#D7DFCF",
  paleBlue: "#EAF0F7",
  paleGold: "#F4E8C8",
  paleClay: "#F2E0D8"
};

function shape(ctx, slide, x, y, w, h, fill = C.white, line = C.line, width = 1, name = "") {
  return ctx.addShape(slide, {
    x, y, w, h,
    name,
    fill,
    line: { style: "solid", fill: line, width }
  });
}

function text(ctx, slide, value, x, y, w, h, opts = {}) {
  return ctx.addText(slide, {
    text: value,
    x, y, w, h,
    fontSize: opts.size ?? 24,
    color: opts.color ?? C.ink,
    bold: opts.bold ?? false,
    typeface: opts.face ?? "Microsoft YaHei",
    align: opts.align ?? "left",
    valign: opts.valign ?? "top",
    fill: opts.fill ?? "#00000000",
    line: { style: "solid", fill: opts.line ?? "#00000000", width: opts.lineWidth ?? 0 },
    insets: opts.insets ?? { left: 8, right: 8, top: 6, bottom: 6 },
    name: opts.name
  });
}

function pageBase(ctx, slide, spec) {
  shape(ctx, slide, 0, 0, 1280, 720, C.paper, C.paper, 0, "background");
  for (let i = 0; i < 12; i += 1) {
    shape(ctx, slide, 16 + i * 100, 672, 72, 12, i % 2 ? "#DCE8CF" : "#CFE0BF", "#00000000", 0, `field-row-${i}`);
  }
  shape(ctx, slide, 54, 44, 42, 4, C.green, C.green, 0, "kicker-marker");
  text(ctx, slide, spec.kicker || "AGRIKB", 106, 33, 540, 26, { size: 14, color: C.green, bold: true, name: "kicker-label" });
  text(ctx, slide, String(spec.slideNo || ""), 1190, 36, 44, 24, { size: 12, color: C.muted, align: "right" });
  text(ctx, slide, "AgriKB 数智新农人经营中枢", 54, 686, 360, 22, { size: 11, color: C.muted });
}

function titleBlock(ctx, slide, spec, y = 68) {
  text(ctx, slide, spec.title, 54, y, 1040, 80, { size: spec.titleSize || 30, bold: true, color: C.ink, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  if (spec.subtitle) {
    text(ctx, slide, spec.subtitle, 58, y + 86, 940, 36, { size: 15, color: C.muted, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  }
}

function card(ctx, slide, x, y, w, h, title, body, opts = {}) {
  shape(ctx, slide, x, y, w, h, opts.fill ?? C.white, opts.line ?? C.line, opts.lineWidth ?? 1, opts.name);
  if (opts.accent) shape(ctx, slide, x, y, 6, h, opts.accent, opts.accent, 0);
  if (h <= 90 && w > 430) {
    text(ctx, slide, title, x + 18, y + 12, 168, h - 22, { size: opts.titleSize ?? 16, bold: true, color: opts.titleColor ?? C.ink });
    text(ctx, slide, body, x + 204, y + 12, w - 228, h - 22, { size: opts.bodySize ?? 13.5, color: opts.bodyColor ?? C.muted });
    return;
  }
  text(ctx, slide, title, x + 18, y + 16, w - 36, 30, { size: opts.titleSize ?? 18, bold: true, color: opts.titleColor ?? C.ink });
  text(ctx, slide, body, x + 18, y + 54, w - 36, h - 60, { size: opts.bodySize ?? 13.5, color: opts.bodyColor ?? C.muted });
}

function metric(ctx, slide, x, y, w, label, value, color = C.green) {
  shape(ctx, slide, x, y, w, 84, C.white, "#DCE4D6", 1);
  text(ctx, slide, value, x + 16, y + 12, w - 32, 32, { size: 25, bold: true, color });
  text(ctx, slide, label, x + 16, y + 48, w - 32, 20, { size: 12, color: C.muted });
}

async function addIcon(ctx, slide, icon, x, y, w, h, color = C.green) {
  try {
    await ctx.addLucideIcon(slide, { icon, x, y, w, h, color, strokeWidth: 1.9, alt: icon });
  } catch {
    shape(ctx, slide, x, y, w, h, "#00000000", color, 1);
  }
}

function pill(ctx, slide, x, y, w, label, color = C.green, fill = C.white) {
  shape(ctx, slide, x, y, w, 34, fill, color, 1.2);
  text(ctx, slide, label, x + 8, y + 6, w - 16, 20, { size: 12.5, bold: true, color, align: "center", valign: "middle" });
}

function arrowText(ctx, slide, x, y, color = C.ochre) {
  text(ctx, slide, "→", x, y, 36, 30, { size: 28, bold: true, color, align: "center", valign: "middle" });
}

export async function buildSpecSlide(presentation, ctx, spec) {
  const slide = presentation.slides.add();
  pageBase(ctx, slide, spec);

  if (spec.layout === "cover") {
    text(ctx, slide, "2026 句容“福地青年英才”创业大赛", 58, 72, 580, 28, { size: 16, color: C.green, bold: true, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
    text(ctx, slide, "AgriKB\n数智新农人经营中枢", 58, 122, 680, 128, { size: 48, bold: true, color: C.ink, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
    text(ctx, slide, "用 AI/RAG、农业知识图谱、实时政策市场情报，把县域农业经营变成可追溯、可执行、可复制的智能决策。", 62, 280, 660, 78, { size: 22, color: C.muted, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
    pill(ctx, slide, 62, 384, 164, "数智信息技术", C.green, "#F2F8ED");
    pill(ctx, slide, 242, 384, 134, "新农人", C.ochre, "#F8F1DF");
    pill(ctx, slide, 392, 384, 192, "句容县域示范", C.blue, "#EAF0F7");
    metric(ctx, slide, 62, 486, 164, "农业知识块", "145+", C.green);
    metric(ctx, slide, 248, 486, 164, "目标用户", "3类", C.ochre);
    metric(ctx, slide, 434, 486, 164, "交付形态", "PWA", C.blue);
    shape(ctx, slide, 760, 90, 420, 426, C.field, "#CCDAC0", 1);
    for (let i = 0; i < 7; i += 1) shape(ctx, slide, 790 + i * 55, 428 - i * 31, 42, 150 + i * 24, i % 2 ? "#BED7A8" : "#D4E6C6", "#00000000", 0);
    await addIcon(ctx, slide, "Wheat", 890, 172, 120, 120, C.green);
    card(ctx, slide, 810, 420, 320, 92, "答辩主张", "不是农业聊天页，而是县域农业经营智能体：问答、证据、图谱、政策、市场、部署一起闭环。", { fill: "#FFFFFF", accent: C.green, bodySize: 12.5 });
  }

  if (spec.layout === "lanes") {
    titleBlock(ctx, slide, spec);
    const lanes = spec.lanes;
    lanes.forEach((lane, i) => {
      const x = 72 + i * 566;
      shape(ctx, slide, x, 210, 500, 330, lane.fill, lane.color, 1.2);
      text(ctx, slide, lane.title, x + 26, 232, 360, 38, { size: 26, bold: true, color: lane.color });
      lane.items.forEach((item, idx) => {
        shape(ctx, slide, x + 30, 300 + idx * 58, 18, 18, lane.color, lane.color, 0);
        text(ctx, slide, item, x + 60, 290 + idx * 58, 390, 40, { size: 16, color: C.ink });
      });
    });
    text(ctx, slide, "融合点：用数智信息技术解决新农人真实经营问题，并把经营结果反哺农业局产业治理。", 150, 590, 980, 44, { size: 22, color: C.ink, bold: true, align: "center" });
  }

  if (spec.layout === "pain") {
    titleBlock(ctx, slide, spec);
    const cards = spec.cards;
    cards.forEach((c, i) => {
      const x = 70 + i * 390;
      card(ctx, slide, x, 218, 330, 230, c.title, c.body, { fill: c.fill, accent: c.color, titleColor: c.color, bodySize: 15 });
      text(ctx, slide, c.after, x + 16, 478, 300, 60, { size: 15, bold: true, color: C.ink, align: "center" });
    });
    card(ctx, slide, 132, 582, 1016, 54, "AgriKB 的突破", "把政策、气象、市场、收购、认证、作物知识和本地台账统一成“可检索证据对象”，再由真实模型整合回答。", { fill: "#FFFFFF", accent: C.green, bodySize: 15 });
  }

  if (spec.layout === "workflow") {
    titleBlock(ctx, slide, spec);
    const steps = spec.steps;
    steps.forEach((s, i) => {
      const x = 66 + i * 230;
      shape(ctx, slide, x, 250, 182, 170, s.fill, s.color, 1.2);
      text(ctx, slide, `0${i + 1}`, x + 14, 265, 50, 34, { size: 20, bold: true, color: s.color });
      text(ctx, slide, s.title, x + 14, 304, 154, 30, { size: 18, bold: true, color: C.ink });
      text(ctx, slide, s.body, x + 14, 340, 154, 48, { size: 12.5, color: C.muted });
      if (i < steps.length - 1) arrowText(ctx, slide, x + 188, 306, C.ochre);
    });
    card(ctx, slide, 96, 488, 1088, 86, "回答输出顺序", "先给经营判断，再给政策匹配、市场/收购信息、渠道建议、风险提示和下一步动作；证据链与知识树默认隐藏，可展开审计。", { fill: "#FFFFFF", accent: C.green, bodySize: 16 });
  }

  if (spec.layout === "architecture") {
    titleBlock(ctx, slide, spec);
    const lanes = [
      ["数据层", "AGROVOC / Crop Ontology / GEE\n台湾农业开放数据 / COA_OpenData\n句容政策 PDF / 农业局台账 / 实时网页", C.green, "#EEF6EA"],
      ["知识与检索层", "分段入库 / SQLite 知识块\nBM25 + Dense + Hybrid + Rerank\n农业知识图谱 / 会话记忆", C.ochre, "#F7F0DF"],
      ["模型与应用层", "Kimi/Moonshot 兼容接口\nOllama 本地模型回退\n问答 / 报告 / 证据链 / PWA", C.blue, "#EAF0F7"],
    ];
    lanes.forEach((lane, i) => {
      const y = 190 + i * 135;
      shape(ctx, slide, 86, y, 1048, 104, lane[3], lane[2], 1.3);
      text(ctx, slide, lane[0], 112, y + 18, 190, 34, { size: 22, bold: true, color: lane[2] });
      text(ctx, slide, lane[1], 320, y + 14, 770, 72, { size: 16, color: C.ink });
      if (i < 2) text(ctx, slide, "↓", 604, y + 104, 40, 30, { size: 28, color: C.ochre, align: "center" });
    });
    text(ctx, slide, "关键壁垒：证据对象 + 农业语义图谱 + 经营任务提示词，让模型不再固定话术，而是真正综合分析。", 122, 610, 990, 34, { size: 19, bold: true, color: C.ink, align: "center" });
  }

  if (spec.layout === "evidence") {
    titleBlock(ctx, slide, spec);
    shape(ctx, slide, 472, 312, 338, 138, "#FFFFFF", C.green, 1.4);
    text(ctx, slide, "证据对象", 558, 328, 166, 32, { size: 24, bold: true, color: C.green, align: "center" });
    text(ctx, slide, "来源 / 时间 / 地域 / 主体\n政策 / 市场 / 作物 / 气象\n可信度 / 可展开链路", 510, 368, 260, 56, { size: 14, color: C.ink, align: "center" });
    const sources = spec.sources;
    sources.forEach((s, i) => {
      const col = i % 3;
      const row = Math.floor(i / 3);
      const x = 74 + col * 382;
      const y = row === 0 ? 206 : 524;
      card(ctx, slide, x, y, 280, 82, s.title, s.body, { fill: s.fill, accent: s.color, bodySize: 12.5, titleSize: 16, titleColor: s.color });
    });
    text(ctx, slide, "默认对农户只显示结论；农业局/企业审计时一键展开证据链和知识树。", 206, 464, 870, 34, { size: 20, bold: true, color: C.ink, align: "center" });
  }

  if (spec.layout === "scenario") {
    titleBlock(ctx, slide, spec);
    shape(ctx, slide, 72, 192, 448, 380, C.field, "#C9DABF", 1.2);
    text(ctx, slide, "句容应用样板", 104, 220, 240, 34, { size: 24, bold: true, color: C.green });
    await addIcon(ctx, slide, "MapPinned", 386, 218, 70, 70, C.green);
    ["草莓采收", "福桃销售", "茶叶品牌", "蔬菜供应"].forEach((label, i) => {
      const x = 116 + (i % 2) * 190;
      const y = 300 + Math.floor(i / 2) * 104;
      shape(ctx, slide, x, y, 148, 62, "#FFFFFF", C.green, 1);
      text(ctx, slide, label, x + 10, y + 18, 128, 24, { size: 17, bold: true, color: C.ink, align: "center" });
    });
    const ladder = spec.ladder;
    ladder.forEach((item, i) => {
      const y = 200 + i * 76;
      shape(ctx, slide, 594, y, 520, 54, i % 2 ? "#FFFFFF" : "#F4F8F0", item.color, 1.1);
      text(ctx, slide, item.title, 616, y + 10, 150, 26, { size: 17, bold: true, color: item.color });
      text(ctx, slide, item.body, 780, y + 9, 300, 30, { size: 14.5, color: C.ink });
    });
  }

  if (spec.layout === "demo") {
    titleBlock(ctx, slide, spec);
    shape(ctx, slide, 86, 178, 430, 420, "#17211D", "#17211D", 0);
    shape(ctx, slide, 116, 210, 370, 330, "#FFFFFF", "#FFFFFF", 0);
    text(ctx, slide, "句容草莓今天要不要采收？", 138, 238, 316, 46, { size: 18, bold: true, color: C.ink });
    text(ctx, slide, "回答摘要", 138, 302, 120, 24, { size: 13, bold: true, color: C.green });
    text(ctx, slide, "建议分批采收，优先走本地团购+电商预售；若降雨预警增强，提前完成包装与冷链排班。", 138, 330, 302, 86, { size: 15, color: C.ink });
    pill(ctx, slide, 138, 438, 92, "政策匹配", C.green, "#EEF6EA");
    pill(ctx, slide, 246, 438, 92, "市场收购", C.ochre, "#F7F0DF");
    pill(ctx, slide, 354, 438, 92, "证据链", C.blue, "#EAF0F7");
    const panels = spec.panels;
    panels.forEach((p, i) => {
      const y = 196 + i * 118;
      card(ctx, slide, 574, y, 550, 88, p.title, p.body, { fill: p.fill, accent: p.color, titleColor: p.color, bodySize: 14.5 });
    });
    text(ctx, slide, "演示关键：现场打开联网搜索，再展开证据链，证明答案不是固定模板。", 176, 626, 926, 34, { size: 20, bold: true, color: C.ink, align: "center" });
  }

  if (spec.layout === "business") {
    titleBlock(ctx, slide, spec);
    const roles = spec.roles;
    for (let i = 0; i < roles.length; i += 1) {
      const r = roles[i];
      const x = 72 + i * 390;
      shape(ctx, slide, x, 204, 330, 292, r.fill, r.color, 1.3);
      await addIcon(ctx, slide, r.icon, x + 126, 228, 78, 78, r.color);
      text(ctx, slide, r.title, x + 32, 324, 266, 32, { size: 23, bold: true, color: r.color, align: "center" });
      text(ctx, slide, r.body, x + 28, 370, 274, 78, { size: 15, color: C.ink, align: "center" });
    }
    card(ctx, slide, 138, 560, 1004, 58, "收入结构", "政府项目/运维 + 企业数据服务/供应链协同 + 新农人工具包/培训营；先从句容样板做标杆，再复制到县域农业场景。", { fill: "#FFFFFF", accent: C.green, bodySize: 16 });
  }

  if (spec.layout === "deploy") {
    titleBlock(ctx, slide, spec);
    const devices = spec.devices;
    for (let i = 0; i < devices.length; i += 1) {
      const d = devices[i];
      const x = 86 + i * 275;
      shape(ctx, slide, x, 220, 220, 250, d.fill, d.color, 1.2);
      await addIcon(ctx, slide, d.icon, x + 74, 242, 72, 72, d.color);
      text(ctx, slide, d.title, x + 18, 330, 184, 30, { size: 20, bold: true, color: d.color, align: "center" });
      text(ctx, slide, d.body, x + 18, 370, 184, 66, { size: 14, color: C.ink, align: "center" });
    }
    text(ctx, slide, "当前已补 PWA manifest 和 service worker：手机可同网访问并添加到主屏幕。", 148, 558, 990, 38, { size: 21, bold: true, color: C.ink, align: "center" });
  }

  if (spec.layout === "ip") {
    titleBlock(ctx, slide, spec);
    const rings = spec.rings;
    rings.forEach((r, i) => {
      const x = 126 + i * 210;
      shape(ctx, slide, x, 238, 180, 180, r.fill, r.color, 1.4);
      text(ctx, slide, r.title, x + 18, 278, 144, 36, { size: 19, bold: true, color: r.color, align: "center" });
      text(ctx, slide, r.body, x + 24, 330, 132, 48, { size: 13, color: C.ink, align: "center" });
    });
    card(ctx, slide, 178, 506, 924, 76, "知识产权组合", "专利保护“多源证据对象 + 农业图谱 + 经营决策生成方法”；软著保护 AgriKB V1.0 软件实现；数据和地区知识包形成持续壁垒。", { fill: "#FFFFFF", accent: C.ochre, bodySize: 15.5 });
  }

  if (spec.layout === "final") {
    titleBlock(ctx, slide, spec);
    const rows = spec.rows;
    rows.forEach((r, i) => {
      const y = 194 + i * 72;
      shape(ctx, slide, 110, y, 1060, 50, i % 2 ? "#FFFFFF" : "#F5F9F0", r.color, 1);
      text(ctx, slide, r.left, 136, y + 11, 300, 26, { size: 17, bold: true, color: r.color });
      text(ctx, slide, r.right, 454, y + 10, 676, 28, { size: 15.5, color: C.ink });
    });
    text(ctx, slide, "结论：技术像数智信息项目，价值像新农人项目，交付像可运行软件。", 150, 604, 980, 42, { size: 28, bold: true, color: C.green, align: "center" });
  }

  return slide;
}
'''


SLIDES = [
    {
        "slideNo": 1,
        "layout": "cover",
        "kicker": "FIRST PRIZE POSITIONING",
        "title": "AgriKB 数智新农人经营中枢",
    },
    {
        "slideNo": 2,
        "layout": "lanes",
        "kicker": "DUAL TRACK FIT",
        "title": "它不是二选一，而是把“数智信息技术”落到“新农人经营”。",
        "subtitle": "句容大赛三大赛道中，AgriKB 选择双赛道融合：技术壁垒来自 AI 与知识图谱，产业价值来自农业经营。", 
        "lanes": [
            {
                "title": "数智信息技术",
                "color": "#2F7D52",
                "fill": "#EEF6EA",
                "items": ["RAG / GraphRAG / 农业知识图谱", "实时搜索、气象、政策、市场数据融合", "Kimi 兼容接口 + 本地模型回退", "证据链审计与报告自动生成"],
            },
            {
                "title": "新农人",
                "color": "#B6852D",
                "fill": "#F7F0DF",
                "items": ["采收、销售、收购、电商渠道判断", "新农人政策申报和培训支持", "合作社与农企供应链协同", "县域农业局产业扶持与项目筛选"],
            },
        ],
    },
    {
        "slideNo": 3,
        "layout": "pain",
        "kicker": "WHY NOW",
        "title": "县域农业的难点不是没有信息，而是信息无法变成当天的经营动作。",
        "subtitle": "农民、农业局、农企面对的是同一片地，却被数据、政策和市场割裂开来。",
        "cards": [
            {"title": "新农人", "body": "气象、病虫害、采收、收购价、电商节奏和补贴材料散在多个渠道。", "after": "需要：今天做什么", "color": "#2F7D52", "fill": "#EEF6EA"},
            {"title": "农业局", "body": "政策文件、主体台账、项目申报、培训记录和产业扶持缺少统一证据链。", "after": "需要：扶持谁、怎么扶持", "color": "#416F9F", "fill": "#EAF0F7"},
            {"title": "农企", "body": "产地采购、认证溯源、稳定供货和品牌电商运营需要可信数据支撑。", "after": "需要：买什么、怎么卖", "color": "#B6852D", "fill": "#F7F0DF"},
        ],
    },
    {
        "slideNo": 4,
        "layout": "workflow",
        "kicker": "PRODUCT LOOP",
        "title": "AgriKB 把一个农业问题转成“数据检索、模型分析、经营执行”的闭环。",
        "subtitle": "面向一线使用，默认展示结论；面向管理和审计，可展开证据链。",
        "steps": [
            {"title": "提问", "body": "作物、地点、时间、经营目标", "color": "#2F7D52", "fill": "#EEF6EA"},
            {"title": "召回", "body": "知识库、图谱、政策、实时网页", "color": "#416F9F", "fill": "#EAF0F7"},
            {"title": "融合", "body": "证据对象去重、排序、冲突检测", "color": "#B6852D", "fill": "#F7F0DF"},
            {"title": "生成", "body": "真实模型综合分析，非固定回答", "color": "#8A5132", "fill": "#F2E0D8"},
            {"title": "执行", "body": "政策、市场、收购、渠道与风险", "color": "#2F7D52", "fill": "#FFFFFF"},
        ],
    },
    {
        "slideNo": 5,
        "layout": "architecture",
        "kicker": "TECH BARRIER",
        "title": "技术壁垒在“农业证据对象”和“经营任务提示词”，不只是接一个大模型。",
        "subtitle": "真实模型回答 + 多源证据 + 知识图谱，让系统能解释、能复核、能持续增量学习。",
    },
    {
        "slideNo": 6,
        "layout": "evidence",
        "kicker": "DATA & EVIDENCE",
        "title": "用公开农业知识和本地政策数据，构造可审计的县域农业知识底座。",
        "subtitle": "当前材料包已覆盖国际农业词表、作物本体、遥感目录、台湾农业开放数据和句容比赛政策要点。",
        "sources": [
            {"title": "AGROVOC", "body": "FAO 农业多语言控制词表", "color": "#2F7D52", "fill": "#EEF6EA"},
            {"title": "Crop Ontology", "body": "作物性状、观测变量与测量方法", "color": "#416F9F", "fill": "#EAF0F7"},
            {"title": "GEE Agriculture", "body": "土地覆盖、遥感、环境变量目录", "color": "#B6852D", "fill": "#F7F0DF"},
            {"title": "台湾开放数据", "body": "有机农业经营者、产品、认证字段", "color": "#8A5132", "fill": "#F2E0D8"},
            {"title": "句容政策文件", "body": "福地青年英才创业大赛赛道和申报要点", "color": "#2F7D52", "fill": "#EEF6EA"},
            {"title": "实时 Web Search", "body": "气象、新闻政策、市场收购和电商渠道", "color": "#416F9F", "fill": "#EAF0F7"},
        ],
    },
    {
        "slideNo": 7,
        "layout": "scenario",
        "kicker": "JURONG PILOT",
        "title": "以江苏句容为示范，把台湾数据样板迁移为本地农业经营判断。",
        "subtitle": "先解决草莓、福桃、茶叶、蔬菜等可演示场景，再扩展到县域多产业。",
        "ladder": [
            {"title": "气象环境", "body": "降雨、温度、灾害预警影响采收窗口", "color": "#416F9F"},
            {"title": "市场收购", "body": "本地收购点、批发行情、电商预售节奏", "color": "#B6852D"},
            {"title": "政策扶持", "body": "新农人培训、创业扶持、产业项目材料", "color": "#2F7D52"},
            {"title": "质量溯源", "body": "认证、主体、产地、批次和销售渠道", "color": "#8A5132"},
            {"title": "经营建议", "body": "分批采收、渠道组合、风险预案、申报清单", "color": "#2F7D52"},
        ],
    },
    {
        "slideNo": 8,
        "layout": "demo",
        "kicker": "LIVE DEMO",
        "title": "演示不是念稿：现场提问，系统实时给经营判断和可展开证据。",
        "subtitle": "回答中默认展示政策、市场和收购判断；证据链、知识树按需打开。",
        "panels": [
            {"title": "政策判断", "body": "匹配句容创业大赛、新农人培训、农业产业扶持材料清单。", "color": "#2F7D52", "fill": "#EEF6EA"},
            {"title": "市场判断", "body": "结合本地收购、批发行情、电商渠道和短期天气给出销售策略。", "color": "#B6852D", "fill": "#F7F0DF"},
            {"title": "审计判断", "body": "展开证据链即可看到文件、网页、知识图谱节点和检索来源。", "color": "#416F9F", "fill": "#EAF0F7"},
        ],
    },
    {
        "slideNo": 9,
        "layout": "business",
        "kicker": "BUSINESS MODEL",
        "title": "从比赛项目到可交付软件：政府端、企业端、新农人端三线变现。",
        "subtitle": "先做句容样板，再复制到县域农业局、合作社、农企和电商助农服务商。",
        "roles": [
            {"title": "农业局", "body": "项目筛选、政策兑现、产业报告、培训工具和年度运维。", "icon": "Building2", "color": "#416F9F", "fill": "#EAF0F7"},
            {"title": "农企/平台", "body": "产地采购、认证溯源、供应链协同、电商运营数据服务。", "icon": "Store", "color": "#B6852D", "fill": "#F7F0DF"},
            {"title": "新农人", "body": "轻量工具包、合作社集采、培训营、助农渠道对接。", "icon": "Leaf", "color": "#2F7D52", "fill": "#EEF6EA"},
        ],
    },
    {
        "slideNo": 10,
        "layout": "deploy",
        "kicker": "DEPLOYMENT",
        "title": "产品形态已按手机、比赛演示、农业局工作站和合作社边缘盒子适配。",
        "subtitle": "不仅能跑在开发电脑上，也能进入田间、培训会和农业局业务场景。",
        "devices": [
            {"title": "手机 PWA", "body": "农户田间使用，同网访问并添加到主屏幕。", "icon": "Smartphone", "color": "#2F7D52", "fill": "#EEF6EA"},
            {"title": "比赛笔记本", "body": "双击启动，现场真实模型问答和证据链演示。", "icon": "Bot", "color": "#416F9F", "fill": "#EAF0F7"},
            {"title": "农业局工作站", "body": "长期运行、导入政策和主体台账、生成报告。", "icon": "Database", "color": "#B6852D", "fill": "#F7F0DF"},
            {"title": "边缘盒子", "body": "接气象站、电子秤、摄像头和二维码溯源。", "icon": "RadioTower", "color": "#8A5132", "fill": "#F2E0D8"},
        ],
    },
    {
        "slideNo": 11,
        "layout": "ip",
        "kicker": "IP & MOAT",
        "title": "专利、软著、数据包和本地场景共同形成可防守的交付壁垒。",
        "subtitle": "不是一次性 demo，而是可以持续沉淀地区农业知识资产的软件产品。",
        "rings": [
            {"title": "专利", "body": "多源证据对象与农业经营生成方法", "color": "#2F7D52", "fill": "#EEF6EA"},
            {"title": "软著", "body": "AgriKB V1.0 软件实现与界面流程", "color": "#416F9F", "fill": "#EAF0F7"},
            {"title": "数据包", "body": "句容政策、台湾样板、农业开放知识", "color": "#B6852D", "fill": "#F7F0DF"},
            {"title": "渠道", "body": "农业局、合作社、农企、电商助农接入", "color": "#8A5132", "fill": "#F2E0D8"},
            {"title": "模型", "body": "Kimi/本地模型双后台，支持私有化", "color": "#2F7D52", "fill": "#FFFFFF"},
        ],
    },
    {
        "slideNo": 12,
        "layout": "final",
        "kicker": "WHY WE WIN",
        "title": "奔着第一名去：用真实软件证明数智信息能长到新农人产业里。",
        "subtitle": "评委看到的不只是概念，而是一套已经能启动、能问答、能导入、能部署、能申报的产品。",
        "rows": [
            {"left": "赛道贴合", "right": "同时命中数智信息技术与新农人，技术与产业两端都成立。", "color": "#2F7D52"},
            {"left": "现场可信", "right": "真实模型调用、联网搜索、证据链展开，避免固定话术演示。", "color": "#416F9F"},
            {"left": "落地明确", "right": "江苏句容场景 + 台湾数据样板 + 农业局/农企/农户三类用户。", "color": "#B6852D"},
            {"left": "商业闭环", "right": "政府项目、企业数据服务、新农人工具包与培训服务可组合收费。", "color": "#8A5132"},
            {"left": "可复制", "right": "地区政策包、产业数据包、模型后台和 PWA 部署可迁移到其他县域。", "color": "#2F7D52"},
        ],
    },
]


def write_notes() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "profile-plan.txt").write_text(
        "\n".join(
            [
                "task mode: create",
                "primary deck-profile: product-platform",
                "secondary gates: strategy-leadership, engineering-platform",
                "required proof objects: platform map, product workflow, use case, deployment path, business linkage, IP moat",
                "source policy: local project docs, user-provided competition PDF, WorkBuddy ppt-processing skill notes",
                "brand policy: no unofficial logos; use text, shapes, and generic Lucide icons only",
                "QA gates: 12 slides, varied macro-layouts, no generic feature-card-only deck, evidence-led claims",
            ]
        ),
        encoding="utf-8",
    )
    (WORKSPACE / "source-notes.txt").write_text(
        "\n".join(
            [
                "Sources used:",
                "- AgriKB local project: docs/COMPETITION_FIRST_PRIZE_PLAN.md, docs/DUAL_TRACK_POSITIONING.md, web UI files.",
                "- Competition PDF brief rendered from E:/Backup/6797937030893568.pdf: 2026 句容市“福地青年英才”创业大赛.",
                "- Knowledge base materials: AGROVOC, Crop Ontology, Google Earth Engine agriculture catalog, Taiwan agriculture open data and COA_OpenData.",
                "- Local WorkBuddy reference: C:/Users/weiku/Desktop/workbuddy-skills/ppt-processing/SKILL.md and scripts.",
                "",
                "Identity assets: no official logos embedded; generic Lucide icons only.",
            ]
        ),
        encoding="utf-8",
    )
    (WORKSPACE / "claim-spine.txt").write_text(
        "\n".join(
            [
                "Thesis: AgriKB wins by proving that 数智信息技术 can directly solve 新农人经营 decisions in a deployable product.",
                "Audience: competition judges, agriculture bureau leaders, local partners, new-farmer representatives.",
                "Arc: dual-track fit -> pain -> product loop -> technical architecture -> data evidence -> Jurong use case -> demo -> business -> deployment -> IP -> why win.",
                "",
                *[f"{s['slideNo']:02d}. {s.get('title', '')}" for s in SLIDES],
            ]
        ),
        encoding="utf-8",
    )
    (WORKSPACE / "design-system.txt").write_text(
        "\n".join(
            [
                "Slide size: 1280x720.",
                "Typography: Microsoft YaHei for Chinese clarity; bold title hierarchy; no tiny core text.",
                "Palette: field paper base, agricultural green, policy blue, market ochre, soil clay.",
                "Visual grammar: flat bands, rectangular evidence objects, field-row footer, generic line icons.",
                "Banned motifs: unofficial logos, decorative blobs/orbs, generic SaaS card grids.",
            ]
        ),
        encoding="utf-8",
    )
    (WORKSPACE / "contact-sheet-plan.txt").write_text(
        "\n".join(
            [
                "Macro-layout rhythm:",
                "1 cover field map + metrics",
                "2 dual-lane comparison",
                "3 pain cards + breakthrough strip",
                "4 horizontal workflow",
                "5 architecture bands",
                "6 evidence hub",
                "7 scenario map + ladder",
                "8 UI demo mock",
                "9 business roles",
                "10 deployment devices",
                "11 IP moat rings",
                "12 judge-fit matrix",
            ]
        ),
        encoding="utf-8",
    )


def write_slides() -> None:
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    LAYOUT_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (SLIDES_DIR / "helpers.mjs").write_text(HELPERS.strip() + "\n", encoding="utf-8")
    for slide in SLIDES:
        num = slide["slideNo"]
        module = (
            'import { buildSpecSlide } from "./helpers.mjs";\n\n'
            f"const spec = {json.dumps(slide, ensure_ascii=False, indent=2)};\n\n"
            f"export async function slide{num:02d}(presentation, ctx) {{\n"
            "  return buildSpecSlide(presentation, ctx, spec);\n"
            "}\n"
        )
        (SLIDES_DIR / f"slide-{num:02d}.mjs").write_text(module, encoding="utf-8")


def main() -> None:
    write_notes()
    write_slides()
    print(
        json.dumps(
            {
                "workspace": str(WORKSPACE),
                "slides_dir": str(SLIDES_DIR),
                "preview_dir": str(PREVIEW_DIR),
                "layout_dir": str(LAYOUT_DIR),
                "output_dir": str(OUTPUT_DIR),
                "slide_count": len(SLIDES),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
