import fs from "node:fs/promises";
import fss from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourceSlidesDir = path.join(projectRoot, "outputs", "manual-20260523-agrikb", "presentations", "agrikb-first-prize", "slides");
const workspace = path.join(
  projectRoot,
  "outputs",
  "manual-20260523-agrikb-function-screenshots",
  "presentations",
  "agrikb-function-screenshots",
);
const slidesDir = path.join(workspace, "slides");
const previewDir = path.join(workspace, "preview");
const layoutDir = path.join(workspace, "layout", "final");
const screenshotDir = path.join(workspace, "assets", "function-screenshots");
const deliverableDir = path.join(projectRoot, "deliverables", "AgriKB_DualTrack_FirstPrize_Materials_20260523");
const finalPptx = path.join(deliverableDir, "AgriKB_数智新农人经营中枢_参赛路演PPT.pptx");
let copyPptx = path.join(deliverableDir, "AgriKB_数智新农人经营中枢_参赛路演PPT_含功能测试截图.pptx");
const backupPptx = path.join(deliverableDir, "AgriKB_数智新农人经营中枢_参赛路演PPT_原版备份.pptx");
const buildScript = process.env.AGRIKB_PRESENTATION_BUILD_SCRIPT || "";
const nodeExe = process.env.AGRIKB_NODE_EXE || process.execPath;

const functions = [
  ["digital", "数智信息", "RAG、知识图谱、实时数据与模型决策"],
  ["new_farmer", "新农人经营", "经营判断、采收销售、政策申报"],
  ["bureau", "农业局治理", "数据治理、产业扶持、培训报告"],
  ["company", "农业企业", "溯源、市场、供应链与电商渠道"],
  ["farmer_today", "今天怎么干", "农民一键获得今日经营清单"],
  ["farmer_sell", "东西卖给谁", "询价、渠道、收购和电商建议"],
  ["farmer_subsidy", "能领啥补贴", "用大白话匹配政策和材料"],
  ["farmer_risk", "天气有没有风险", "天气、病虫害、运输和采收风险"],
  ["policy", "新农人政策", "政策申报、培训补贴、创业扶持"],
  ["platform", "数智中台", "知识库、模型、证据链与 PWA 部署"],
  ["intelligence", "资讯聚合", "政策新闻、气象预警、市场信号与农技咨询聚合"],
  ["benchmark", "竞品对标", "对标优秀农业类 APP/平台并形成产品强化建议"],
  ["competition", "创业大赛", "答辩要点、评分亮点、演示路径"],
  ["market", "农产品行情", "市场收购、电商助农、经营判断"],
  ["weather", "农业气象", "当地气象、环境、采收和病虫害风险"],
  ["traceability", "质量溯源", "主体、地块、批次、认证、二维码"],
  ["crop", "作物本体", "AGROVOC、Crop Ontology、作物性状关系"],
];

function esc(value) {
  return JSON.stringify(value);
}

async function copyDir(src, dest) {
  await fs.rm(dest, { recursive: true, force: true });
  await fs.mkdir(dest, { recursive: true });
  const entries = await fs.readdir(src, { withFileTypes: true });
  for (const entry of entries) {
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) await copyDir(from, to);
    else await fs.copyFile(from, to);
  }
}

function screenshotPath(index, id) {
  return path.join(screenshotDir, `${String(index + 1).padStart(2, "0")}_${id}.png`).replaceAll("\\", "\\\\");
}

function commonHelpers() {
  return `
const C = {
  paper: "#F7F5EC",
  ink: "#17211D",
  muted: "#63716A",
  green: "#2F7D52",
  deepGreen: "#1F5137",
  ochre: "#B6852D",
  blue: "#416F9F",
  line: "#D7DFCF",
  field: "#E7F0DB",
  white: "#FFFFFF"
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
    fontSize: opts.size ?? 20,
    color: opts.color ?? C.ink,
    bold: opts.bold ?? false,
    typeface: opts.face ?? "Microsoft YaHei",
    align: opts.align ?? "left",
    valign: opts.valign ?? "top",
    fill: opts.fill ?? "#00000000",
    line: { style: "solid", fill: "#00000000", width: 0 },
    insets: opts.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
    name: opts.name
  });
}

function base(ctx, slide, kicker, slideNo) {
  shape(ctx, slide, 0, 0, 1280, 720, C.paper, C.paper, 0, "background");
  shape(ctx, slide, 54, 42, 42, 4, C.green, C.green, 0, "kicker-marker");
  text(ctx, slide, kicker, 106, 32, 620, 24, { size: 13, color: C.green, bold: true, name: "kicker-label" });
  text(ctx, slide, String(slideNo), 1190, 36, 44, 24, { size: 12, color: C.muted, align: "right" });
  text(ctx, slide, "AgriKB 数智新农人经营中枢 | 功能入口自动化测试截图", 54, 686, 540, 22, { size: 11, color: C.muted });
}
`;
}

