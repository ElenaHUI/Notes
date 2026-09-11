from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn

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

OUT = "问题一键上报-流程框图.pptx"
LIGHT = RGBColor(0xF5, 0xF6, 0xF8)
GREY = RGBColor(0xA8, 0xAE, 0xB6)
L_SIZE = 13

MAIN = [
    ("01 · 用户终端", ["在 opencode 中执行 /report", "填写问题描述与复现步骤"]),
    ("02 · opencode 插件", ["收集诊断信息与运行上下文", "敏感信息脱敏处理", "HTTP 上报到服务端"]),
    (
        "03 · app-notifier 服务端",
        ["接收 POST /alert/issue/report", "落盘归档 + 写入 MySQL", "生成详情链接并推送钉钉"],
    ),
    ("04 · 钉钉问题上报群", ["Markdown 卡片 + @ 责任人", "点击链接直达详情页"]),
]

STORE = ("数据落库", ["JSON 归档到 issue-reports 目录", "MySQL 写入 issue_report 表"])
FRONT = ("web-mgmt 前端 · React", ["列表页：筛选 / 分页 / 跳转", "详情页：日志与状态切换"])
NOTE = (
    "链路要点",
    ["客户端完成脱敏，服务端与数据库不落敏感信息", "钉钉消息内嵌详情链接，上报 → 查看形成闭环"],
)


def arrow(slide, x1, y1, x2, y2, color=ORANGE, width=28575, dash=False, head="med"):
    cn = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    cn.line.color.rgb = color
    cn.line.width = Emu(width)
    ln = cn.line._get_or_add_ln()
    if dash:
        ln.append(ln.makeelement(qn("a:prstDash"), {"val": "dash"}))
    if head:
        ln.append(
            ln.makeelement(
                qn("a:tailEnd"), {"type": "triangle", "w": head, "len": head}
            )
        )
    return cn


def label(slide, x, y, w, text, align=PP_ALIGN.CENTER):
    tf = txbox(slide, x, y, w, 0.36)
    run(tf.paragraphs[0], text, L_SIZE, False, MUTED, align)


def main():
    prs = Presentation(SRC)
    slide = prs.slides.add_slide(prs.slide_masters[0].slide_layouts[1])

    tf = txbox(slide, 1.55, 1.3, 23.56, 0.55)
    run(tf.paragraphs[0], "WORKFLOW", 22, True, ORANGE)

    tf = txbox(slide, 1.55, 1.85, 23.56, 1.2)
    run(tf.paragraphs[0], "问题一键上报 · 端到端链路", 52, True, DARK)

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
        "opencode 插件 → app-notifier 服务端 → 钉钉群 → web-mgmt 前端",
        20,
        False,
        SUB,
    )

    tf = txbox(slide, 23.11, 14.22, 2.0, 0.5)
    run(tf.paragraphs[0], "01", 18, False, MUTED, PP_ALIGN.RIGHT)

    left, total, gap = 1.55, 23.56, 1.32
    cw = (total - gap * 3) / 4
    xs = [left + i * (cw + gap) for i in range(4)]

    main_h = max(card_height(cw, t, b) for t, b in MAIN)
    side_h = card_height(cw, *STORE)
    store_y = 5.05
    main_y = store_y + side_h + 0.705
    front_y = main_y + main_h + 0.70
    mid_y = main_y + main_h / 2

    for x, (title, bullets) in zip(xs, MAIN):
        add_card(slide, x, main_y, cw, main_h, title, bullets)

    for i, text in enumerate(["/report", "POST 上报", "推送通知"]):
        x1 = xs[i] + cw + 0.12
        x2 = xs[i + 1] - 0.12
        arrow(slide, x1, mid_y, x2, mid_y)
        label(slide, xs[i] + cw, mid_y - 0.46, gap, text)

    store = add_card(slide, xs[2], store_y, cw, side_h, *STORE)
    store.fill.fore_color.rgb = LIGHT
    store_cx = xs[2] + cw / 2
    arrow(slide, store_cx, main_y - 0.12, store_cx, store_y + side_h + 0.12, GREY, 22225)
    label(slide, store_cx + 0.2, main_y - 0.62, 2.4, "落盘 / 入库", PP_ALIGN.LEFT)

    front = add_card(slide, xs[3], front_y, cw, side_h, *FRONT)
    front.fill.fore_color.rgb = LIGHT
    front_cx = xs[3] + cw / 2
    arrow(slide, front_cx, main_y + main_h + 0.12, front_cx, front_y - 0.12, GREY, 22225)
    label(slide, front_cx + 0.2, main_y + main_h + 0.16, 2.4, "跳转详情页", PP_ALIGN.LEFT)

    back_y = front_y + side_h / 2
    arrow(slide, xs[3] - 0.12, back_y, store_cx, back_y, GREY, 22225, dash=True, head=None)
    arrow(slide, store_cx, back_y, store_cx, main_y + main_h + 0.12, GREY, 22225, dash=True, head="lg")
    label(slide, store_cx, back_y - 0.44, xs[3] - store_cx, "GET /alert/issue/{id}")

    note = add_card(slide, xs[0], front_y, 7.0, side_h, *NOTE)
    note.fill.fore_color.rgb = LIGHT
    for r in note.text_frame.paragraphs[0].runs:
        r.font.color.rgb = DARK

    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst)[:-1]:
        prs.part.drop_rel(sldId.rId)
        sldIdLst.remove(sldId)

    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
