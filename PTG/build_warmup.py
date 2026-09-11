from pptx import Presentation
from pptx.util import Inches, Pt, Emu
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
    PAD_L,
    add_card,
    card_height,
    run,
    txbox,
)
from build_flow import LIGHT, arrow, label

OUT = "Warmup-录制回放流程框图.pptx"

ROW1 = [
    ("01 · 真实请求", ["OpenCode / QwenCode 日常调用", "多轮对话 + tool_calls + 长代码"]),
    ("02 · litellm-proxy 抓取", ["按 API Key / User ID 筛选", "落 capture JSON，含完整 body"]),
    ("03 · 导出 warmup.jsonl", ["GET /capture/export-warmup", "去重 / 限长，按 tokens 降序"]),
]

NOTE = ("数据要点", ["旧：1 万字静态纯文本", "新：多轮 + tool_calls 长上下文"])

ROW2 = [
    (
        "引擎后台启动",
        ["推理引擎进程后台拉起", "monitor_and_warmup.sh 接管", "端口三级回退 → LLM_PORT"],
    ),
    (
        "Step 1 · 健康检查等待",
        ["轮询 /health，间隔 10s", "总超时 1200s", "PID 消失即判定启动失败"],
    ),
    (
        "Step 2 · 真实请求回放",
        ["逐行读 JSONL，注入 model", "串行发 /v1/chat/completions", "max_tokens 上限 2048"],
    ),
    (
        "Step 3 · 就绪标记",
        ["touch /tmp/warmup-done", "readinessProbe 通过 → Ready", "Pod 开始接入真实流量"],
    ),
]

GUARD = (
    "兜底原则",
    "warmup 失败仅打印 WARNING，始终 touch 就绪标记；数据缺失回退旧版纯文本，"
    "WARMUP_SKIP=true 可整段跳过 —— 任何异常都不阻塞 Pod Ready",
)


def band(slide, x, y, text):
    sq = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(x), Inches(y + 0.12), Inches(0.14), Inches(0.14)
    )
    sq.fill.solid()
    sq.fill.fore_color.rgb = ORANGE
    sq.line.fill.background()
    sq.shadow.inherit = False
    tf = txbox(slide, x + 0.32, y, 12.0, 0.42)
    run(tf.paragraphs[0], text, 19, True, DARK)


def strip(slide, x, y, w, h, lead, text):
    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    box.adjustments[0] = 0.12
    box.fill.solid()
    box.fill.fore_color.rgb = LIGHT
    box.line.color.rgb = BORDER
    box.line.width = Emu(15875)
    box.shadow.inherit = False
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(PAD_L)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    run(p, lead + "　", 18, True, ORANGE)
    run(p, text, 18, False, BODY)


def main():
    prs = Presentation(SRC)
    slide = prs.slides.add_slide(prs.slide_masters[0].slide_layouts[1])

    tf = txbox(slide, 1.55, 1.3, 23.56, 0.55)
    run(tf.paragraphs[0], "WARM UP", 22, True, ORANGE)

    tf = txbox(slide, 1.55, 1.85, 23.56, 1.2)
    run(tf.paragraphs[0], "模型启动预热 · 真实请求录制回放", 52, True, DARK)

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
        "录制真实流量 → 导出 JSONL → Pod 启动逐条回放 → 就绪门控",
        20,
        False,
        SUB,
    )

    tf = txbox(slide, 23.11, 14.22, 2.0, 0.5)
    run(tf.paragraphs[0], "01", 18, False, MUTED, PP_ALIGN.RIGHT)

    left, total, gap = 1.55, 23.56, 1.32
    cw = (total - gap * 3) / 4
    xs = [left + i * (cw + gap) for i in range(4)]

    h1 = max(card_height(cw, t, b) for t, b in ROW1 + [NOTE])
    h2 = max(card_height(cw, t, b) for t, b in ROW2)
    y1 = 5.10
    y2 = 8.10

    band(slide, left, y1 - 0.55, "录制阶段 · 一次性 / 定期")
    band(slide, left, y2 - 0.55, "启动阶段 · 每次 Pod 启动 · monitor_and_warmup.sh")

    for x, (title, bullets) in zip(xs, ROW1):
        add_card(slide, x, y1, cw, h1, title, bullets)

    note = add_card(slide, xs[3], y1, cw, h1, *NOTE)
    note.fill.fore_color.rgb = LIGHT
    for r in note.text_frame.paragraphs[0].runs:
        r.font.color.rgb = DARK

    for x, (title, bullets) in zip(xs, ROW2):
        add_card(slide, x, y2, cw, h2, title, bullets)

    mid1 = y1 + h1 / 2
    for i in range(2):
        arrow(slide, xs[i] + cw + 0.12, mid1, xs[i + 1] - 0.12, mid1)

    mid2 = y2 + h2 / 2
    for i in range(3):
        arrow(slide, xs[i] + cw + 0.12, mid2, xs[i + 1] - 0.12, mid2)

    hand_x = xs[2] + cw / 2
    arrow(slide, hand_x, y1 + h1 + 0.12, hand_x, y2 - 0.12)
    label(
        slide,
        hand_x + 0.24,
        y1 + h1 + 0.28,
        3.3,
        "/warmup-data/warmup/{model}.jsonl",
        PP_ALIGN.LEFT,
    )

    strip(slide, left, y2 + h2 + 0.70, total, 0.95, *GUARD)

    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst)[:-1]:
        prs.part.drop_rel(sldId.rId)
        sldIdLst.remove(sldId)

    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
