from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from build_timeline import (
    SRC,
    ORANGE,
    DARK,
    BODY,
    MUTED,
    SUB,
    BORDER,
    WHITE,
    PAD_L,
    add_card,
    card_height,
    run,
    txbox,
)
from build_flow import LIGHT, arrow
from build_warmup import band, strip

OUT = "ModelExpress-P2P权重分发-验证.pptx"
IMG = "asset/mx-p2p-transfer-log.png"

# ---- slide 1 content ----
TRAD = ["共享存储 / PVC", "读取原始权重", "构造 · 量化 · 加载", "写入 PPU 显存", "Pod Ready"]
P2P = ["Source PPU 显存", "NIXL / UCX RDMA", "Target PPU 显存", "Pod Ready"]

ROLES = [
    ("MX Server · 控制面", ["元数据登记 / 查询 / source 健康", "gRPC :8001，不搬运权重数据"]),
    ("Kubernetes CRD", ["持久化 ModelMetadata", "记录可用 source 供发现"]),
    ("Source ↔ Target · 数据面", ["NIXL / UCX RDMA 显存直传", "69GB 权重不经 MX Server"]),
]

VALUE = (
    "核心价值",
    "跳过共享存储读取与重复权重加载；控制面（MX Server 管元数据）与数据面"
    "（Source↔Target RDMA 直传）解耦 —— 扩容更快、存储 I/O 压力更低",
)

# ---- slide 2 content ----
STATS = [
    ("69.35", "GB", "权重传输量"),
    ("7.97", "s", "RDMA 传输耗时"),
    ("69.6", "Gbps", "传输吞吐"),
    ("2017", "", "传输张量数"),
]

GAINS = [
    ("权重搬运耗时", ["磁盘加载 371s → P2P 7.97s", "约 46× 加速"]),
    ("模型初始化", ["425s → 63.2s", "约 6.7× 加速"]),
    ("初始化耗时下降", ["约 85%", "扩容启动大幅缩短"]),
]

CONCLUSION = (
    "结论",
    "P2P 显存直传能力与性能已验证；适用增量扩容 / 故障恢复 / 滚动升级（需存活 Source），"
    "冷启动无 source 时回退磁盘。后续完善推理正确性与 ModelMetadata 自动回收",
)

FONT = "Microsoft YaHei"


def header(slide, en, cn, sub, page):
    tf = txbox(slide, 1.55, 1.30, 23.56, 0.55)
    run(tf.paragraphs[0], en, 22, True, ORANGE)
    tf = txbox(slide, 1.55, 1.85, 23.56, 1.20)
    run(tf.paragraphs[0], cn, 52, True, DARK)
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(1.55), Inches(3.16), Inches(2.1), Inches(0.06)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = ORANGE
    bar.line.fill.background()
    bar.shadow.inherit = False
    tf = txbox(slide, 1.55, 3.52, 23.56, 0.5)
    run(tf.paragraphs[0], sub, 20, False, SUB)
    tf = txbox(slide, 23.11, 14.22, 2.0, 0.5)
    run(tf.paragraphs[0], page, 18, False, MUTED, PP_ALIGN.RIGHT)


def node(slide, x, y, w, h, text, fill, txt, border, size=15):
    sh = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    sh.adjustments[0] = 0.12
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if border is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = border
        sh.line.width = Emu(15875)
    sh.shadow.inherit = False
    tf = sh.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.1)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    run(tf.paragraphs[0], text, size, True, txt, PP_ALIGN.CENTER)
    return sh


def chain(slide, y, nodes, fill, txt, border, arrow_color):
    left, total = 1.55, 23.56
    gap = 1.30
    n = len(nodes)
    w = (total - gap * (n - 1)) / n
    h = 0.92
    xs = [left + i * (w + gap) for i in range(n)]
    for x, text in zip(xs, nodes):
        node(slide, x, y, w, h, text, fill, txt, border)
    mid = y + h / 2
    for i in range(n - 1):
        arrow(slide, xs[i] + w + 0.12, mid, xs[i + 1] - 0.12, mid, arrow_color)
    return h


def tag(slide, x, y, text, color):
    tf = txbox(slide, x, y, 3.2, 0.42)
    run(tf.paragraphs[0], text, 17, True, color)


