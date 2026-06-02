# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from PIL import Image
import win32com.client


ROOT = Path(__file__).resolve().parents[1]
DELIVERABLES = ROOT / "deliverables" / "AgriKB_DualTrack_FirstPrize_Materials_20260523"
OLD_SHOTS = ROOT / "outputs" / "manual-20260523-agrikb-function-screenshots" / "presentations" / "agrikb-function-screenshots" / "assets" / "function-screenshots"
NEW_SHOTS = ROOT / "outputs" / "roadshow-mobile-refresh" / "screenshots"
CROP_DIR = NEW_SHOTS / "crops"
QR_PATH = DELIVERABLES / "AgriKB_mobile_test_qr.png"
VIDEO_PATH = DELIVERABLES / "AgriKB_function_demo_recording.webm"
FINAL_PPTX = DELIVERABLES / "AgriKB_数智新农人经营中枢_路演终版_含视频二维码.pptx"


SLIDE_W = 960
SLIDE_H = 540

PAPER = 0xECF5F7
INK = 0x1D2117
MUTED = 0x6A7163
GREEN = 0x527D2F
DEEP_GREEN = 0x37511F
OCHRE = 0x2D85B6
BLUE = 0x9F6F41
RED = 0x3C4AB1
LINE = 0xCFDFD7
FIELD = 0xDBF0E7
WHITE = 0xFFFFFF
PALE_GREEN = 0xEAF6EE
PALE_GOLD = 0xDFF0F7
PALE_BLUE = 0xF7F0EA


def rgb(hex_value: int) -> int:
    r = (hex_value >> 16) & 255
    g = (hex_value >> 8) & 255
    b = hex_value & 255
    return r + g * 256 + b * 65536


def add_rect(slide, x, y, w, h, fill=WHITE, line=LINE, width=1):
    shape = slide.Shapes.AddShape(1, x, y, w, h)
    shape.Fill.Visible = -1
    shape.Fill.ForeColor.RGB = rgb(fill)
    shape.Line.Visible = -1 if width else 0
    if width:
        shape.Line.ForeColor.RGB = rgb(line)
        shape.Line.Weight = width
    return shape


def add_text(slide, text, x, y, w, h, size=18, color=INK, bold=False, align=1, valign=1, font="Microsoft YaHei"):
    box = slide.Shapes.AddTextbox(1, x, y, w, h)
    tf = box.TextFrame
    tf.WordWrap = -1
    tf.MarginLeft = 3
    tf.MarginRight = 3
    tf.MarginTop = 2
    tf.MarginBottom = 2
    tf.VerticalAnchor = valign
    tr = tf.TextRange
    tr.Text = text
    tr.Font.Name = font
    tr.Font.Size = size
    tr.Font.Bold = -1 if bold else 0
    tr.Font.Color.RGB = rgb(color)
    tr.ParagraphFormat.Alignment = align
    return box


def add_pill(slide, text, x, y, w, fill=PALE_GREEN, color=GREEN):
    add_rect(slide, x, y, w, 26, fill, color, 1)
    add_text(slide, text, x + 4, y + 4, w - 8, 18, 10.5, color, True, 2, 3)


def add_image(slide, path: Path, x, y, w, h, contain=True):
    path = Path(path)
    with Image.open(path) as img:
        iw, ih = img.size
    if contain:
        scale = min(w / iw, h / ih)
        nw, nh = iw * scale, ih * scale
        nx, ny = x + (w - nw) / 2, y + (h - nh) / 2
    else:
        nw, nh, nx, ny = w, h, x, y
    return slide.Shapes.AddPicture(str(path), 0, -1, nx, ny, nw, nh)


def base(slide, kicker: str, num: int, dark=False):
    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, DEEP_GREEN if dark else PAPER, DEEP_GREEN if dark else PAPER, 0)
    marker = GREEN if not dark else 0xD4E6C6
    text_color = marker
    add_rect(slide, 40, 30, 34, 3, marker, marker, 0)
    add_text(slide, kicker, 82, 22, 510, 20, 9.5, text_color, True)
    add_text(slide, f"{num:02d}", 890, 24, 34, 18, 8.5, text_color if dark else MUTED, False, 3)
    add_text(slide, "AgriKB 数智新农人经营中枢", 40, 512, 260, 14, 8.2, text_color if dark else MUTED)