function overviewModule() {
  const cards = functions
    .map(([id, label, note], index) => {
      const col = index % 6;
      const row = Math.floor(index / 6);
      const x = 42 + col * 200;
      const y = 158 + row * 158;
      return `
  shape(ctx, slide, ${x}, ${y}, 180, 132, C.white, C.line, 1);
  await ctx.addImage(slide, { path: "${screenshotPath(index, id)}", x: ${x + 9}, y: ${y + 10}, w: 162, h: 78, fit: "cover", alt: ${esc(label + " screenshot")} });
  text(ctx, slide, ${esc(`${String(index + 1).padStart(2, "0")} ${label}`)}, ${x + 9}, ${y + 94}, 162, 18, { size: 11.2, bold: true, color: C.green, align: "center" });
  text(ctx, slide, ${esc(note)}, ${x + 10}, ${y + 112}, 160, 14, { size: 7.5, color: C.muted, align: "center" });
`;
    })
    .join("\n");
  return `import { } from "./helpers.mjs";
${commonHelpers()}

export async function slide17(presentation, ctx) {
  const slide = presentation.slides.add();
  base(ctx, slide, "FUNCTION TEST OVERVIEW", 17);
  text(ctx, slide, "17 个功能入口均已逐项点选，并形成可验收界面截图。", 54, 76, 980, 46, { size: 30, bold: true, color: C.ink });
  text(ctx, slide, "每个截图都展示：点击入口、问答区返回测试信息、/api/query 参数包含联网搜索与区域情报。", 58, 124, 1040, 24, { size: 15, color: C.muted });
${cards}
  return slide;
}
`;
}

