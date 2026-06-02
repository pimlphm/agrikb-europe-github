# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "AgriKB_DualTrack_FirstPrize_Materials_20260523"
TODAY = "2026-05-25"

GREEN = "1F6B45"
DEEP = "153B2B"
GOLD = "A87224"
RED = "B34536"
INK = "1F2A24"
MUTED = "5F6E65"


def clean(text: str) -> str:
    result = str(text)
    for bad in ("".join(["南", "京", "句", "容"]), "".join(["江", "宁", "区"])):
        result = result.replace(bad, "江苏句容")
    return (
        result
        .replace("Kimi 智能问答", "新农人助手")
        .replace("kimi-for-coding", "新农人助手模型")
    )


def set_run_font(run, size: float | None = None, bold: bool | None = None, color: str | None = None) -> None:
    run.font.name = "Microsoft YaHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def style_doc(doc: Document, title: str) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(1.7)
    section.bottom_margin = Cm(1.7)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    normal = doc.styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.18
    normal.paragraph_format.space_after = Pt(5)
    for name, size, color in [("Heading 1", 16, GREEN), ("Heading 2", 13, DEEP), ("Heading 3", 11.5, GOLD)]:
        style = doc.styles[name]
        style.font.name = "Microsoft YaHei"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
    doc.core_properties.title = clean(title)
    doc.core_properties.subject = "AgriKB 数智新农人经营中枢交付材料增强版"
    doc.core_properties.author = "AgriKB Project"
    doc.core_properties.comments = "Generated on 2026-05-25. API keys are intentionally not printed in document body."


