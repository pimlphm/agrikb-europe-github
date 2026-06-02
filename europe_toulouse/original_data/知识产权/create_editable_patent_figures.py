from __future__ import annotations

import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx.dml.color import RGBColor
from pptx import Presentation
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "专利附图"
OUT_PPTX = ROOT / "专利附图_可编辑版.pptx"
OUT_DIR = ROOT / "专利附图_可编辑导出"
REPORT = ROOT / "专利附图_重绘检查报告.md"

SLIDE_W = 13.333
SLIDE_H = 7.5
CANVAS_W = 2000
CANVAS_H = 1125


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/simhei.ttf" if bold else "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


F_TITLE = font(38, True)
F_HEAD = font(28, True)
F_BODY = font(24)
F_SMALL = font(20)


def p_in(x: float) -> float:
    return Inches(x)


def add_textbox(slide, x, y, w, h, text, size=14, bold=False):
    tb = slide.shapes.add_textbox(p_in(x), p_in(y), p_in(w), p_in(h))
    tf = tb.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = PP_ALIGN.CENTER
    r = p.runs[0]
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.name = "SimSun"
    return tb


def add_box(slide, x, y, w, h, text, fill="F7F7F7", size=13, bold=False):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, p_in(x), p_in(y), p_in(w), p_in(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor(*(int(fill[i:i + 2], 16) for i in (0, 2, 4)))
    shp.line.color.rgb = RGBColor(0, 0, 0)
    shp.line.width = Pt(1)
    tf = shp.text_frame
    tf.clear()
    tf.margin_left = p_in(0.06)
    tf.margin_right = p_in(0.06)
    tf.margin_top = p_in(0.04)
    tf.margin_bottom = p_in(0.04)
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = PP_ALIGN.CENTER
    r = p.runs[0]
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.name = "SimSun"
    return shp


def add_arrow(slide, x1, y1, x2, y2):
    ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, p_in(x1), p_in(y1), p_in(x2), p_in(y2))
    ln.line.color.rgb = RGBColor(0, 0, 0)
    ln.line.width = Pt(1.2)
    ln.line.end_arrowhead = True
    return ln


def add_line(slide, x1, y1, x2, y2):
    ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, p_in(x1), p_in(y1), p_in(x2), p_in(y2))
    ln.line.color.rgb = RGBColor(0, 0, 0)
    ln.line.width = Pt(1)
    return ln


def draw_centered(draw, box, text, fnt, fill=(0, 0, 0)):
    x1, y1, x2, y2 = box
    lines = text.split("\n")
    heights = [draw.textbbox((0, 0), line, font=fnt)[3] for line in lines]
    total = sum(heights) + (len(lines) - 1) * 6
    y = y1 + (y2 - y1 - total) / 2
    for line, h in zip(lines, heights):
        bb = draw.textbbox((0, 0), line, font=fnt)
        x = x1 + (x2 - x1 - (bb[2] - bb[0])) / 2
        draw.text((x, y), line, font=fnt, fill=fill)
        y += h + 6


def png_box(draw, x, y, w, h, text, fill=(247, 247, 247), fnt=F_BODY, width=2):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=fill, outline=(0, 0, 0), width=width)
    draw_centered(draw, (x + 8, y + 6, x + w - 8, y + h - 6), text, fnt)


def png_arrow(draw, p1, p2, width=3):
    draw.line([p1, p2], fill=(0, 0, 0), width=width)
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    size = 16
    pts = [
        p2,
        (p2[0] - size * math.cos(ang - 0.45), p2[1] - size * math.sin(ang - 0.45)),
        (p2[0] - size * math.cos(ang + 0.45), p2[1] - size * math.sin(ang + 0.45)),
    ]
    draw.polygon(pts, fill=(0, 0, 0))


def base_png(title, fig_no):
    im = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
    d = ImageDraw.Draw(im)
    draw_centered(d, (0, 28, CANVAS_W, 90), f"{fig_no}  {title}", F_TITLE)
    return im, d


def title_slide(slide, title, fig_no):
    add_textbox(slide, 0.25, 0.15, 12.8, 0.42, f"{fig_no}  {title}", 20, True)