function businessModule(slideNo) {
  if (slideNo === 13) {
    return `import { } from "./helpers.mjs";
${commonHelpers()}

export async function slide13(presentation, ctx) {
  const slide = presentation.slides.add();
  base(ctx, slide, "MARKET BENCHMARK", 13);
  text(ctx, slide, "优秀农业类 APP 的能力正在分化，AgriKB 要做“县域经营智能体”。", 54, 76, 1060, 50, { size: 30, bold: true, color: C.ink });
  text(ctx, slide, "对标 FieldView、John Deere Operations Center、CropX、Agworld、OneSoil、EOSDA、惠农网、一亩田、农技耘等平台，差异化不在单点工具，而在本地资讯聚合、政策市场经营判断和农业局治理闭环。", 58, 124, 1100, 42, { size: 15, color: C.muted });
  const rows = [
    ["遥感/农情", "FieldView / OneSoil / EOSDA", "偏作物监测、地块地图、长势分析", "AgriKB叠加政策、市场、收购和本地经营判断"],
    ["农机/作业", "John Deere Operations Center", "强在设备数据、作业协同和农场运营", "AgriKB面向县域主体台账和农业局项目治理"],
    ["农技/管理", "CropX / Agworld", "强在农艺建议、作业记录、投入品管理", "AgriKB把咨询、知识库、证据链和本地政策一起回答"],
    ["交易/渠道", "惠农网 / 一亩田", "强在农产品撮合、批发交易、渠道流量", "AgriKB补足经营决策：什么时候卖、卖给谁、申报什么扶持"]
  ];
  ["能力维度", "代表平台", "市场强项", "AgriKB商业卡位"].forEach((h, i) => text(ctx, slide, h, 78 + i * 290, 196, 260, 24, { size: 14, bold: true, color: C.green, align: "center" }));
  rows.forEach((r, idx) => {
    const y = 232 + idx * 88;
    shape(ctx, slide, 58, y, 1162, 70, idx % 2 ? "#FFFFFF" : "#F4F8F0", C.line, 1);
    r.forEach((cell, i) => text(ctx, slide, cell, 78 + i * 290, y + 12, 252, 44, { size: i === 0 ? 15 : 12.5, bold: i === 0, color: i === 3 ? C.deepGreen : C.ink, align: "center", valign: "middle" }));
  });
  shape(ctx, slide, 90, 606, 1100, 48, "#EEF6EA", "#C9DABF", 1);
  text(ctx, slide, "商业表达：不是再做一个农业 App，而是把县域农业“信息、判断、申报、交易、监管”聚合成可部署的 AI 经营中枢。", 118, 620, 1040, 20, { size: 17, bold: true, color: C.deepGreen, align: "center" });
  return slide;
}
`;
  }
  if (slideNo === 14) {
    return `import { } from "./helpers.mjs";
${commonHelpers()}

export async function slide14(presentation, ctx) {
  const slide = presentation.slides.add();
  base(ctx, slide, "INTELLIGENCE ENGINE", 14);
  text(ctx, slide, "资讯搜集不只是搜索链接，而是把信息变成经营动作。", 54, 76, 1060, 48, { size: 32, bold: true, color: C.ink });
  text(ctx, slide, "AgriKB 的咨询/资讯聚合链路：多源采集 → 可信度标注 → 语义归类 → 地区适配 → 模型推理 → 证据链隐藏展开。", 58, 124, 1060, 26, { size: 16, color: C.muted });
  const nodes = [
    ["政策新闻", "农业农村、地方政府、创业扶持、补贴申报"],
    ["气象环境", "句容天气、灾害预警、采收窗口、病虫害风险"],
    ["市场渠道", "收购信息、电商助农、批发平台、供需变化"],
    ["知识本体", "AGROVOC、Crop Ontology、台湾农业开放数据"],
    ["经营判断", "卖不卖、采不采、申不申、投不投"]
  ];
  nodes.forEach((n, i) => {
    const x = 70 + i * 232;
    shape(ctx, slide, x, 242, 178, 118, i === 4 ? "#EAF0F7" : "#FFFFFF", i === 4 ? C.blue : C.green, 1.2);
    text(ctx, slide, n[0], x + 14, 262, 150, 24, { size: 19, bold: true, color: i === 4 ? C.blue : C.green, align: "center" });
    text(ctx, slide, n[1], x + 16, 302, 146, 42, { size: 12.5, color: C.ink, align: "center" });
    if (i < nodes.length - 1) text(ctx, slide, "→", x + 184, 284, 34, 30, { size: 25, bold: true, color: C.ochre, align: "center" });
  });
  const outputs = [
    ["给农民", "今日经营清单、采收销售建议、政策匹配材料"],
    ["给农业局", "主体筛选、产业扶持、项目台账、审计证据链"],
    ["给企业", "采购窗口、产地合作、质量溯源、渠道判断"]
  ];
  outputs.forEach((o, i) => {
    const x = 86 + i * 380;
    shape(ctx, slide, x, 438, 320, 112, "#F7F5EC", C.line, 1);
    text(ctx, slide, o[0], x + 22, 462, 276, 24, { size: 20, bold: true, color: C.deepGreen, align: "center" });
    text(ctx, slide, o[1], x + 28, 502, 264, 30, { size: 13.5, color: C.ink, align: "center" });
  });
  text(ctx, slide, "落地要点：默认隐藏证据链，前台显示可执行判断；需要审计/汇报时一键展开来源、图谱和会话证据。", 128, 610, 1024, 28, { size: 18, bold: true, color: C.ink, align: "center" });
  return slide;
}
`;
  }
  if (slideNo === 15) {
    return `import { } from "./helpers.mjs";
${commonHelpers()}

export async function slide15(presentation, ctx) {
  const slide = presentation.slides.add();
  base(ctx, slide, "BUSINESS MODEL", 15);
  text(ctx, slide, "商业化不是卖问答，而是卖县域农业数字经营能力。", 54, 76, 1060, 50, { size: 32, bold: true, color: C.ink });
  const roles = [
    ["政府/农业局", "项目建设费 + 年度运维\\n产业报告、主体台账、扶持项目筛选", C.green, "#EEF6EA"],
    ["农业企业", "数据服务 + 供应链协作\\n产地合作、质量溯源、采购窗口", C.blue, "#EAF0F7"],
    ["新农人/合作社", "工具包 + 培训营\\n经营问答、申报材料、销售渠道", C.ochre, "#F7F0DF"]
  ];
  roles.forEach((r, i) => {
    const x = 82 + i * 384;
    shape(ctx, slide, x, 186, 326, 196, r[3], r[2], 1.3);
    text(ctx, slide, r[0], x + 24, 220, 278, 30, { size: 23, bold: true, color: r[2], align: "center" });
    text(ctx, slide, r[1], x + 30, 278, 266, 70, { size: 15, color: C.ink, align: "center" });
  });
  const kpis = [
    ["试点指标", "50+主体", "句容新农人/合作社/企业样板"],
    ["数据指标", "17入口", "政策、市场、气象、溯源、竞品对标"],
    ["交付指标", "PWA+本地部署", "电脑/手机/局域网/演示环境"]
  ];
  kpis.forEach((k, i) => {
    const x = 126 + i * 340;
    shape(ctx, slide, x, 462, 274, 96, "#FFFFFF", C.line, 1);
    text(ctx, slide, k[1], x + 22, 478, 230, 30, { size: 26, bold: true, color: i === 1 ? C.blue : C.green, align: "center" });
    text(ctx, slide, k[0], x + 22, 514, 230, 18, { size: 12, bold: true, color: C.muted, align: "center" });
    text(ctx, slide, k[2], x + 20, 536, 234, 18, { size: 11.5, color: C.ink, align: "center" });
  });
  text(ctx, slide, "第一名表达：技术完整、场景真实、客户清晰、交付可运行、后续可规模复制。", 170, 614, 940, 30, { size: 22, bold: true, color: C.deepGreen, align: "center" });
  return slide;
}
`;
  }
  return `import { } from "./helpers.mjs";
${commonHelpers()}

export async function slide16(presentation, ctx) {
  const slide = presentation.slides.add();
  base(ctx, slide, "DEMO STORYLINE", 16);
  text(ctx, slide, "现场演示按“资讯聚合 → 经营判断 → 证据展开 → 渠道动作”推进。", 54, 76, 1100, 48, { size: 31, bold: true, color: C.ink });
  const steps = [
    ["1. 点资讯聚合", "汇总政策、新闻、天气、市场、渠道"],
    ["2. 点农业气象/行情", "生成今日采收销售与风险判断"],
    ["3. 点新农人政策", "输出申报对象、材料和下一步动作"],
    ["4. 展开证据链", "让评委看到来源、图谱和推理关系"],
    ["5. 点竞品对标", "说明比单点农业APP更适合县域落地"]
  ];
  steps.forEach((s, i) => {
    const y = 178 + i * 84;
    shape(ctx, slide, 106, y, 1068, 58, i % 2 ? "#FFFFFF" : "#F4F8F0", i === 4 ? C.blue : C.green, 1.1);
    text(ctx, slide, s[0], 132, y + 14, 240, 26, { size: 18, bold: true, color: i === 4 ? C.blue : C.green });
    text(ctx, slide, s[1], 390, y + 15, 720, 24, { size: 16, color: C.ink });
  });
  shape(ctx, slide, 138, 624, 1004, 34, "#EEF6EA", "#C9DABF", 1);
  text(ctx, slide, "演示目标：让评委看到它不是静态 PPT，也不是通用聊天，而是一个面向农民、农业局、企业都能点进去用的数智农业产品。", 158, 632, 964, 18, { size: 14.5, bold: true, color: C.deepGreen, align: "center" });
  return slide;
}
`;
}

