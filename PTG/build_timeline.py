import math

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

SRC = "PTG实习工作总结-v2.pptx"
OUT = "闫一慧-周会工作时间轴.pptx"

ORANGE = RGBColor(0xFF, 0x50, 0x0C)
DARK = RGBColor(0x3C, 0x41, 0x48)
BODY = RGBColor(0x53, 0x58, 0x5F)
MUTED = RGBColor(0x8A, 0x90, 0x99)
SUB = RGBColor(0x6E, 0x74, 0x7C)
BORDER = RGBColor(0xE1, 0xE4, 0xE8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Microsoft YaHei"

T_SIZE, B_SIZE = 19, 16
PAD_L, PAD_T, PAD_B = 0.26, 0.28, 0.34
MAR_L = 0.19

# 每周：主线项目排在轴线上方，其余项目分别列在轴线下方
WEEKS = [
    {
        "date": "07.29",
        "up": [
            (
                "Opencode 上报 · 服务端",
                ["/report 全流程打通", "建 issue_report 数据表", "3 个上报 API 落地"],
            )
        ],
        "down": [
            ("上报链路联调", ["落库与日志数据核对", "钉钉群通知触达验证"]),
        ],
    },
    {
        "date": "08.05",
        "up": [
            (
                "Opencode 上报 · 前端",
                ["列表页：筛选与分页跳转", "详情页：日志与状态切换", "dev / prod 双环境验证"],
            )
        ],
        "down": [
            ("插件安装兼容性修复", ["autoupdate 导致版本降级", "加校验并关闭自动更新"]),
        ],
    },
    {
        "date": "08.12",
        "up": [
            (
                "Dynamo 监控链路搭建",
                ["打通 v1.3.0 采集与展示", "适配两块核心看板", "ServiceMonitor 去重"],
            )
        ],
        "down": [
            ("上报时间偏移修复", ["DATETIME 未存时区", "落库时间差 8 小时"]),
        ],
    },
    {
        "date": "08.19",
        "up": [
            (
                "红区 DSH 安装部署",
                ["npm 与 dsh.sh 两套方案", "自解压包内嵌 Node", "共用机器动态分配端口"],
            )
        ],
        "down": [
            ("DSH 安全特性梳理", ["三级沙箱与权限升级审批", "仅放通 loopback 访问"]),
        ],
    },
    {
        "date": "08.26",
        "up": [
            (
                "DeepSeek PD 分离部署",
                ["DGD 替代 Deployment", "修复 RDMA 初始化失败", "配置调优后吞吐提升明显"],
            )
        ],
        "down": [
            ("红区 DSH 升级", ["升级 0.1.1-rc.1 并打包", "自动写入 Tone 配置"]),
            ("值守 Agent 巡检重构", ["热路径 10min / 兜底每日", "单轮耗时降到 2-3min"]),
        ],
    },
    {
        "date": "09.03",
        "up": [
            (
                "Dynamo 监控适配",
                ["适配 PD 分离与混合部署", "支持跨 namespace 筛选", "补齐 KV 缓存与吞吐指标"],
            ),
        ],
        "down": [
            ("值守 Agent 方案沉淀", ["输出巡检与告警方案文档", "沉淀部署与排障 SOP"]),
        ],
    },
]


def em_len(text):
    return sum(1.0 if ord(c) > 0x2E80 else 0.5 for c in text)


def wrap_lines(text, size, usable):
    return max(1, math.ceil(em_len(text) * size / usable - 0.06))


def card_height(cw, title, items):
    usable = (cw - 2 * PAD_L) * 72
    h = wrap_lines(title, T_SIZE, usable) * T_SIZE * 1.15 + 8
    for it in items:
        h += wrap_lines("· " + it, B_SIZE, usable - MAR_L * 72) * B_SIZE * 1.3 + 8
    return h / 72 + PAD_T + PAD_B


def txbox(slide, x, y, w, h):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def run(par, text, size, bold=False, color=DARK, align=PP_ALIGN.LEFT):
    par.alignment = align
    r = par.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.name = FONT
    r.font.color.rgb = color
    rPr = r._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.makeelement(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}"
            + tag.split(":")[1],
            {"typeface": FONT},
        )
        rPr.append(el)
    return r