def title(slide, claim: str, sub: str = "", y=62, dark=False):
    add_text(slide, claim, 40, y, 790, 58, 25, WHITE if dark else INK, True)
    if sub:
        add_text(slide, sub, 42, y + 62, 780, 32, 12.5, 0xE0EBD8 if dark else MUTED)


def metric(slide, value, label, x, y, w, color=GREEN):
    add_rect(slide, x, y, w, 70, WHITE, LINE, 1)
    add_text(slide, value, x + 12, y + 10, w - 24, 24, 21, color, True)
    add_text(slide, label, x + 12, y + 42, w - 24, 18, 9.5, MUTED)


def card(slide, head, body, x, y, w, h, accent=GREEN, fill=WHITE):
    add_rect(slide, x, y, w, h, fill, LINE, 1)
    add_rect(slide, x, y, 5, h, accent, accent, 0)
    add_text(slide, head, x + 14, y + 12, w - 28, 22, 14, accent, True)
    add_text(slide, body, x + 14, y + 40, w - 28, h - 48, 11.5, INK)


def prepare_zoom_crops():
    CROP_DIR.mkdir(parents=True, exist_ok=True)
    for path in NEW_SHOTS.glob("*_full.png"):
        out = CROP_DIR / f"{path.stem}_answer_zoom.png"
        if out.exists():
            continue
        with Image.open(path) as img:
            w, h = img.size
            crop = img.crop((int(w * 0.20), min(620, h - 1), int(w * 0.66), h))
            crop.save(out)


def slide_cover(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "2026 句容“福地青年英才”创业大赛", 1, dark=True)
    add_text(s, "AgriKB\n数智新农人经营中枢", 54, 92, 530, 116, 38, WHITE, True)
    add_text(s, "把政策、市场、气象、收购和农业知识，变成农民能听懂、政府能治理、企业能经营的一句话决策。", 58, 228, 610, 54, 17, 0xE0EBD8)
    add_pill(s, "党关注“三农”", 58, 310, 126, 0xF0F6EA, DEEP_GREEN)
    add_pill(s, "服务乡村全面振兴", 198, 310, 156, 0xF0F6EA, DEEP_GREEN)
    add_pill(s, "数智信息 × 新农人", 368, 310, 154, 0xF7F0DF, OCHRE)
    metric(s, "145+", "已整理农业知识块", 60, 390, 150, GREEN)
    metric(s, "17", "功能实测截图", 232, 390, 150, OCHRE)
    metric(s, "PWA", "手机扫码即测", 404, 390, 150, BLUE)
    add_rect(s, 650, 74, 238, 330, 0xEAF6EE, 0xC6DAC0, 1)
    for i in range(7):
        add_rect(s, 676 + i * 28, 330 - i * 28, 18, 110 + i * 25, 0xC6E3B0 if i % 2 else 0xD9ECCC, 0xC6E3B0 if i % 2 else 0xD9ECCC, 0)
    card(s, "路演主张", "不是再做一个农业 App，而是县域农业经营智能体：问答、证据、图谱、政策、市场、气象和渠道闭环。", 626, 420, 286, 70, GREEN, WHITE)


def slide_opportunity(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "WHY NOW", 2)
    title(s, "县域农业缺的不是信息，而是能直接行动的经营判断。", "农民、农业局、企业面对的是同一批数据，但今天仍然被分散在通知、群消息、网页、台账和经验里。")
    cards = [
        ("农民", "看不懂政策、找不到收购渠道、错过采收窗口。", GREEN),
        ("农业局", "项目、主体、培训和产业扶持难形成实时台账。", OCHRE),
        ("企业", "采购、溯源、供应链和电商运营缺少本地可信信号。", BLUE),
    ]
    for i, (h, b, c) in enumerate(cards):
        card(s, h, b, 58 + i * 300, 190, 254, 154, c, WHITE)
    add_rect(s, 96, 405, 768, 54, 0xEAF6EE, 0xC9DABF, 1)
    add_text(s, "AgriKB 的价值：把“找信息”变成“下一步怎么干”，把“经验判断”变成“有证据的经营建议”。", 120, 420, 720, 22, 15, DEEP_GREEN, True, 2)