function screenshotModule(index, id, label, note) {
  const slideNo = 18 + index;
  return `import { } from "./helpers.mjs";
${commonHelpers()}

export async function slide${String(slideNo).padStart(2, "0")}(presentation, ctx) {
  const slide = presentation.slides.add();
  base(ctx, slide, "FUNCTION TEST ${String(index + 1).padStart(2, "0")}", ${slideNo});
  text(ctx, slide, ${esc(`${String(index + 1).padStart(2, "0")} ${label}：点击后可以实时进入并返回信息。`)}, 54, 72, 1048, 42, { size: 28, bold: true, color: C.ink });
  text(ctx, slide, ${esc(note)}, 58, 114, 940, 24, { size: 15, color: C.muted });
  shape(ctx, slide, 86, 148, 1108, 498, "#FFFFFF", C.line, 1.1, "screenshot-frame");
  await ctx.addImage(slide, { path: "${screenshotPath(index, id)}", x: 102, y: 162, w: 1076, h: 468, fit: "contain", alt: ${esc(label + " feature test screenshot")} });
  shape(ctx, slide, 84, 650, 1112, 28, "#EEF6EA", "#C9DABF", 1);
  text(ctx, slide, "验收点：入口是 button；点击发起 /api/query；请求带 web_search=true、regional_intelligence=true、top_k=7；问答区出现对应返回。", 100, 656, 1080, 18, { size: 12.5, color: C.deepGreen, align: "center" });
  return slide;
}
`;
}

