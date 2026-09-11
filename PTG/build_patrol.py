from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from build_timeline import (
    SRC,
    ORANGE,
    DARK,
    MUTED,
    SUB,
    WHITE,
    add_card,
    card_height,
    run,
    txbox,
)
from build_flow import LIGHT, arrow, label
from build_warmup import band, strip

OUT = "值守Agent-巡检流程框图.pptx"

STEPS = [
    ("01 · 定时触发", ["热路径 10min 增量巡检", "兜底每日回看 24h"]),
    ("02 · 取 checkpoint", ["state 读上次处理位点", "仅处理增量，避免重复回复"]),
    ("03 · dws 拉群消息", ["按群拉取新增消息", "无新消息即短路结束"]),
    ("04 · classify 过滤分类", ["剔除噪声，筛出待办问题", "无待办即短路归档"]),
    ("05 · 读 faq.json + 读图", ["加载文档知识索引", "识别截图与报错信息"]),
]

SHORT = ("短路退出", ["无新消息 → 直接结束", "无待办 → 归档后结束"])

DECIDE = "逐条判定 · LLM 对照 faq.json 与截图，逐条给出结论并选定处置动作"

BRANCHES = [
    (
        "命中文档",
        "按文档原文回复",
        ["命中即引用 faq.json 原文片段", "不做自由生成，避免答案跑偏"],
    ),
    (
        "未命中",
        "转人工兜底",
        ["@ 值班同学接手并跟进处理", "未覆盖问题回灌 faq 知识库"],
    ),
    (
        "模型不可用",
        "DING 告警负责人",
        ["模型或消息链路异常时触发", "DING 到责任人，保证不漏单"],
    ),
]

CLOSE = (
    "收尾",
    "归档问答 → commit 推进 checkpoint → 本轮结束；短路分支跳过判定直接归档，"
    "重构后单轮耗时稳定在 2-3min",
)


def pill(slide, x, y, w, h, text):
    sh = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    sh.adjustments[0] = 0.5
    sh.fill.solid()
    sh.fill.fore_color.rgb = ORANGE
    sh.line.fill.background()
    sh.shadow.inherit = False
    tf = sh.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    run(tf.paragraphs[0], text, 20, True, WHITE, PP_ALIGN.CENTER)
    return sh


# A dashed line's prstDash also shreds the arrowhead outline, so the final leg
# carrying the head is drawn solid.
def dashed_down(slide, x, y1, y2, color):
    tip = y2 - 0.20
    arrow(slide, x, y1, x, tip, color, 22225, True, None)
    arrow(slide, x, tip, x, y2, color, 22225, False, "med")


def main():
    prs = Presentation(SRC)
    slide = prs.slides.add_slide(prs.slide_masters[0].slide_layouts[1])

    tf = txbox(slide, 1.55, 1.3, 23.56, 0.55)
    run(tf.paragraphs[0], "PATROL LOOP", 22, True, ORANGE)

    tf = txbox(slide, 1.55, 1.85, 23.56, 1.2)
    run(tf.paragraphs[0], "红区值守 Agent · 单轮巡检流程", 52, True, DARK)

    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(1.55), Inches(3.16), Inches(2.1), Inches(0.06)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = ORANGE
    bar.line.fill.background()
    bar.shadow.inherit = False

    tf = txbox(slide, 1.55, 3.52, 23.56, 0.5)
    run(
        tf.paragraphs[0],
        "定时触发 → 拉取分类 → 逐条判定 → 分支处置 → 归档并推进 checkpoint",
        20,
        False,
        SUB,
    )

    tf = txbox(slide, 23.11, 14.22, 2.0, 0.5)
    run(tf.paragraphs[0], "01", 18, False, MUTED, PP_ALIGN.RIGHT)

    left, total = 1.55, 23.56
    gap5 = 0.70
    cw5 = (total - gap5 * 4) / 5
    xs = [left + i * (cw5 + gap5) for i in range(5)]

    y1 = 5.05
    h1 = max(card_height(cw5, t, b) for t, b in STEPS)
    row1_bottom = y1 + h1

    band(slide, left, y1 - 0.55, "采集与准备")

    for x, (title, bullets) in zip(xs, STEPS):
        add_card(slide, x, y1, cw5, h1, title, bullets)

    mid1 = y1 + h1 / 2
    for i in range(4):
        arrow(slide, xs[i] + cw5 + 0.12, mid1, xs[i + 1] - 0.12, mid1)

    bx0 = xs[1]
    region = total - (cw5 + gap5)
    gap3 = 1.32
    cw3 = (region - gap3 * 2) / 3
    bxs = [bx0 + i * (cw3 + gap3) for i in range(3)]

    y_dec = row1_bottom + 0.95
    dec_h = 0.90
    y_br = y_dec + dec_h + 1.00
    h_br = max(card_height(cw3, t, b) for _, t, b in BRANCHES)
    y_close = y_br + h_br + 0.75

    pill(slide, bx0, y_dec, region, dec_h, DECIDE)

    hand_x = xs[4] + cw5 / 2
    arrow(slide, hand_x, row1_bottom + 0.12, hand_x, y_dec - 0.12)

    for bx, (edge, title, bullets) in zip(bxs, BRANCHES):
        add_card(slide, bx, y_br, cw3, h_br, title, bullets)
        bcx = bx + cw3 / 2
        arrow(slide, bcx, y_dec + dec_h + 0.12, bcx, y_br - 0.12)
        label(slide, bcx + 0.24, y_dec + dec_h + 0.28, 3.2, edge, PP_ALIGN.LEFT)
        arrow(slide, bcx, y_br + h_br + 0.12, bcx, y_close - 0.12, MUTED, 22225)

    short = add_card(slide, left, y_dec, cw5, card_height(cw5, *SHORT), *SHORT)
    short.fill.fore_color.rgb = LIGHT
    for r in short.text_frame.paragraphs[0].runs:
        r.font.color.rgb = DARK
    short_cx = left + cw5 / 2
    short_bottom = y_dec + card_height(cw5, *SHORT)

    y_h = row1_bottom + 0.45
    for i in (2, 3):
        cx = xs[i] + cw5 / 2
        arrow(slide, cx, row1_bottom + 0.12, cx, y_h, MUTED, 22225, True, None)
    arrow(slide, xs[3] + cw5 / 2, y_h, short_cx, y_h, MUTED, 22225, True, None)
    dashed_down(slide, short_cx, y_h, y_dec - 0.12, MUTED)
    label(
        slide,
        (short_cx + xs[3] + cw5 / 2) / 2 - 2.2,
        y_h + 0.10,
        4.4,
        "无新消息 / 无待办",
        PP_ALIGN.CENTER,
    )

    dashed_down(slide, short_cx, short_bottom + 0.12, y_close - 0.12, MUTED)

    strip(slide, left, y_close, total, 0.95, *CLOSE)

    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst)[:-1]:
        prs.part.drop_rel(sldId.rId)
        sldIdLst.remove(sldId)

    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