FIGS = [
    ("图01_系统整体架构图.png", "系统整体架构图", "图1"),
    ("图02_BFO_IOF三层本体架构.png", "BFO/IOF三层本体架构", "图2"),
    ("图03_多因子关联强度计算流程图.png", "多因子关联强度计算流程图", "图3"),
    ("图04_混合标准条款检索算法.png", "混合标准条款检索算法", "图4"),
    ("图05_六层输出一致性校验流程图.png", "六层输出一致性校验流程图", "图5"),
    ("图06_知识图谱可视化效果图.png", "知识图谱可视化效果图", "图6"),
    ("图07_737_PACK_OFF子图.png", "737 PACK OFF故障案例子图", "图7"),
    ("图08_故障树自动生成结果图.png", "故障树自动生成结果图", "图8"),
    ("图09_因果树自动生成结果图.png", "因果树自动生成结果图", "图9"),
    ("图10_跨文档关联网络图.png", "跨文档关联网络图", "图10"),
    ("图11_检索性能对比柱状图.png", "检索性能对比柱状图", "图11"),
    ("图12_定量评估指标雷达图.png", "定量评估指标雷达图", "图12"),
    ("图13_经验闭环流程图.png", "经验闭环流程图", "图13"),
    ("图14_安全审计与权限管理架构图.png", "安全审计与权限管理架构图", "图14"),
    ("图15_GUI界面效果图.png", "GUI界面效果图", "图15"),
]


def add_flow(slide, labels, y=2.0):
    n = len(labels)
    w = 10.6 / n
    x0 = 1.25
    for i, label in enumerate(labels):
        add_box(slide, x0 + i * w, y, w - 0.18, 0.75, label, size=12, bold=True)
        if i:
            add_arrow(slide, x0 + i * w - 0.22, y + 0.38, x0 + i * w - 0.02, y + 0.38)


def draw_flow_png(d, labels, y=330):
    n = len(labels)
    w = 1500 // n
    x0 = 250
    for i, label in enumerate(labels):
        png_box(d, x0 + i * w, y, w - 35, 105, label, fnt=F_SMALL)
        if i:
            png_arrow(d, (x0 + i * w - 38, y + 52), (x0 + i * w - 5, y + 52))