def stat(slide, x, y, w, h, value, unit, label):
    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    box.adjustments[0] = 0.06
    box.fill.solid()
    box.fill.fore_color.rgb = LIGHT
    box.line.color.rgb = BORDER
    box.line.width = Emu(15875)
    box.shadow.inherit = False
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.2)
    tf.margin_top = Inches(0.24)
    tf.margin_bottom = Inches(0.2)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = value
    r.font.size = Pt(46)
    r.font.bold = True
    r.font.name = FONT
    r.font.color.rgb = ORANGE
    _ea(r)
    if unit:
        r2 = p.add_run()
        r2.text = " " + unit
        r2.font.size = Pt(22)
        r2.font.bold = True
        r2.font.name = FONT
        r2.font.color.rgb = ORANGE
        _ea(r2)
    p2 = tf.add_paragraph()
    p2.space_before = Pt(6)
    run(p2, label, 16, False, BODY, PP_ALIGN.CENTER)


def _ea(r):
    rPr = r._r.get_or_add_rPr()
    for tagn in ("a:ea", "a:cs"):
        el = rPr.makeelement(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}"
            + tagn.split(":")[1],
            {"typeface": FONT},
        )
        rPr.append(el)


def slide1(prs):
    slide = prs.slides.add_slide(prs.slide_masters[0].slide_layouts[1])
    header(
        slide,
        "MODELEXPRESS · P2P",
        "ModelExpress P2P 权重分发 · 方案与架构",
        "GLM-5.3 INT8 · TP=16 · 1P1D Dynamo + TensorRT-LLM · NIXL/UCX RDMA 显存直传",
        "01",
    )

    band(slide, 1.55, 4.35, "扩容路径对比 · 传统磁盘加载 vs P2P 显存直传")

    y_a = 5.05
    tag(slide, 1.55, y_a - 0.02, "传统", MUTED)
    h_a = chain(slide, y_a + 0.40, TRAD, WHITE, DARK, BORDER, MUTED)

    y_b = y_a + 0.40 + h_a + 0.75
    tag(slide, 1.55, y_b - 0.42, "P2P", ORANGE)
    node_orange = RGBColor(0xFF, 0xEC, 0xE2)
    chain(slide, y_b, P2P, node_orange, RGBColor(0xB8, 0x3A, 0x08), ORANGE, ORANGE)

    band(slide, 1.55, 8.55, "控制面 / 数据面职责分离")
    left, total, gap = 1.55, 23.56, 1.0
    cw = (total - gap * 2) / 3
    xs = [left + i * (cw + gap) for i in range(3)]
    hr = max(card_height(cw, t, b) for t, b in ROLES)
    for x, (t, b) in zip(xs, ROLES):
        add_card(slide, x, 9.25, cw, hr, t, b)

    strip(slide, left, 9.25 + hr + 0.70, total, 1.05, *VALUE)


def slide2(prs):
    slide = prs.slides.add_slide(prs.slide_masters[0].slide_layouts[1])
    header(
        slide,
        "VALIDATION · RESULT",
        "ModelExpress P2P · 验证结果与收益",
        "新 Decode Pod 发现 Source 后经 RDMA 显存直传 —— 传输日志（rank0）为最终结果",
        "02",
    )

    band(slide, 1.55, 4.35, "P2P 传输日志 · Transfer complete")
    img_w = 23.56
    img_h = img_w * 314 / 2324
    img_y = 4.80
    slide.shapes.add_picture(
        IMG, Inches(1.55), Inches(img_y), Inches(img_w), Inches(img_h)
    )

    y_stat = img_y + img_h + 0.45
    left, total, gap = 1.55, 23.56, 0.6
    sw = (total - gap * 3) / 4
    xs = [left + i * (sw + gap) for i in range(4)]
    for x, (v, u, lb) in zip(xs, STATS):
        stat(slide, x, y_stat, sw, 1.60, v, u, lb)

    y_band = y_stat + 1.60 + 0.45
    band(slide, 1.55, y_band, "性能收益 · 对比传统磁盘加载")
    gap2 = 1.0
    cw = (total - gap2 * 2) / 3
    xs3 = [left + i * (cw + gap2) for i in range(3)]
    hr = max(card_height(cw, t, b) for t, b in GAINS)
    y_cards = y_band + 0.65
    for x, (t, b) in zip(xs3, GAINS):
        add_card(slide, x, y_cards, cw, hr, t, b)

    strip(slide, left, y_cards + hr + 0.45, total, 0.95, *CONCLUSION)


def main():
    prs = Presentation(SRC)
    slide1(prs)
    slide2(prs)
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst)[:-2]:
        prs.part.drop_rel(sldId.rId)
        sldIdLst.remove(sldId)
    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