def slide_solution(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "SOLUTION", 3)
    title(s, "一个入口，三类用户，围绕句容农业经营实时给答案。", "前台像 ChatGPT 一样简单；后台连接知识库、政策资料、气象环境、市场渠道和 Kimi 模型。")
    roles = [
        ("农民端", "今天先干什么、卖给谁、能领什么补贴、天气有没有风险。", GREEN),
        ("农业局端", "主体台账、产业扶持、培训服务、项目筛选和治理报告。", OCHRE),
        ("企业端", "收购窗口、质量溯源、供应链协同、电商助农和品牌运营。", BLUE),
    ]
    for i, (h, b, c) in enumerate(roles):
        card(s, h, b, 58 + i * 300, 174, 254, 150, c, 0xF9FBF6)
    steps = [("问一句", "自然语言、快捷按钮、文件上传"), ("查一遍", "政策、市场、气象、知识库"), ("判一次", "新农人助手整合分析"), ("能执行", "动作、渠道、材料、风险")]
    for i, (h, b) in enumerate(steps):
        x = 80 + i * 210
        add_rect(s, x, 390, 150, 68, WHITE, LINE, 1)
        add_text(s, f"0{i+1}", x + 10, 402, 34, 22, 16, GREEN, True)
        add_text(s, h, x + 48, 398, 86, 22, 15, INK, True)
        add_text(s, b, x + 18, 430, 112, 16, 9.5, MUTED, False, 2)