async function main() {
  await fs.mkdir(workspace, { recursive: true });
  await fs.writeFile(
    path.join(workspace, "profile-plan.txt"),
    [
      "task mode: targeted-edit-media / appendix insertion",
      "primary profile: product-platform",
      "proof object: one automated UI screenshot for each AgriKB feature entry",
      "QA gate: every screenshot shows a clicked function and rendered Q&A response",
    ].join("\n"),
    "utf8",
  );
  await fs.writeFile(
    path.join(workspace, "source-notes.txt"),
    "Screenshots are generated from local AgriKB UI at http://127.0.0.1:8010/ui/ using the project test harness.\n",
    "utf8",
  );
  await copyDir(sourceSlidesDir, slidesDir);
  for (const slideNo of [13, 14, 15, 16]) {
    await fs.writeFile(path.join(slidesDir, `slide-${String(slideNo).padStart(2, "0")}.mjs`), businessModule(slideNo), "utf8");
  }
  await fs.writeFile(path.join(slidesDir, "slide-17.mjs"), overviewModule(), "utf8");
  for (let index = 0; index < functions.length; index += 1) {
    const [id, label, note] = functions[index];
    const slideNo = 18 + index;
    await fs.writeFile(path.join(slidesDir, `slide-${String(slideNo).padStart(2, "0")}.mjs`), screenshotModule(index, id, label, note), "utf8");
  }

  if (fss.existsSync(finalPptx) && !fss.existsSync(backupPptx)) {
    await fs.copyFile(finalPptx, backupPptx);
  }

  if (!buildScript || !fss.existsSync(buildScript)) {
    throw new Error("Set AGRIKB_PRESENTATION_BUILD_SCRIPT to the local build_artifact_deck.mjs path before rebuilding the screenshot deck.");
  }

  const result = spawnSync(
    nodeExe,
    [
      buildScript,
      "--workspace",
      workspace,
      "--slides-dir",
      slidesDir,
      "--out",
      finalPptx,
      "--preview-dir",
      previewDir,
      "--layout-dir",
      layoutDir,
      "--slide-count",
      "34",
    ],
    {
      cwd: projectRoot,
      env: { ...process.env, HOME: process.env.HOME || process.env.USERPROFILE || projectRoot },
      encoding: "utf8",
      stdio: "pipe",
    },
  );
  if (result.status !== 0) {
    console.error(result.stdout);
    console.error(result.stderr);
    process.exit(result.status || 1);
  }
  try {
    await fs.copyFile(finalPptx, copyPptx);
  } catch (error) {
    if (error && ["EBUSY", "EPERM", "EACCES"].includes(error.code)) {
      copyPptx = path.join(deliverableDir, "AgriKB_数智新农人经营中枢_商业增强路演PPT_含功能测试截图_最新版.pptx");
      await fs.copyFile(finalPptx, copyPptx);
    } else {
      throw error;
    }
  }
  console.log(JSON.stringify({ finalPptx, copyPptx, workspace, previewDir }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
