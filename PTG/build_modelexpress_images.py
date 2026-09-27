from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from build_timeline import SRC, ORANGE, DARK, BODY, MUTED, SUB, BORDER, WHITE, run, txbox
from build_flow import LIGHT, arrow
from build_warmup import band, strip

OUT = "ModelExpress-镜像清单.pptx"
FONT = "Microsoft YaHei"
MONO = "Consolas"
PALE_ORANGE = RGBColor(0xFF, 0xEC, 0xE2)
ORANGE_DARK = RGBColor(0xB8, 0x3A, 0x08)

IMAGES = [
    (
        "MX Server",
        "0.5.1",
        "管理 Source 元数据、处理 Worker 注册与查询",
        "art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/\nmodelexpress-server:0.5.1",
    ),
    (
        "Worker Client",
        "MX 0.5.0",
        "Prefill / Decode 运行；集成 TRT-LLM、NIXL 与 MX Client",
        "art.eng.t-head.cn/ptgai-docker_ai-service/ai-tmp/\nmx-glm53-trtllm:mx0.5.0-trtllm",
    ),
    (
        "Holmes Base",
        "基础镜像",
        "提供 PPU SDK、PyTorch、CUDA 与 TRT-LLM 基础能力",
        "reg.docker.alibaba-inc.com/ai-tmp/holmes:\nllm-torch2.9-cuda12.9-ubuntu24.04-py312-dpskv4-ppu202609121210",
    ),
]

STEPS = [
    ("01", "安装 CRD", "注册 MX 元数据类型"),
    ("02", "部署 MX Server", "foundation · :8001"),
    ("03", "构建 Worker 镜像", "Holmes + MX Client"),
    ("04", "配置 Prefill / Decode", "Engine Args + envs"),
    ("05", "扩容验证", "1P1D → 1P2D"),
]


def add_ea(run_obj, font=FONT):
    rpr = run_obj._r.get_or_add_rPr()
    for tag in ("ea", "cs"):
        el = rpr.makeelement(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}" + tag,
            {"typeface": font},
        )
        rpr.append(el)


def text_run(p, text, size, bold=False, color=DARK, font=FONT, align=PP_ALIGN.LEFT):
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.name = font
    r.font.color.rgb = color
    add_ea(r, font)
    return r


def rect(slide, x, y, w, h, fill, line=BORDER, radius=True):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h),
    )
    if radius:
        shape.adjustments[0] = 0.04
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Emu(15875)
    shape.shadow.inherit = False
    return shape


def textbox(slide, x, y, w, h, text, size, bold=False, color=DARK, font=FONT,
            align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.MIDDLE, ml=0.12, mr=0.12):
    tf = txbox(slide, x, y, w, h)
    tf.margin_left = Inches(ml)
    tf.margin_right = Inches(mr)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = valign
    tf.word_wrap = True
    text_run(tf.paragraphs[0], text, size, bold, color, font, align)
    return tf


def lines(slide, x, y, w, h, items, size=13, color=BODY, font=FONT, gap=2):
    tf = txbox(slide, x, y, w, h)
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = False
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap if i < len(items) - 1 else 0)
        p.line_spacing = 1.0
        text_run(p, item, size, False, color, font)
    return tf


def header(slide):
    tf = txbox(slide, 1.55, 1.30, 23.56, 0.55)
    run(tf.paragraphs[0], "DEPLOYMENT OVERVIEW", 22, True, ORANGE)
    tf = txbox(slide, 1.55, 1.85, 23.56, 1.20)
    run(tf.paragraphs[0], "ModelExpress · 镜像与接入配置", 52, True, DARK)
    rect(slide, 1.55, 3.16, 2.10, 0.06, ORANGE, None, False)
    tf = txbox(slide, 1.55, 3.52, 23.56, 0.50)
    run(tf.paragraphs[0], "镜像依赖、Prefill / Decode 配置与上线步骤一页总览", 20, False, SUB)
    tf = txbox(slide, 23.11, 14.22, 2.00, 0.50)
    run(tf.paragraphs[0], "01", 18, False, MUTED, PP_ALIGN.RIGHT)


def step_card(slide, x, y, w, h, num, title, desc):
    card = rect(slide, x, y, w, h, WHITE, BORDER, True)
    badge = rect(slide, x + 0.18, y + 0.23, 0.62, 0.62, ORANGE, None, True)
    badge.adjustments[0] = 0.5
    textbox(slide, x + 0.18, y + 0.23, 0.62, 0.62, num, 15, True, WHITE,
            align=PP_ALIGN.CENTER, ml=0, mr=0)
    textbox(slide, x + 0.92, y + 0.12, w - 1.05, 0.48, title, 16, True, DARK, ml=0, mr=0)
    textbox(slide, x + 0.92, y + 0.58, w - 1.05, 0.38, desc, 12, False, MUTED, ml=0, mr=0)
    return card