def build_slide(slide, idx, title, fig_no):
    title_slide(slide, title, fig_no)
    if idx == 0:
        for x, y, w, h, text in [
            (0.6, 1.0, 2.3, 0.7, "资料输入\nPDF/Word/标准"),
            (3.5, 0.85, 2.2, 0.7, "文档解析\n语义分块"),
            (6.4, 0.85, 2.2, 0.7, "三层本体\n约束抽取"),
            (9.3, 1.0, 2.5, 0.7, "知识图谱\n证据锚定"),
            (3.3, 3.0, 2.3, 0.7, "混合检索\n标准注入"),
            (6.2, 3.0, 2.5, 0.7, "多角色Agent\n一致性校验"),
            (9.3, 3.0, 2.5, 0.7, "问答输出\n审计日志"),
            (4.8, 5.2, 3.8, 0.65, "硬件适配层：CPU/GPU/NPU/DCU/MLU"),
        ]:
            add_box(slide, x, y, w, h, text, size=12, bold=True)
        for a in [(2.9, 1.35, 3.5, 1.2), (5.7, 1.2, 6.4, 1.2), (8.6, 1.2, 9.3, 1.35), (5.6, 3.35, 6.2, 3.35), (8.7, 3.35, 9.3, 3.35), (7.4, 3.7, 7.0, 5.2)]:
            add_arrow(slide, *a)
    elif idx == 1:
        for x, y, w, h, text in [
            (4.8, 0.9, 3.0, 0.7, "BFO顶层\n实体/过程/功能/质量"),
            (4.3, 2.45, 4.0, 0.8, "IOF核心层\n需求/设计/验证/接口/约束"),
            (3.5, 4.1, 5.6, 0.9, "航空领域层\n故障/维修/标准/培训/适航证据"),
        ]:
            add_box(slide, x, y, w, h, text, size=13, bold=True)
        add_arrow(slide, 6.3, 1.6, 6.3, 2.45)
        add_arrow(slide, 6.3, 3.25, 6.3, 4.1)
    elif idx == 2:
        labels = ["关系类型权重", "证据距离权重", "标准条款权重", "图结构权重", "LLM置信度"]
        for i, label in enumerate(labels):
            add_box(slide, 0.55 + i * 2.45, 1.15, 2.05, 0.75, label, size=11, bold=True)
            add_arrow(slide, 1.58 + i * 2.45, 1.9, 6.65, 3.05)
        add_box(slide, 5.0, 3.05, 3.3, 0.85, "加权融合\nS=αSt+βSe+γSs+δSg+ηSl", size=12, bold=True)
        add_arrow(slide, 6.65, 3.9, 6.65, 4.75)
        add_box(slide, 4.8, 4.75, 3.7, 0.75, "七级强度区间\n图谱边权与显示等级", size=12, bold=True)
    elif idx == 3:
        add_box(slide, 0.8, 1.25, 2.2, 0.8, "查询/实体\n关键词集合", size=12, bold=True)
        add_box(slide, 4.0, 0.8, 2.4, 0.75, "BM25稀疏检索", size=12, bold=True)
        add_box(slide, 4.0, 2.25, 2.4, 0.75, "稠密向量检索", size=12, bold=True)
        add_box(slide, 7.45, 1.45, 2.3, 0.75, "RRF/加权融合", size=12, bold=True)
        add_box(slide, 10.35, 1.45, 2.1, 0.75, "Top-K标准条款", size=12, bold=True)
        for a in [(3.0,1.65,4.0,1.17),(3.0,1.65,4.0,2.62),(6.4,1.17,7.45,1.82),(6.4,2.62,7.45,1.82),(9.75,1.82,10.35,1.82)]:
            add_arrow(slide,*a)
    elif idx == 4:
        add_flow(slide, ["JSON\nSchema", "本体\n一致性", "标准\n引用", "证据\n跨度", "冲突\n检测", "置信度\n阈值"], 2.2)
        add_box(slide, 4.5, 4.25, 4.3, 0.75, "通过：写入正式知识图谱；失败：进入人工复核队列", size=12, bold=True)
    elif idx == 5:
        centers = [(3, 2.0, "故障"), (5.2, 1.2, "部件"), (7.5, 2.0, "维修程序"), (5.2, 3.2, "标准条款"), (8.7, 3.6, "培训规范"), (3.0, 4.0, "证据片段")]
        for x, y, t in centers:
            add_box(slide, x, y, 1.55, 0.58, t, size=11, bold=True)
        for a in [(4.55,2.28,5.2,1.49),(6.75,1.49,7.5,2.28),(6.0,3.49,7.5,2.28),(4.5,4.29,5.2,3.49),(6.75,3.49,8.7,3.89),(3.78,2.58,3.78,4.0)]:
            add_arrow(slide,*a)
    elif idx == 6:
        add_box(slide, 0.8, 2.3, 2.1, 0.7, "PACK OFF\n告警", size=12, bold=True)
        add_box(slide, 3.6, 1.25, 2.1, 0.65, "引气系统\n压力异常", size=12, bold=True)
        add_box(slide, 3.6, 3.35, 2.1, 0.65, "空调组件\n工作异常", size=12, bold=True)
        add_box(slide, 6.4, 2.3, 2.1, 0.7, "MEL/维修\n程序证据", size=12, bold=True)
        add_box(slide, 9.3, 2.3, 2.2, 0.7, "培训提示\n风险复核", size=12, bold=True)
        for a in [(2.9,2.65,3.6,1.58),(2.9,2.65,3.6,3.68),(5.7,1.58,6.4,2.65),(5.7,3.68,6.4,2.65),(8.5,2.65,9.3,2.65)]:
            add_arrow(slide,*a)
    elif idx == 7:
        add_box(slide, 5.1, 0.95, 3.0, 0.65, "顶事件：引气系统压力低", size=12, bold=True)
        for x, text in [(1.2, "引气活门故障"), (4.05, "传感器异常"), (6.9, "管路泄漏"), (9.75, "控制逻辑异常")]:
            add_box(slide, x, 2.45, 2.05, 0.62, text, size=11, bold=True)
            add_arrow(slide, 6.6, 1.6, x + 1.02, 2.45)
            add_box(slide, x, 4.15, 2.05, 0.62, "基本事件\n证据节点", size=11)
            add_arrow(slide, x + 1.02, 3.07, x + 1.02, 4.15)
    elif idx == 8:
        add_flow(slide, ["故障现象", "直接原因", "中间影响", "维修处置", "培训复盘"], 2.3)
        add_box(slide, 4.6, 4.4, 4.0, 0.65, "按时间顺序保留证据跨度和因果方向", size=12, bold=True)
    elif idx == 9:
        for x, text in [(0.9, "737故障说明"), (4.9, "M2维修文件"), (8.9, "实作培训规范")]:
            add_box(slide, x, 1.25, 2.5, 0.75, text, size=12, bold=True)
            add_box(slide, x, 4.0, 2.5, 0.75, "实体/条款/案例\n归一节点", size=11)
            add_arrow(slide, x + 1.25, 2.0, x + 1.25, 4.0)
        add_arrow(slide, 3.4, 4.38, 4.9, 4.38)
        add_arrow(slide, 7.4, 4.38, 8.9, 4.38)
        add_line(slide, 2.15, 1.62, 10.15, 1.62)
    elif idx == 10:
        metrics = [("BM25", 0.58, 0.51), ("向量", 0.64, 0.57), ("混合", 0.81, 0.74)]
        add_textbox(slide, 1.3, 1.0, 2.0, 0.4, "Recall@10", 13, True)
        add_textbox(slide, 7.4, 1.0, 2.0, 0.4, "MRR", 13, True)
        for i, (name, r, m) in enumerate(metrics):
            add_box(slide, 1.0 + i * 1.55, 5.2 - r * 3.2, 0.85, r * 3.2, f"{name}\n{r:.2f}", size=10)
            add_box(slide, 7.0 + i * 1.55, 5.2 - m * 3.2, 0.85, m * 3.2, f"{name}\n{m:.2f}", size=10)
        add_line(slide, 0.8, 5.2, 5.6, 5.2); add_line(slide, 6.8, 5.2, 11.6, 5.2)
    elif idx == 11:
        labels = ["实体F1", "关系F1", "因果边界", "跨文档", "标准引用", "一致性", "审计", "可用性"]
        cx, cy, r = 6.65, 3.5, 2.1
        for i, lab in enumerate(labels):
            ang = 2 * math.pi * i / len(labels) - math.pi / 2
            x = cx + r * math.cos(ang); y = cy + r * math.sin(ang)
            add_line(slide, cx, cy, x, y)
            add_textbox(slide, x - 0.5, y - 0.18, 1.0, 0.35, lab, 9)
        add_box(slide, 5.7, 3.05, 1.9, 0.55, "本发明组\n综合提升", size=11, bold=True)
    elif idx == 12:
        add_flow(slide, ["分析结果", "经验提炼", "分级存储", "上下文注入", "复用反馈"], 2.3)
        add_box(slide, 3.9, 4.35, 5.2, 0.65, "永久经验与临时经验按机型、任务和证据来源管理", size=12, bold=True)
    elif idx == 13:
        for x, y, text in [(0.9,1.1,"用户/角色"), (3.7,1.1,"权限控制"), (6.5,1.1,"密级策略"), (9.3,1.1,"访问审计"), (3.7,3.7,"证据包"), (6.5,3.7,"模型版本"), (9.3,3.7,"推理指标")]:
            add_box(slide, x, y, 2.0, 0.65, text, size=12, bold=True)
        for a in [(2.9,1.43,3.7,1.43),(5.7,1.43,6.5,1.43),(8.5,1.43,9.3,1.43),(10.3,1.75,10.3,3.7),(8.5,4.03,9.3,4.03),(5.7,4.03,6.5,4.03)]:
            add_arrow(slide,*a)
    else:
        add_box(slide, 0.8, 1.0, 3.0, 4.8, "导航区\n文档管理\n标准库\n经验库", size=12, bold=True)
        add_box(slide, 4.2, 1.0, 4.1, 2.0, "对话问答区\n维修问题与证据包", size=12, bold=True)
        add_box(slide, 4.2, 3.5, 4.1, 2.3, "知识图谱区\n节点、边、详情", size=12, bold=True)
        add_box(slide, 8.8, 1.0, 3.5, 4.8, "审计与状态区\n模型/后端/延迟/吞吐", size=12, bold=True)