def add_cover(doc: Document, title: str, subtitle: str, version: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(clean(title))
    set_run_font(r, 24, True, DEEP)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(clean(subtitle))
    set_run_font(r, 13, False, MUTED)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(clean(version))
    set_run_font(r, 11, True, GOLD)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("适用场景：江苏句容样板、县域农业局、合作社、家庭农场、收购企业与新农人创业团队")
    set_run_font(r, 10.5, False, INK)
    doc.add_paragraph()


def add_paragraph(doc: Document, text: str, bold: bool = False) -> None:
    p = doc.add_paragraph()
    r = p.add_run(clean(text))
    set_run_font(r, 10.5, bold, INK)


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        r = p.add_run(clean(item))
        set_run_font(r, 10.5, False, INK)


def add_numbers(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Number")
        r = p.add_run(clean(item))
        set_run_font(r, 10.5, False, INK)


def add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(clean(header))
        set_run_font(r, 9.5, True, DEEP)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            p = cells[i].paragraphs[0]
            r = p.add_run(clean(value))
            set_run_font(r, 9.2, False, INK)


def render_doc(filename: str, title: str, subtitle: str, sections: list[dict]) -> Path:
    doc = Document()
    style_doc(doc, title)
    add_cover(doc, title, subtitle, f"增强版 V1.3 / {TODAY}")
    for section in sections:
        doc.add_heading(clean(section["title"]), level=1)
        for para in section.get("paragraphs", []):
            add_paragraph(doc, para)
        if section.get("bullets"):
            add_bullets(doc, section["bullets"])
        if section.get("numbers"):
            add_numbers(doc, section["numbers"])
        for table in section.get("tables", []):
            add_table(doc, table["headers"], table["rows"])
    path = OUT / filename
    doc.save(path)
    return path


def render_md(filename: str, title: str, subtitle: str, sections: list[dict]) -> Path:
    lines = [f"# {clean(title)}", "", clean(subtitle), "", f"版本：增强版 V1.3 / {TODAY}", ""]
    for section in sections:
        lines += [f"## {clean(section['title'])}", ""]
        for para in section.get("paragraphs", []):
            lines += [clean(para), ""]
        for item in section.get("bullets", []):
            lines.append(f"- {clean(item)}")
        if section.get("bullets"):
            lines.append("")
        for i, item in enumerate(section.get("numbers", []), start=1):
            lines.append(f"{i}. {clean(item)}")
        if section.get("numbers"):
            lines.append("")
        for table in section.get("tables", []):
            headers = [clean(x) for x in table["headers"]]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for row in table["rows"]:
                lines.append("| " + " | ".join(clean(x).replace("\n", "<br>") for x in row) + " |")
            lines.append("")
    path = OUT / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def usage_sections() -> list[dict]:
    return [
        {
            "title": "一键启动与手机测试",
            "paragraphs": [
                "本说明面向可信电脑交付包。用户解压后不需要重新配置开发环境，先运行启动脚本，再通过电脑浏览器或同一局域网手机访问系统。默认场景为江苏句容，可在设置、天气、地图与市场模块中切换位置。",
            ],
            "numbers": [
                "解压 `AgriKB_TrustedPC_OneClick_20260525.zip`，进入 `AgriKB_TrustedPC_OneClick` 文件夹。",
                "双击 `一键启动AgriKB_可信电脑.bat`，等待浏览器打开首页。",
                "需要手机测试时打开“设置”，在“手机端可扫码”区域扫描二维码；如果酒店 Wi-Fi 阻断互访，改用手机热点或运行 `一键修复手机扫码访问.bat`。",
                "需要更换模型或 API key 时进入“设置”，更新新农人助手模型配置并保存。",
                "交付结束或迁移前可运行 `一键卸载AgriKB.bat` 清理本项目创建的后台进程、临时文件和便携环境。",
            ],
        },
        {
            "title": "农户、农业局、企业三类用户怎么用",
            "tables": [
                {
                    "headers": ["用户", "第一步", "重点查看", "形成结果"],
                    "rows": [
                        ["农户/新农人", "从今日安排、销售渠道、补贴申报、天气风险进入", "一句话建议、价格表、天气滑页、路线和收购渠道", "今天该干什么、卖给谁、是否抢采、防潮和物流怎么安排"],
                        ["农业局/园区", "进入政策解读、资讯聚合、质量溯源和数智中台", "本地部门入口、热线、政策窗口、产业热点和舆情线索", "政策宣传、申报辅导、风险预警、产业扶持研判"],
                        ["收购企业/合作社", "进入市场行情、目标市场、路线规划和供应商聚合", "产地与目标市场价格、沿途散货建议、冷链与配送候选", "锁定货源、安排分级包装、减少损耗、形成采购计划"],
                    ],
                }
            ],
        },
        {
            "title": "核心界面与功能入口",
            "bullets": [
                "问答悬浮窗位于屏幕中央偏下，支持回车发送、文件上传、联网搜索开关、模型配置入口和回答下方小喇叭朗读。",
                "证据链、知识树和规则解释默认折叠，用户需要时再展开，避免首页堆满技术信息。",
                "政策、市场、气象、收购和路线会在回答中自动聚合，优先给出能执行的一句话建议，再给出分步骤判断。",
                "市场与农资查询支持下拉选择和手动输入；查询后会自动生成小结与实时建议，并沉淀到本地 ontology 文件夹。",
                "地图选点后会把产地和目标市场自动更新到文本框，路线模块给出行驶方向、物流建议和沿途散货销售判断。",
                "天气模块默认江苏句容，并提供当天、明天、三天、五到十天、十五天和三周趋势的滑页视图。",
                "资讯聚合采用类似头条流的动态刷新方式，围绕农业创业、科技农业、青年人才、招商孵化、新媒体助农、政策资金六类滚动展示。",
            ],
        },
        {
            "title": "文件、设置与数据沉淀",
            "bullets": [
                "“文件”用于导入政策文件、收购表、价格表、图片和 PDF，也可导出当前问答、规则解读和材料摘要。",
                "“设置”用于切换联网、更新 API key、选择模型、查看手机扫码地址、配置默认产地和目标市场。",
                "所有用户主动查询形成的品类、价格、规则、证据摘要会按作物、农资、政策、市场、气象、物流等 ontology 目录组织，便于下次召回。",
                "后台保留 AGROVOC、Crop Ontology、台湾农业开放数据、Google Earth Engine 农业标签数据和江苏句容本地报道支撑库。",
            ],
        },
        {
            "title": "常见问题",
            "bullets": [
                "手机打不开：大概率是酒店或公共 Wi-Fi 开启客户端隔离。优先换手机热点或路由器，再运行防火墙修复脚本。",
                "模型超时：系统已将新农人助手模型调用超时放宽，并启用压缩重试；若网络波动，前端会返回可用的本地证据建议。",
                "页面旧样式：刷新时使用 `?v=20260525agri93`，或清理浏览器缓存。",
                "不要公开外发 `.env`，其中包含可信电脑专用的模型配置。",
            ],
        },
    ]


def product_sections() -> list[dict]:
    return [
        {
            "title": "产品定位",
            "paragraphs": [
                "AgriKB 数智新农人经营中枢是一套面向县域农业经营的 AI 应用软件。它不是单一问答网页，而是把农业知识图谱、实时资讯、政策申报、行情价格、气象风险、物流路线、IOT 监测和新农人创业服务合成一个可交付系统。",
                "本版本以江苏句容为应用样板，同时用台湾农业开放数据、AGROVOC、Crop Ontology 等公开知识源作为标准化底座，形成“本地场景 + 开放标准 + 实时模型分析”的双赛道能力。",
            ],
        },
        {
            "title": "核心价值",
            "tables": [
                {
                    "headers": ["痛点", "产品能力", "用户收益"],
                    "rows": [
                        ["政策多、窗口散、材料难懂", "政策雷达、部门入口、材料清单、AI 解读", "知道能不能申、先准备什么、找哪个入口"],
                        ["行情和收购信息不透明", "农产品价格表、目标市场、收购与电商渠道聚合", "减少错卖、晚卖和低价出货"],
                        ["天气和生产动作脱节", "多时间段天气滑页、抢采/防潮/病虫害提醒", "把天气风险转化成今天能执行的动作"],
                        ["知识图谱太复杂", "因果图、俗语化总领、规则气泡解释", "非专业用户也能看出利害关系"],
                        ["AI 回答容易脱离本地", "IP/手动位置、江苏句容样板、本地报道和部门入口", "回答跟本地产业、市场和物流相连"],
                    ],
                }
            ],
        },
        {
            "title": "高级技术架构",
            "tables": [
                {
                    "headers": ["层级", "实现", "说明"],
                    "rows": [
                        ["前端交互层", "PWA + 中央悬浮问答 + 设置/文件/地图/天气/行情模块", "农户少操作，农业局和企业可深挖证据"],
                        ["模型服务层", "新农人助手模型层 + 本地备用模型", "优先真实调用云端模型，异常时保留本地证据回复能力"],
                        ["RAG 检索层", "向量召回、关键词召回、实时 Web 情报和本地资料混合排序", "把知识库、政策、市场和新闻统一成证据对象"],
                        ["Ontology 管理层", "作物、性状、市场、政策、物流、气象、规则六类目录", "用户查询和 AI 小结持续沉淀，形成经验资产"],
                        ["RLM 递归推理层", "问题拆解、证据检索、规则校验、追问补全、答案压缩", "从“问一句”到“可执行经营判断”"],
                        ["实时情报层", "天气、价格、新闻、政策、物流和招商人才信息", "滚动刷新，支持打开来源与AI趋势分析"],
                        ["现场感知层", "温湿度、光照、土壤、EC、CO2、摄像头与边缘网关接口", "可连接大棚、仓储、冷链和基地监测屏"],
                    ],
                }
            ],
        },
        {
            "title": "盈利方案",
            "tables": [
                {
                    "headers": ["收入项", "客户", "交付方式", "价值"],
                    "rows": [
                        ["县域部署服务费", "农业农村局、园区、乡镇", "本地化知识库、内网部署、培训和运维", "政策服务、产业监测、项目申报和数据看板"],
                        ["合作社/农企订阅", "合作社、家庭农场、收购企业", "年度账号、行情与渠道模块、采购协同", "降低信息成本和交易损耗"],
                        ["IOT 集成与硬件适配", "设施农业基地、示范园", "传感器、网关、监测屏和移动端适配", "从看数据升级为看建议"],
                        ["数据与报告服务", "金融、保险、园区招商、供应链企业", "产业趋势报告、风险报告、品类画像", "辅助授信、保险定价和招商筛选"],
                        ["培训和赛事服务", "新农人团队、高校、创业大赛", "路演材料、项目孵化、商业计划书和演示系统", "提升参赛、融资和项目申报成功率"],
                    ],
                }
            ],
        },
        {
            "title": "交付形态",
            "bullets": [
                "比赛路演版：30 页商业路演 PPT、功能截图、操作视频、产品说明、项目介绍、专利和软著材料。",
                "可信电脑版：包含便携 Python、依赖包、知识库、模型配置、启动脚本、测试脚本和卸载脚本。",
                "手机访问版：局域网二维码、PWA 轻量页面、移动端测试说明和 Wi-Fi 障碍处理脚本。",
                "现场硬件版：接入大棚 IOT、基地摄像头、环境监测、冷库温控和运输节点数据。",
            ],
        },
    ]


def patent_sections() -> list[dict]:
    return [
        {
            "title": "建议专利名称",
            "paragraphs": [
                "一种面向新农人经营决策的农业知识图谱与实时情报融合方法、系统、设备及存储介质。",
            ],
        },
        {
            "title": "摘要",
            "paragraphs": [
                "本发明公开了一种面向新农人经营决策的农业知识图谱与实时情报融合方法、系统、设备及存储介质。该方法获取用户问题、当前位置、目标市场、作物品类、天气、行情、政策、物流、公开知识源和本地经验数据；通过农业 ontology 将作物、性状、观测变量、政策对象、市场主体、路线节点和经营动作标准化；再利用混合检索和 RLM 递归推理生成证据对象、因果规则、风险判断和执行建议。系统支持证据链折叠展示、规则气泡解释、用户查询沉淀、实时头条聚合、路线与沿途销售建议、IOT 监测联动以及可信电脑一键部署。",
            ],
        },
        {
            "title": "权利要求书初稿",
            "numbers": [
                "一种农业经营决策生成方法，其特征在于：接收用户问题、产地位置、目标市场、作物或农资品类，并同步获取天气、价格、政策、物流、新闻和本地知识库数据。",
                "根据权利要求1所述的方法，其中将输入数据映射到农业 ontology，形成作物实体、观测变量、阈值、政策对象、市场主体、运输节点和经营动作之间的结构化关系。",
                "根据权利要求1所述的方法，其中通过向量检索、关键词检索、规则检索和实时网络检索生成候选证据对象，并对证据来源、时间、地区、许可和可信度进行标注。",
                "根据权利要求1所述的方法，其中采用 RLM 递归推理流程，将经营问题拆解为政策、市场、气象、生产、物流和风险六类子问题，分别检索、校验、合并后输出分层建议。",
                "根据权利要求4所述的方法，其中答案先输出一句话建议，再输出行动清单、政策判断、市场判断、天气风险、路线物流和证据折叠入口。",
                "根据权利要求1所述的方法，其中用户查询品类后，系统自动将价格、来源、AI 小结、规则解释和操作记录沉淀至本地 ontology 文件夹。",
                "根据权利要求1所述的方法，其中地图选点或手动输入位置后，系统自动更新产地和目标市场文本框，并生成路线、运输时间、冷链或普货建议及沿途散货销售建议。",
                "根据权利要求1所述的方法，其中资讯聚合模块按农业创业、科技农业、青年人才、招商孵化、新媒体助农和政策资金六类动态滚动，并对每类头条生成 AI 趋势分析。",
                "根据权利要求1所述的方法，其中规则知识以因果图、气泡解释和俗语化总领展示，并允许导出为材料或沉淀为本地经验。",
                "一种农业经营决策系统，包括前端交互模块、模型服务模块、混合检索模块、ontology 管理模块、RLM 递归推理模块、实时情报模块、IOT 接入模块和交付部署模块。",
                "根据权利要求10所述的系统，其中 IOT 接入模块可连接大棚温湿度、光照、土壤水分、EC、CO2、摄像头、冷库温控和物流节点数据。",
                "一种电子设备和一种计算机可读存储介质，其上存储有程序，所述程序被处理器执行时实现权利要求1至9任一项所述方法。",
            ],
        },
        {
            "title": "技术方案与实施例",
            "bullets": [
                "实施例一：草莓大棚监测。系统把温湿度、光照、土壤水分、EC 等传感器数据映射到作物本体，判断是否达标，并给出通风、补光、控水、病害预防和采收建议。",
                "实施例二：政策申报。用户输入“能不能申请补贴”，系统结合主体类型、材料清单、政策窗口和部门入口，生成先准备、再申报、后留痕的流程图。",
                "实施例三：行情与收购。用户查询草莓或农资价格，系统获取行情表、相似品类、目标市场和收购渠道，输出议价判断和分级包装建议。",
                "实施例四：两地路线。用户在地图选择产地和目标市场，系统规划路线，结合天气、路况、冷链和沿途消费节点给出配送与散货销售建议。",
                "实施例五：赛事与招商。系统围绕创业大赛主题聚合农业、科技、人才、招商和新媒体信息，形成路演趋势和项目申报建议。",
            ],
        },
        {
            "title": "有益效果",
            "bullets": [
                "把分散的政策、市场、天气和技术知识转化为用户能执行的经营动作。",
                "通过 ontology 管理和用户查询沉淀，使每一次咨询都成为本地农业知识资产。",
                "通过 RLM 递归推理减少固定模板回答，提高复杂农业问题的解释性和一致性。",
                "通过可信电脑一键部署降低县域现场交付门槛，适合比赛演示、农业局试点和合作社使用。",
            ],
        },
    ]


def copyright_sections() -> list[dict]:
    return [
        {
            "title": "软件基本信息",
            "tables": [
                {
                    "headers": ["项目", "内容"],
                    "rows": [
                        ["软件名称", "AgriKB 数智新农人经营中枢软件"],
                        ["版本号", "V1.3"],
                        ["完成日期", TODAY],
                        ["运行环境", "Windows 10/11；Python 3.11；浏览器；可局域网手机访问"],
                        ["应用领域", "智慧农业、农业知识图谱、政策服务、行情咨询、县域新农人创业服务"],
                    ],
                }
            ],
        },
        {
            "title": "主要功能模块",
            "bullets": [
                "新农人助手问答：真实模型调用、联网开关、证据折叠、文件上传、回车发送和回答朗读。",
                "农业知识库：AGROVOC、Crop Ontology、台湾农业开放数据、江苏句容本地资料、用户经验沉淀。",
                "政策雷达：政策解读、申报材料、部门入口、热线和维权服务聚合。",
                "市场与农资：价格表、品类查询、AI 小结、农资咨询和本体文件沉淀。",
                "天气与环境：多时间段天气滑页、城市切换、地图切换和农业风险提醒。",
                "路线与物流：产地和目标市场选择、路线规划、冷链/配送供应商聚合、沿途销售建议。",
                "作物监测：大棚模拟、传感器动画、阈值判断、调整建议和 IOT 接入预留。",
                "设置与文件：API key、模型、联网、导入导出、手机二维码和一键卸载说明。",
            ],
        },
        {
            "title": "技术特点",
            "bullets": [
                "前后端分离架构，后端提供健康检查、问答、天气、市场、资讯、规则解释、文件导入和 TTS 服务。",
                "模型服务层采用新农人助手模型配置，具备超时重试、压缩请求和本地证据兜底机制。",
                "ontology 文件夹按作物、农资、政策、市场、气象、物流和规则组织，支持增量写入和再次召回。",
                "UI 采用面向农户的简约交互，技术证据默认隐藏，深度功能可逐层展开。",
                "交付包包含便携 Python 和依赖，适合可信电脑直接解压运行。",
            ],
        },
        {
            "title": "源程序与材料清单",
            "tables": [
                {
                    "headers": ["目录", "用途"],
                    "rows": [
                        ["src/backend", "后端 API、模型提供者、检索、实时情报和规则服务"],
                        ["src/generation", "回答生成、提示组织、证据压缩和兜底逻辑"],
                        ["web", "前端界面、PWA、样式、服务工作线程和交互脚本"],
                        ["data / knowledge", "知识库索引、公开数据、用户沉淀和本体组织"],
                        ["tools", "下载、索引、截图、PPT、材料刷新和打包脚本"],
                        ["deliverables", "PPT、视频、说明书、专利、软著和交付清单"],
                    ],
                }
            ],
        },
    ]


def project_sections() -> list[dict]:
    return [
        {
            "title": "项目一句话",
            "paragraphs": [
                "AgriKB 用 AI 把政策、行情、天气、收购、物流和作物监测变成新农人每天能执行的经营建议，并把每一次使用沉淀成县域农业知识资产。",
            ],
        },
        {
            "title": "参赛主题契合",
            "bullets": [
                "数智信息：通过实时资讯、模型分析、知识图谱、RLM 递归推理和本地知识沉淀，让农业信息从“能查到”变成“能决策”。",
                "新农人：面向返乡创业、家庭农场、合作社和大学生创业团队，提供政策、经营、渠道、品牌和技术咨询。",
                "江苏句容样板：围绕本地农业、人才、科技、招商、乡村产业和福地青年英才创业大赛主题构建演示场景。",
                "可复制交付：可信电脑一键包、手机扫码、PWA 页面、IOT 接入预留和材料包，适合比赛、试点和商业拓展。",
            ],
        },
        {
            "title": "演示路径",
            "numbers": [
                "首页展示六类头条与 AI 趋势分析，说明系统如何抓取聚合与农业创业相关的信息。",
                "进入作物监测，展示草莓大棚数据、阈值、传感器动画和调整建议。",
                "查询草莓行情，生成价格小结、目标市场建议、收购渠道和本地 ontology 沉淀记录。",
                "打开天气滑页，查看当天到三周的生产风险，说明如何决定抢采、防潮和运输。",
                "进入政策雷达，点击对象、材料、窗口、部门，展示气泡式 AI 解读和导出能力。",
                "打开设置，展示模型配置、联网开关、手机二维码和可信电脑交付能力。",
            ],
        },
        {
            "title": "IOT 与现场连接",
            "tables": [
                {
                    "headers": ["现场", "接入数据", "AI 输出"],
                    "rows": [
                        ["温室大棚", "温湿度、光照、土壤水分、EC、CO2、摄像头", "达标判断、调控动作、病虫害风险和采收建议"],
                        ["仓储冷库", "库温、湿度、开关门、库存批次", "保鲜风险、出库顺序、冷链安排"],
                        ["运输车辆", "GPS、温控、路线、预计到达", "路径调整、沿途散货、目标市场到货窗口"],
                        ["农业局监测屏", "政策申报、价格波动、天气预警、舆情热点", "产业扶持研判、服务对象清单和风险处置优先级"],
                    ],
                }
            ],
        },
        {
            "title": "阶段计划",
            "bullets": [
                "比赛阶段：以江苏句容样板完成路演、手机扫码、PPT 视频和全功能截图演示。",
                "试点阶段：接入真实乡镇、合作社、市场和部门数据，建立 3 到 5 个品类的稳定经营知识包。",
                "商业阶段：形成县域部署、农企订阅、IOT 集成、培训服务和数据报告五类收入。",
                "复制阶段：把 ontology、RLM 和交付脚本迁移到其它县域，实现一地试点、多地复制。",
            ],
        },
    ]


def deployment_sections() -> list[dict]:
    return [
        {
            "title": "可信电脑包内容",
            "bullets": [
                "`AgriKB_TrustedPC_OneClick_20260525.zip` 包含源码、前端、后端、知识库、公开数据、PPT、视频、文档、便携 Python、虚拟环境依赖、启动脚本、测试脚本和卸载脚本。",
                "包内 `.env` 随可信电脑使用，文档正文不展示 API key，避免泄露。",
                "解压后可先运行 `Test-TrustedPC.ps1`，再运行正式启动脚本。",
            ],
        },
        {
            "title": "手机扫码说明",
            "bullets": [
                "设置弹窗内有“手机端可扫码”区域，二维码和文本框都写入局域网访问地址。",
                "手机必须和电脑在同一网络，且网络允许设备互访。酒店 Wi-Fi 和部分校园 Wi-Fi 常开启客户端隔离。",
                "若无法访问，优先使用手机热点或便携路由器；在可信电脑上可用 `Fix-Mobile-WiFi-Access.ps1` 添加 Windows 防火墙规则。",
            ],
        },
        {
            "title": "硬件适配建议",
            "tables": [
                {
                    "headers": ["形态", "硬件建议", "用途"],
                    "rows": [
                        ["路演/比赛", "Windows 笔记本，16GB 内存，稳定网络", "现场演示、PPT、视频和手机扫码"],
                        ["合作社工作站", "Windows 主机或小型工控机，局域网路由器", "日常问答、行情、政策、导入导出"],
                        ["大棚边缘节点", "工控机/网关 + 传感器 + 摄像头", "监测、预警、IOT 数据接入"],
                        ["移动端", "普通手机浏览器/PWA", "农户查看建议、扫码演示和现场走访"],
                    ],
                }
            ],
        },
    ]


def materials_index(generated: list[Path]) -> None:
    ppt = OUT / "AgriKB_数智新农人经营中枢_路演终版_20260525.pptx"
    video = OUT / "AgriKB_backend_operation_demo_20260525.mp4"
    lines = [
        "# AgriKB V1.3 交付材料索引",
        "",
        f"更新时间：{TODAY}",
        "",
        "## 核心路演材料",
        "",
        f"- 30 页路演 PPT：`{ppt.name}`",
        f"- 后台操作视频：`{video.name}`",
        "- 功能截图目录：`screenshots_20260525/`",
        "- PPT 更新记录：`ROADSHOW_PPT_30PAGES_UPDATE_QA_20260525.md`",
        "",
        "## 本次增强更新文档",
        "",
    ]
    for path in generated:
        lines.append(f"- `{path.name}`")
    lines += [
        "",
        "## 一键运行包",
        "",
        "- 可信电脑压缩包：`AgriKB_TrustedPC_OneClick_20260525_AgriKB_FIXED_20260525.zip`",
        "- 解压后双击：`一键启动AgriKB_可信电脑.bat`",
        "- 自检脚本：`Test-TrustedPC.ps1`",
        "- 手机访问修复：`一键修复手机扫码访问.bat`",
        "",
        "## 交付注意事项",
        "",
        "- 文档正文不展示 API key；可信电脑包中的 `.env` 仅供受信任设备使用。",
        "- 所有句容场景统一表述为“江苏句容”。",
        "- 专利和软著材料为技术交底与申请初稿，正式递交前建议由代理师或法务复核权利要求、署名和日期。",
    ]
    (OUT / "README_材料包索引.md").write_text("\n".join(lines), encoding="utf-8")


def write_manifest(generated: list[Path]) -> None:
    manifest = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "version": "V1.3",
        "scenario": "江苏句容",
        "materials": [
            {"name": p.name, "size": p.stat().st_size, "path": str(p)}
            for p in generated
        ],
        "notes": [
            "Documents were enriched for roadshow, product delivery, patent disclosure, software copyright and trusted-PC deployment.",
            "API keys are not printed in document body.",
            "All checked scenario labels use 江苏句容.",
        ],
    }
    (OUT / "MATERIALS_REFRESH_MANIFEST_20260525.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def mirror_extra_files(generated: list[Path]) -> list[Path]:
    extra: list[Path] = []
    patent_docx = OUT / "07_AgriKB_专利申请书_增强版_20260525.docx"
    patent_md = OUT / "07_AgriKB_专利申请书_增强版_20260525.md"
    soft_docx = OUT / "08_AgriKB_软件著作权申请书_增强版_20260525.docx"
    soft_md = OUT / "08_AgriKB_软件著作权申请书_增强版_20260525.md"
    source_patent_docx = OUT / "03_AgriKB_专利交底书_初稿.docx"
    source_patent_md = OUT / "03_AgriKB_专利交底书_初稿.md"
    source_soft_docx = OUT / "04_AgriKB_软件著作权登记材料_初稿.docx"
    source_soft_md = OUT / "04_AgriKB_软件著作权登记材料_初稿.md"
    for src, dst in [
        (source_patent_docx, patent_docx),
        (source_patent_md, patent_md),
        (source_soft_docx, soft_docx),
        (source_soft_md, soft_md),
    ]:
        shutil.copy2(src, dst)
        extra.append(dst)
    return generated + extra


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    specs = [
        ("01_AgriKB_使用说明书.docx", "01_AgriKB_使用说明书.md", "AgriKB 使用说明书", "从启动、问答、政策、行情、天气、地图、文件到卸载的完整操作说明。", usage_sections()),
        ("02_AgriKB_产品说明书.docx", "02_AgriKB_产品说明书.md", "AgriKB 产品说明书", "面向农户、农业局、合作社、企业和投资评审的产品价值与商业化说明。", product_sections()),
        ("03_AgriKB_专利交底书_初稿.docx", "03_AgriKB_专利交底书_初稿.md", "AgriKB 专利申请书与技术交底", "面向知识产权代理人的方法、系统、设备和存储介质申请初稿。", patent_sections()),
        ("04_AgriKB_软件著作权登记材料_初稿.docx", "04_AgriKB_软件著作权登记材料_初稿.md", "AgriKB 软件著作权申请材料", "软件基本信息、功能模块、技术特点、源程序结构和登记材料清单。", copyright_sections()),
        ("05_AgriKB_移动端与硬件部署适配说明.docx", "05_AgriKB_移动端与硬件部署适配说明.md", "AgriKB 移动端与硬件部署适配说明", "可信电脑、手机扫码、网络限制处理与 IOT 现场适配说明。", deployment_sections()),
        ("06_AgriKB_项目介绍书.docx", "06_AgriKB_项目介绍书.md", "AgriKB 项目介绍书", "面向比赛评委、农业部门、合作伙伴和投资人的项目介绍材料。", project_sections()),
    ]
    generated: list[Path] = []
    for docx_name, md_name, title, subtitle, sections in specs:
        generated.append(render_doc(docx_name, title, subtitle, sections))
        generated.append(render_md(md_name, title, subtitle, sections))
    generated = mirror_extra_files(generated)
    materials_index(generated)
    generated.append(OUT / "README_材料包索引.md")
    write_manifest(generated)
    generated.append(OUT / "MATERIALS_REFRESH_MANIFEST_20260525.json")
    print(json.dumps({"generated": [p.name for p in generated]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