def image_row(slide, x, y, w, h, index, kind, version, purpose, image):
    row = rect(slide, x, y, w, h, WHITE if index % 2 else LIGHT, BORDER, True)
    badge = rect(slide, x + 0.22, y + 0.22, 0.56, 0.56, ORANGE, None, True)
    badge.adjustments[0] = 0.5
    textbox(slide, x + 0.22, y + 0.22, 0.56, 0.56, f"{index:02d}", 13, True, WHITE,
            align=PP_ALIGN.CENTER, ml=0, mr=0)
    textbox(slide, x + 0.92, y + 0.13, 2.45, 0.45, kind, 16, True, DARK, ml=0, mr=0)
    pill_w = 1.55 if version != "基础镜像" else 1.70
    pill = rect(slide, x + w - pill_w - 0.22, y + 0.16, pill_w, 0.52, PALE_ORANGE, ORANGE, True)
    pill.adjustments[0] = 0.28
    textbox(slide, x + w - pill_w - 0.22, y + 0.16, pill_w, 0.52, version, 12, True,
            ORANGE_DARK, align=PP_ALIGN.CENTER, ml=0.05, mr=0.05)
    textbox(slide, x + 0.92, y + 0.55, w - 1.25, 0.38, purpose, 12, False, MUTED, ml=0, mr=0)
    lines(slide, x + 0.92, y + 0.93, w - 1.25, h - 1.02, image.split("\n"), 11, BODY, MONO, 1)
    return row


def config_box(slide, x, y, w, h, title, file_path, body_lines, accent=False):
    fill = PALE_ORANGE if accent else LIGHT
    line = ORANGE if accent else BORDER
    card = rect(slide, x, y, w, h, fill, line, True)
    textbox(slide, x + 0.22, y + 0.10, w - 0.44, 0.42, title, 15, True,
            ORANGE_DARK if accent else DARK, ml=0, mr=0)
    textbox(slide, x + 0.22, y + 0.48, w - 0.44, 0.34, file_path, 10, False, MUTED, MONO, ml=0, mr=0)
    lines(slide, x + 0.22, y + 0.86, w - 0.44, h - 0.98, body_lines, 12, BODY, MONO, 3)
    return card


def main():
    prs = Presentation(SRC)
    slide = prs.slides.add_slide(prs.slide_masters[0].slide_layouts[1])
    header(slide)

    band(slide, 1.55, 4.30, "实施流程")
    left, total = 1.55, 23.56
    flow_y, flow_h, flow_gap = 4.88, 1.10, 0.65
    flow_w = (total - flow_gap * 4) / 5
    flow_xs = [left + i * (flow_w + flow_gap) for i in range(5)]
    for x, data in zip(flow_xs, STEPS):
        step_card(slide, x, flow_y, flow_w, flow_h, *data)
    for i in range(4):
        arrow(slide, flow_xs[i] + flow_w + 0.10, flow_y + flow_h / 2,
              flow_xs[i + 1] - 0.10, flow_y + flow_h / 2, ORANGE, 22225)

    left_w, main_gap = 9.15, 0.70
    right_x = left + left_w + main_gap
    right_w = total - left_w - main_gap
    band(slide, left, 6.40, "镜像清单 · 3 层依赖")
    band(slide, right_x, 6.40, "Prefill / Decode 接入配置")

    row_y, row_h, row_gap = 7.02, 1.58, 0.16
    for i, data in enumerate(IMAGES, 1):
        image_row(slide, left, row_y + (i - 1) * (row_h + row_gap), left_w, row_h, i, *data)

    outer = rect(slide, right_x, row_y, right_w, 5.06, WHITE, BORDER, True)
    config_box(
        slide, right_x + 0.25, row_y + 0.25, right_w - 0.50, 1.50,
        "Engine Args · Prefill + Decode",
        "configmap-engine-args.yaml",
        ["checkpoint_format: MX", "mx_config.server_url: modelexpress-server.foundation.svc.cluster.local:8001"],
        True,
    )

    inner_y = row_y + 1.98
    inner_gap = 0.22
    inner_w = (right_w - 0.50 - inner_gap * 2) / 3
    inner_xs = [right_x + 0.25 + i * (inner_w + inner_gap) for i in range(3)]
    config_box(
        slide, inner_xs[0], inner_y, inner_w, 2.83,
        "Server Endpoint",
        "deploy-1p1d.yaml · envs",
        ["MODEL_EXPRESS_URL", "MX_SERVER_ADDRESS", "= modelexpress-server", "  .foundation.svc:8001"],
    )
    config_box(
        slide, inner_xs[1], inner_y, inner_w, 2.83,
        "Model Identity",
        "deploy-1p1d.yaml · envs",
        ["MODEL_NAME=", "GLM-5.3-Quant-W-INT8-", "PerChannel-A-INT8-PerToken", "Source / Target 必须一致"],
    )
    config_box(
        slide, inner_xs[2], inner_y, inner_w, 2.83,
        "RDMA Runtime",
        "deploy-1p1d.yaml · envs",
        ["MX_RDMA_NIC_PIN=off", "MX_POOL_REG=0", "MX_VMM_ARENA=0", "UCX_RNDV_THRESH=0"],
    )

    strip(
        slide, left, 12.55, total, 0.95,
        "版本约束",
        "MX Server 使用 v0.5.1；Worker 内 MX Client 固定 v0.5.0，"
        "以匹配当前 Holmes / TensorRT-LLM 原生 MX Loader 接口",
    )

    sld_id_list = prs.slides._sldIdLst
    for sld_id in list(sld_id_list)[:-1]:
        prs.part.drop_rel(sld_id.rId)
        sld_id_list.remove(sld_id)
    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