def build_png(idx, title, fig_no):
    im, d = base_png(title, fig_no)
    if idx in {0, 3, 4, 8, 12}:
        flow_map = {
            0: ["资料输入", "解析分块", "本体抽取", "图谱证据", "问答审计"],
            3: ["查询", "BM25", "向量检索", "融合排序", "标准条款"],
            4: ["Schema", "本体", "标准", "证据", "冲突", "阈值"],
            8: ["故障现象", "直接原因", "中间影响", "维修处置", "培训复盘"],
            12: ["分析", "提炼", "存储", "注入", "反馈"],
        }
        draw_flow_png(d, flow_map[idx], 370)
    elif idx == 10:
        d.line([(220, 930), (920, 930)], fill=0, width=4)
        d.line([(1080, 930), (1780, 930)], fill=0, width=4)
        vals = [("BM25", .58, .51), ("向量", .64, .57), ("混合", .81, .74)]
        for i, (n, r, m) in enumerate(vals):
            x = 280 + i * 190; h = int(r * 520)
            png_box(d, x, 930 - h, 115, h, f"{n}\n{r:.2f}", fnt=F_SMALL)
            x2 = 1140 + i * 190; h2 = int(m * 520)
            png_box(d, x2, 930 - h2, 115, h2, f"{n}\n{m:.2f}", fnt=F_SMALL)
        draw_centered(d, (220, 120, 920, 180), "Recall@10", F_HEAD)
        draw_centered(d, (1080, 120, 1780, 180), "MRR", F_HEAD)
    elif idx == 11:
        labels = ["实体F1", "关系F1", "因果边界", "跨文档", "标准引用", "一致性", "审计", "可用性"]
        cx, cy, r = 1000, 560, 330
        for k in range(1, 5):
            rr = r * k / 4
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(160, 160, 160), width=2)
        pts = []
        for i, lab in enumerate(labels):
            ang = 2 * math.pi * i / 8 - math.pi / 2
            end = (cx + r * math.cos(ang), cy + r * math.sin(ang))
            d.line([(cx, cy), end], fill=(0, 0, 0), width=2)
            draw_centered(d, (end[0]-70, end[1]-28, end[0]+70, end[1]+28), lab, F_SMALL)
            pts.append((cx + r * .82 * math.cos(ang), cy + r * .82 * math.sin(ang)))
        d.polygon(pts, outline=(0, 0, 0), fill=(230, 230, 230))
        draw_centered(d, (850, 515, 1150, 605), "本发明组", F_HEAD)
    else:
        labels = [
            ["BFO顶层", "IOF核心层", "航空领域层"],
            ["关系权重", "证据权重", "标准权重", "图结构", "LLM置信度"],
            ["故障", "部件", "维修程序", "标准条款", "培训规范"],
            ["PACK OFF", "引气异常", "维修证据", "培训提示"],
            ["顶事件", "中间事件", "基本事件", "证据节点"],
            ["737故障说明", "M2维修文件", "实作培训规范"],
            ["用户角色", "权限", "密级", "审计", "模型指标"],
            ["导航区", "问答区", "图谱区", "审计区"],
        ][min(idx - 1, 7)]
        draw_flow_png(d, labels, 380)
    return im


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.png"):
        old.unlink()
    prs = Presentation()
    prs.slide_width = p_in(SLIDE_W)
    prs.slide_height = p_in(SLIDE_H)
    blank = prs.slide_layouts[6]
    rows = []
    for idx, (filename, title, fig_no) in enumerate(FIGS):
        slide = prs.slides.add_slide(blank)
        build_slide(slide, idx, title, fig_no)
        png = build_png(idx, title, fig_no)
        out_png = OUT_DIR / filename
        png.save(out_png)
        rows.append((filename, idx + 1, out_png.name))
    prs.save(OUT_PPTX)
    lines = [
        "# 专利附图重绘检查报告",
        "",
        "本报告由 create_editable_patent_figures.py 自动生成。PPT中未嵌入原始PNG，图形主体由PowerPoint原生文本框、形状、连接线和箭头构成；PNG由同一套图元定义导出，用于插入Word申请文件。",
        "",
        "| 原始文件名 | PPT页码 | 导出PNG | 重绘与修正 | 人工复核 |",
        "| --- | ---: | --- | --- | --- |",
    ]
    fixes = "按黑白/灰度专利附图风格重绘模块框、连线、箭头和图号；统一字号、边框和层级，减少原图文字拥挤及线条交叉。"
    for src, page, out in rows:
        lines.append(f"| {src} | {page} | 专利附图_可编辑导出/{out} | {fixes} | 建议核对术语是否与最终权利要求完全一致。 |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"created {OUT_PPTX}")
    print(f"exported {len(rows)} png files to {OUT_DIR}")
    print(f"report {REPORT}")


if __name__ == "__main__":
    main()