def hanging(par, amount=MAR_L):
    pPr = par._p.get_or_add_pPr()
    marL = int(amount * 914400)
    pPr.set("marL", str(marL))
    pPr.set("indent", str(-marL))


def add_card(slide, x, y, w, h, title, items):
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    card.adjustments[0] = 0.04
    card.fill.solid()
    card.fill.fore_color.rgb = WHITE
    card.line.color.rgb = BORDER
    card.line.width = Emu(15875)
    card.shadow.inherit = False

    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(PAD_L)
    tf.margin_top = Inches(PAD_T)
    tf.margin_bottom = Inches(PAD_B)
    tf.vertical_anchor = MSO_ANCHOR.TOP

    p = tf.paragraphs[0]
    p.line_spacing = 1.15
    p.space_after = Pt(8)
    run(p, title, T_SIZE, True, ORANGE)

    for it in items:
        p = tf.add_paragraph()
        p.line_spacing = 1.3
        p.space_after = Pt(6)
        hanging(p)
        run(p, "· ", B_SIZE, True, ORANGE)
        run(p, it, B_SIZE, False, BODY)
    return card


def main():
    prs = Presentation(SRC)
    slide = prs.slides.add_slide(prs.slide_masters[0].slide_layouts[1])

    tf = txbox(slide, 1.55, 1.3, 23.56, 0.55)
    run(tf.paragraphs[0], "TIMELINE", 22, True, ORANGE)

    tf = txbox(slide, 1.55, 1.85, 23.56, 1.2)
    run(tf.paragraphs[0], "周会视角 · 六周工作时间轴", 52, True, DARK)

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
        "07.29 — 09.03 · 主线：模型部署 / 可观测 / 端侧 / 运维 Agent",
        20,
        False,
        SUB,
    )

    tf = txbox(slide, 23.11, 14.22, 2.0, 0.5)
    run(tf.paragraphs[0], "01", 18, False, MUTED, PP_ALIGN.RIGHT)

    left, total, gap = 1.55, 23.56, 0.3
    cw = (total - gap * (len(WEEKS) - 1)) / len(WEEKS)
    axis_y = 8.62
    pill_w, pill_h = 1.55, 0.66
    up_bottom = axis_y - pill_h / 2 - 0.3
    down_top = axis_y + pill_h / 2 + 0.3
    stack_gap = 0.22

    axis = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(axis_y), Inches(total), Inches(0.045)
    )
    axis.fill.solid()
    axis.fill.fore_color.rgb = BORDER
    axis.line.fill.background()
    axis.shadow.inherit = False

    for i, wk in enumerate(WEEKS):
        x = left + i * (cw + gap)
        cx = x + cw / 2

        y = up_bottom
        for title, items in reversed(wk["up"]):
            h = card_height(cw, title, items)
            y -= h
            add_card(slide, x, y, cw, h, title, items)
            y -= stack_gap

        y = down_top
        for title, items in wk["down"]:
            h = card_height(cw, title, items)
            add_card(slide, x, y, cw, h, title, items)
            y += h + stack_gap

        pill = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(cx - pill_w / 2),
            Inches(axis_y + 0.0225 - pill_h / 2),
            Inches(pill_w),
            Inches(pill_h),
        )
        pill.adjustments[0] = 0.5
        pill.fill.solid()
        pill.fill.fore_color.rgb = ORANGE
        pill.line.fill.background()
        pill.shadow.inherit = False
        ptf = pill.text_frame
        ptf.margin_left = ptf.margin_right = 0
        ptf.margin_top = ptf.margin_bottom = 0
        ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
        run(ptf.paragraphs[0], wk["date"], 24, True, WHITE, PP_ALIGN.CENTER)

    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst)[:-1]:
        prs.part.drop_rel(sldId.rId)
        sldIdLst.remove(sldId)

    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