def slide_farmer_journey(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "FARMER JOURNEY", 4)
    title(s, "农民不需要学习复杂系统，只需要点四个大按钮。", "把高门槛的信息系统变成“今天怎么干、东西卖给谁、能领啥补贴、天气有没有风险”。")
    buttons = [("今天怎么干", "采收、用工、运输、田间记录"), ("东西卖给谁", "收购、团购、电商、报价"), ("能领啥补贴", "培训、创业、品牌、认证"), ("天气有没有风险", "降雨、病虫害、冷链、作业窗口")]
    for i, (h, b) in enumerate(buttons):
        x = 76 + (i % 2) * 410
        y = 180 + (i // 2) * 138
        add_rect(s, x, y, 342, 96, 0xF3FAEE, 0xC9DABF, 1)
        add_text(s, h, x + 20, y + 18, 150, 28, 21, DEEP_GREEN, True)
        add_text(s, b, x + 20, y + 54, 292, 20, 12, MUTED)
    add_text(s, "路演现场演示：点“农产品行情”后，系统给出政策扶持、市场/收购/电商渠道、气象环境提醒和下一步动作。", 90, 470, 780, 28, 16, INK, True, 2)


def slide_intelligence(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "INTELLIGENCE ENGINE", 5)
    title(s, "Kimi 不再输出固定话术，而是围绕证据做经营整合。", "默认隐藏证据链和知识树，农民先看结论；需要审计时，农业局和企业可以展开来源。")
    card(s, "模型层", "Kimi Code CLI 作为默认回答模型，回答链路实测 llm_used=true。", 56, 178, 260, 118, GREEN, WHITE)
    card(s, "知识层", "AGROVOC、Crop Ontology、台湾农业数据、句容政策和本地助农资料统一索引。", 350, 178, 260, 118, OCHRE, WHITE)
    card(s, "实时层", "联网搜索开关控制政策、新闻、气象、行情、收购和渠道信息是否实时查询。", 644, 178, 260, 118, BLUE, WHITE)
    add_rect(s, 112, 360, 736, 74, 0xF7F0DF, 0xD8C99F, 1)
    add_text(s, "回答结构固定为经营价值，而不是技术日志：先干什么、政策机会、市场渠道、气象风险、证据来源、下一步动作。", 140, 382, 680, 24, 16, INK, True, 2)


def slide_sources(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "DATA MOAT", 6)
    title(s, "开放知识源 + 本地农业数据，构成县域可复制的数据底座。", "用国际农业语义标准做骨架，用台湾农业开放数据做样板，用句容政策与助农渠道做落地。")
    items = [
        ("AGROVOC", "农业多语言控制词表，标准化作物、病虫害、农业活动。", GREEN),
        ("Crop Ontology", "性状、观测变量、测量方法，支撑作物本体推理。", OCHRE),
        ("Google Earth Engine", "农业遥感、土地覆盖和环境变量，支撑区域农情。", BLUE),
        ("台湾农业开放数据", "主体、产品、认证字段可作为本地化台账样板。", GREEN),
        ("句容政策与渠道", "农业局资料、电商进农村、供销渠道、新农人扶持。", OCHRE),
        ("用户补充资料", "PDF、DOCX、CSV、XLSX 可随时补充进知识库。", BLUE),
    ]
    for i, (h, b, c) in enumerate(items):
        card(s, h, b, 54 + (i % 3) * 300, 170 + (i // 3) * 144, 258, 106, c, WHITE)


def slide_business(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "BUSINESS MODEL", 7)
    title(s, "先做句容标杆，再复制到县域农业经营场景。", "商业化不是单点工具收费，而是围绕政府、企业和新农人的长期运营服务。")
    cols = [
        ("政府项目/运营", "产业扶持、培训、数据治理、报告和示范区运营。", GREEN),
        ("企业数据服务", "采购、溯源、供应链、电商渠道与品牌运营。", BLUE),
        ("新农人工具包", "问答、台账、政策匹配、销售建议和移动端服务。", OCHRE),
    ]
    for i, (h, b, c) in enumerate(cols):
        card(s, h, b, 68 + i * 292, 176, 246, 148, c, WHITE)
    metric(s, "句容", "首个区域样板", 92, 392, 150, GREEN)
    metric(s, "农业局", "组织与政策入口", 302, 392, 150, OCHRE)
    metric(s, "企业/合作社", "交易与供应链闭环", 512, 392, 150, BLUE)
    metric(s, "新农人", "真实高频使用者", 722, 392, 150, GREEN)


def slide_competition(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "COMPETITIVE EDGE", 8)
    title(s, "优秀农业软件多在单点能力，AgriKB 争的是县域经营中枢。", "对标 FieldView、John Deere Operations Center、CropX、Agworld、OneSoil、EOSDA、惠农网、一亩田等平台。")
    rows = [
        ("遥感农情", "强在地块监测", "AgriKB 叠加政策、市场和经营动作"),
        ("农机作业", "强在设备协同", "AgriKB 面向县域主体台账和项目治理"),
        ("农技管理", "强在作业记录", "AgriKB 把农技、证据链和本地政策合成回答"),
        ("交易渠道", "强在撮合交易", "AgriKB 给出什么时候卖、卖给谁、怎么申报"),
    ]
    y = 170
    add_text(s, "能力维度", 76, 142, 130, 18, 11, GREEN, True, 2)
    add_text(s, "市场强项", 326, 142, 160, 18, 11, GREEN, True, 2)
    add_text(s, "AgriKB 差异化", 602, 142, 220, 18, 11, GREEN, True, 2)
    for i, (a, b, c) in enumerate(rows):
        yy = y + i * 70
        add_rect(s, 60, yy, 840, 52, 0xF7FBF4 if i % 2 == 0 else WHITE, LINE, 1)
        add_text(s, a, 76, yy + 16, 130, 18, 12, INK, True, 2)
        add_text(s, b, 280, yy + 16, 240, 18, 12, MUTED, False, 2)
        add_text(s, c, 550, yy + 14, 300, 22, 12, DEEP_GREEN, True, 2)
    add_text(s, "核心判断：不是做“又一个农产品问答页”，而是做县域农业的信息聚合、经营判断、申报交易与治理闭环。", 86, 470, 790, 24, 15, INK, True, 2)


def slide_go_to_market(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "GO TO MARKET", 9)
    title(s, "以“数智信息 + 新农人”参赛，以句容农业场景交付。", "现场路演重点证明三件事：农民能用、农业局能管、企业能转化。")
    steps = [
        ("1", "比赛路演", "用草莓、福桃、茶叶、蔬菜等本地场景完成可操作演示。"),
        ("2", "示范合作", "农业局、合作社、电商助农渠道共同形成试点数据闭环。"),
        ("3", "县域复制", "将知识源、政策库、渠道库和移动端模板复制到更多地区。"),
    ]
    for i, (n, h, b) in enumerate(steps):
        x = 74 + i * 286
        add_rect(s, x, 185, 230, 196, WHITE, LINE, 1)
        add_text(s, n, x + 18, 206, 44, 44, 30, GREEN, True, 2, 3)
        add_text(s, h, x + 72, 212, 120, 24, 18, INK, True)
        add_text(s, b, x + 22, 268, 184, 70, 12.5, MUTED)
    add_rect(s, 106, 430, 748, 56, 0xEAF6EE, 0xC9DABF, 1)
    add_text(s, "第一名叙事：技术有壁垒、场景有刚需、界面能上手、材料可交付、现场可扫码实测。", 132, 446, 700, 22, 16, DEEP_GREEN, True, 2)


def slide_mobile(pres, mobile_url):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "MOBILE TEST", 10)
    title(s, "评委可以直接扫码，在手机上打开同一套农业智能体。", "同一 Wi-Fi 下运行“手机扫码测试.bat”，后台以 0.0.0.0 启动，手机访问局域网地址。")
    add_rect(s, 82, 160, 314, 314, WHITE, LINE, 1)
    add_image(s, QR_PATH, 100, 176, 278, 278)
    add_text(s, "扫码测试地址", 448, 176, 180, 24, 18, INK, True)
    add_text(s, "手机与电脑同一 Wi-Fi，直接扫左侧二维码", 448, 212, 410, 22, 15, BLUE, True)
    add_text(s, mobile_url, 448, 236, 410, 18, 9.2, MUTED, False)
    card(s, "手机端适配", "PWA 页面、简化操作、按钮化问答、文件上传与回答朗读，减少复杂配置。", 448, 270, 354, 86, GREEN, WHITE)
    card(s, "现场提醒", "手机和电脑需连接同一 Wi-Fi；如无法访问，放行 Windows 防火墙中的 Python 或端口 8010。", 448, 382, 354, 86, OCHRE, WHITE)


def slide_video(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "DEMO VIDEO", 11)
    title(s, "功能讲解视频已嵌入 PPT，可在路演中直接播放。", "视频旁保留手机二维码：讲完商业逻辑后，评委可以现场扫码实测。")
    add_rect(s, 62, 148, 600, 338, 0x111A16, 0x111A16, 0)
    try:
        media = s.Shapes.AddMediaObject2(str(VIDEO_PATH), 0, -1, 62, 148, 600, 338)
        media.Name = "AgriKB 功能讲解视频"
    except Exception:
        add_text(s, "视频文件已随包提供\nAgriKB_function_demo_recording.webm", 120, 278, 480, 48, 20, WHITE, True, 2)
    add_rect(s, 704, 156, 176, 176, WHITE, LINE, 1)
    add_image(s, QR_PATH, 716, 168, 152, 152)
    card(s, "推荐讲解顺序", "1. 扫码进入手机端\n2. 打开联网搜索开关\n3. 点“农产品行情”\n4. 展开证据链和知识树\n5. 展示政策、市场、气象判断", 698, 358, 190, 112, GREEN, WHITE)


def slide_appendix_index(pres):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "LIVE PROOF", 12)
    title(s, "17 个功能入口均可点入并返回信息，09-17 已换成完整长页截图。", "以下为功能实测附录，路演时可按评委关注点跳转。")
    groups = [
        ("角色入口", "数智信息、新农人、农业局、企业"),
        ("农民高频", "今天怎么干、卖给谁、补贴、天气风险"),
        ("产业情报", "新农人政策、数智中台、资讯聚合、竞品对标、创业大赛"),
        ("经营服务", "农产品行情、农业气象、质量溯源、作物本体"),
    ]
    for i, (h, b) in enumerate(groups):
        card(s, h, b, 76 + (i % 2) * 410, 176 + (i // 2) * 130, 340, 92, [GREEN, OCHRE, BLUE, GREEN][i], WHITE)
    add_text(s, "备注：附录中的“完整长页截图”保留页面上下文、问题和回答；右侧放大区用于路演投屏时阅读关键答案。", 100, 454, 760, 24, 14, INK, True, 2)


def screenshot_slide(pres, num, label, subtitle, path, full=False, zoom_path=None):
    s = pres.Slides.Add(pres.Slides.Count + 1, 12)
    base(s, "PRODUCT PROOF", num)
    title(s, label, subtitle)
    if full and zoom_path:
        add_rect(s, 42, 140, 280, 340, WHITE, LINE, 1)
        add_image(s, path, 50, 148, 264, 324)
        add_text(s, "完整长页", 112, 484, 140, 14, 9.5, MUTED, False, 2)
        add_rect(s, 354, 140, 552, 340, WHITE, LINE, 1)
        add_image(s, zoom_path, 366, 152, 528, 316)
        add_text(s, "回答区放大", 548, 484, 160, 14, 9.5, MUTED, False, 2)
    else:
        add_rect(s, 66, 136, 828, 354, WHITE, LINE, 1)
        add_image(s, path, 78, 148, 804, 330)
    return s


def build():
    prepare_zoom_crops()
    FINAL_PPTX.parent.mkdir(parents=True, exist_ok=True)

    mobile_url = "http://10.188.88.114:8010/ui/?v=20260523agri6"

    ppt = win32com.client.Dispatch("PowerPoint.Application")
    ppt.Visible = True
    pres = ppt.Presentations.Add()
    pres.PageSetup.SlideWidth = SLIDE_W
    pres.PageSetup.SlideHeight = SLIDE_H

    slide_cover(pres)
    slide_opportunity(pres)
    slide_solution(pres)
    slide_farmer_journey(pres)
    slide_intelligence(pres)
    slide_sources(pres)
    slide_business(pres)
    slide_competition(pres)
    slide_go_to_market(pres)
    slide_mobile(pres, mobile_url)
    slide_video(pres)
    slide_appendix_index(pres)

    first = [
        ("01 数智信息入口", "RAG、知识图谱、实时数据和模型决策", OLD_SHOTS / "01_digital.png"),
        ("02 新农人工作台", "经营判断、采收销售、政策申报", OLD_SHOTS / "02_new_farmer.png"),
        ("03 农业局治理", "数据治理、产业扶持、培训报告", OLD_SHOTS / "03_bureau.png"),
        ("04 农业企业入口", "溯源、市场、供应链与电商渠道", OLD_SHOTS / "04_company.png"),
        ("05 今天怎么干", "一键生成农民今日行动清单", OLD_SHOTS / "05_farmer_today.png"),
        ("06 东西卖给谁", "收购、电商、报价与渠道建议", OLD_SHOTS / "06_farmer_sell.png"),
        ("07 能领啥补贴", "政策匹配和材料准备清单", OLD_SHOTS / "07_farmer_subsidy.png"),
        ("08 天气有没有风险", "气象、病虫害、采收和运输风险", OLD_SHOTS / "08_farmer_risk.png"),
    ]
    for i, (h, sub, p) in enumerate(first, start=13):
        screenshot_slide(pres, i, h, sub, p)

    second = [
        ("09 新农人政策", "完整聊天页 + 回答区放大", NEW_SHOTS / "09_policy_full.png"),
        ("10 数智中台", "完整聊天页 + 回答区放大", NEW_SHOTS / "10_platform_full.png"),
        ("11 资讯聚合", "完整聊天页 + 回答区放大", NEW_SHOTS / "11_intelligence_full.png"),
        ("12 竞品对标", "完整聊天页 + 回答区放大", NEW_SHOTS / "12_benchmark_full.png"),
        ("13 创业大赛", "完整聊天页 + 回答区放大", NEW_SHOTS / "13_competition_full.png"),
        ("14 农产品行情", "完整聊天页 + 回答区放大", NEW_SHOTS / "14_market_full.png"),
        ("15 农业气象", "完整聊天页 + 回答区放大", NEW_SHOTS / "15_weather_full.png"),
        ("16 质量溯源", "完整聊天页 + 回答区放大", NEW_SHOTS / "16_traceability_full.png"),
        ("17 作物本体", "完整聊天页 + 回答区放大", NEW_SHOTS / "17_crop_full.png"),
    ]
    for i, (h, sub, p) in enumerate(second, start=21):
        zoom = CROP_DIR / f"{p.stem}_answer_zoom.png"
        screenshot_slide(pres, i, h, sub, p, True, zoom)

    pres.SaveAs(str(FINAL_PPTX))
    pres.Close()
    ppt.Quit()

    return FINAL_PPTX


if __name__ == "__main__":
    final = build()
    print(final)
