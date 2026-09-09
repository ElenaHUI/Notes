# -*- coding: utf-8 -*-
"""基于 PTG/模版.pptx 生成实习工作总结 PPT。"""
import copy
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt
from lxml import etree

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(BASE, "PTG", "模版.pptx")
OUTPUT = os.path.join(BASE, "PTG", "PTG实习工作总结.pptx")

FONT = "Microsoft YaHei"
ORANGE = RGBColor(0xFF, 0x50, 0x0C)
DARK = RGBColor(0x3C, 0x41, 0x48)
GRAY = RGBColor(0x53, 0x58, 0x5F)
MUTED = RGBColor(0x8A, 0x90, 0x99)
CARD_BG = RGBColor(0xF5, 0xF6, 0xF8)
CARD_LN = RGBColor(0xE1, 0xE4, 0xE8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BULLET = "•  "

L = 1.55            # 内容左边界
R = 25.11           # 内容右边界
W = R - L           # 23.56
BODY_TOP = 3.6
BODY_BOT = 13.85

IMG_ROOT = BASE
IMG_INFRA = os.path.join(BASE, "asset", "红区AI Infra.png")
IMG_DGD = os.path.join(BASE, "PTG", "asset", "Pasted image 20260828153229.png")
IMG_WARM = os.path.join(BASE, "PTG", "asset", "Pasted image 20260903114401.png")
IMG_GRAFANA = os.path.join(
    BASE, "Dynamo", "Dynamo监控链路搭建", "asset", "Pasted image 20260811171322.png"
)


# --------------------------------------------------------------------------- 基础工具
def set_font(run, size, color, bold=False, font=FONT):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    f.name = font
    rPr = f._rPr
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", font)


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return box


def para(tf, first=False):
    return tf.paragraphs[0] if first else tf.add_paragraph()


def blank_para(tf, first=False, align=PP_ALIGN.LEFT, space_before=0, space_after=0,
               spacing=1.0):
    """只建段落不建 run，避免留下影响行高的空 run。"""
    p = para(tf, first)
    p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    p.line_spacing = spacing
    return p


def line(tf, text, size, color, bold=False, first=False, align=PP_ALIGN.LEFT,
         space_before=0, space_after=0, spacing=1.0):
    p = para(tf, first)
    p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    p.line_spacing = spacing
    run = p.add_run()
    run.text = text
    set_font(run, size, color, bold)
    return p


def rect(slide, x, y, w, h, fill, line_color=None, line_w=1.5, radius=None):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shp.adjustments[0] = radius
    shp.shadow.inherit = False
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line_color is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line_color
        shp.line.width = Pt(line_w)
    shp.text_frame.word_wrap = True
    return shp


# --------------------------------------------------------------------------- 版式构件
def page_head(slide, kicker, title, num=None):
    tb = textbox(slide, L, 1.30, W, 0.55)
    line(tb.text_frame, kicker, 22, ORANGE, bold=True, first=True)
    tb = textbox(slide, L, 1.85, W, 1.20)
    line(tb.text_frame, title, 52, DARK, bold=True, first=True)
    rect(slide, L, 3.16, 2.10, 0.06, ORANGE)
    if num is not None:
        tb = textbox(slide, R - 2.0, 14.22, 2.0, 0.5)
        line(tb.text_frame, "%02d" % num, 18, MUTED, first=True, align=PP_ALIGN.RIGHT)


def card(slide, x, y, w, h, header=None, items=(), pad=0.42, header_size=30,
         body_size=24, fill=CARD_BG, anchor=MSO_ANCHOR.MIDDLE):
    shp = rect(slide, x, y, w, h, fill, CARD_LN, 1.25, radius=0.04)
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Inches(pad)
    tf.margin_top = Inches(pad * 0.8)
    tf.margin_bottom = Inches(pad * 0.6)
    tf.vertical_anchor = anchor
    first = True
    if header:
        line(tf, header, header_size, ORANGE, bold=True, first=True, space_after=10)
        first = False
    for it in items:
        kind, text = it[0], it[1]
        if kind == "sub":
            line(tf, text, body_size + 2, DARK, bold=True, first=first,
                 space_before=0 if first else 14, space_after=6, spacing=1.15)
        elif kind == "b":
            p = para(tf, first)
            p.space_before = Pt(0)
            p.space_after = Pt(9)
            p.line_spacing = 1.25
            r0 = p.add_run()
            r0.text = BULLET
            set_font(r0, body_size, ORANGE)
            r1 = p.add_run()
            r1.text = text
            set_font(r1, body_size, GRAY)
        elif kind == "kv":
            p = para(tf, first)
            p.space_before = Pt(0)
            p.space_after = Pt(9)
            p.line_spacing = 1.25
            r0 = p.add_run()
            r0.text = it[1] + "  "
            set_font(r0, body_size, DARK, bold=True)
            r1 = p.add_run()
            r1.text = it[2]
            set_font(r1, body_size, GRAY)
        elif kind == "t":
            line(tf, text, body_size, GRAY, first=first, space_after=9, spacing=1.25)
        elif kind == "note":
            line(tf, text, body_size - 4, MUTED, first=first, space_before=10,
                 space_after=0, spacing=1.2)
        first = False
    return shp


def stat_card(slide, x, y, w, h, value, unit, label, note=None):
    shp = rect(slide, x, y, w, h, WHITE, CARD_LN, 1.25, radius=0.05)
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Inches(0.32)
    tf.margin_top = Inches(0.40)
    tf.margin_bottom = Inches(0.30)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = blank_para(tf, first=True)
    r = p.add_run()
    r.text = value
    set_font(r, 66, ORANGE, bold=True)
    if unit:
        r2 = p.add_run()
        r2.text = " " + unit
        set_font(r2, 26, ORANGE, bold=True)
    line(tf, label, 26, DARK, bold=True, space_before=8, space_after=4, spacing=1.15)
    if note:
        line(tf, note, 20, MUTED, spacing=1.2)
    return shp


def flow_box(slide, x, y, w, h, text):
    shp = rect(slide, x, y, w, h, WHITE, ORANGE, 1.5, radius=0.08)
    tf = shp.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Inches(0.18)
    lines = text.split("\n")
    for i, t in enumerate(lines):
        line(tf, t, 24 if i == 0 else 20, DARK if i == 0 else MUTED,
             bold=(i == 0), first=(i == 0), align=PP_ALIGN.CENTER, spacing=1.15)
    return shp


def arrow(slide, x, y, w, h):
    tb = textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.MIDDLE)
    line(tb.text_frame, "→", 30, ORANGE, first=True, align=PP_ALIGN.CENTER)


def picture(slide, path, x, y, w=None, h=None):
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    return slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def divider(prs, layout, num, title, en, points):
    slide = prs.slides.add_slide(layout)
    tb = textbox(slide, 1.60, 5.05, 5.0, 2.2)
    line(tb.text_frame, num, 130, ORANGE, bold=True, first=True)
    tb = textbox(slide, 1.62, 7.35, 6.4, 1.4)
    line(tb.text_frame, title, 74, DARK, bold=True, first=True)
    tb = textbox(slide, 1.66, 8.95, 6.4, 0.7)
    line(tb.text_frame, en, 28, MUTED, first=True)
    rect(slide, 1.66, 6.85, 1.9, 0.06, ORANGE)
    tb = textbox(slide, 9.80, 5.20, 15.0, 5.0)
    tf = tb.text_frame
    for i, t in enumerate(points):
        p = blank_para(tf, first=(i == 0), space_after=16, spacing=1.25)
        r0 = p.add_run()
        r0.text = BULLET
        set_font(r0, 30, ORANGE)
        r1 = p.add_run()
        r1.text = t
        set_font(r1, 30, GRAY)
    return slide


# --------------------------------------------------------------------------- 模版文本替换
def set_para_text(p, text):
    runs = p.runs
    if not runs:
        r = p.add_run()
        r.text = text
        set_font(r, 24, GRAY)
        return
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def set_shape_lines(shape, lines):
    tf = shape.text_frame
    paras = tf.paragraphs
    while len(paras) < len(lines):
        tf._txBody.append(copy.deepcopy(paras[-1]._p))
        paras = tf.paragraphs
    for i, text in enumerate(lines):
        set_para_text(paras[i], text)
    for p in paras[len(lines):]:
        p._p.getparent().remove(p._p)


def find_shape(slide, name):
    for shp in slide.shapes:
        if shp.name == name:
            return shp
    raise KeyError(name)


def delete_slide(prs, index):
    slides = prs.slides
    sldId = slides._sldIdLst[index]
    rId = sldId.get(qn("r:id"))
    prs.part.drop_rel(rId)
    slides._sldIdLst.remove(sldId)


def move_slide_to_end(prs, index):
    lst = prs.slides._sldIdLst
    el = lst[index]
    lst.remove(el)
    lst.append(el)


# --------------------------------------------------------------------------- 正文
def main():
    prs = Presentation(TEMPLATE)
    cover, toc, blank, thanks = prs.slides[0], prs.slides[1], prs.slides[2], prs.slides[3]
    layouts = {lay.name: lay for lay in prs.slide_masters[0].slide_layouts}
    LAY_PAGE = layouts["封面"]      # 浅色底纹内页
    LAY_SEC = layouts["侧边"]        # 左侧灰底章节页

    # ---- 封面
    set_shape_lines(find_shape(cover, "这里是标题平头哥PPT模版"), ["红区大模型推理平台建设与优化"])
    set_shape_lines(find_shape(cover, "New Future on Cloud"),
                    ["PD 分离 · 智能调度 · 监控体系 · Agent 工具链"])
    set_shape_lines(find_shape(cover, "演讲人姓名"), ["闫一慧"])
    set_shape_lines(find_shape(cover, "职位名称平头哥市场高级专家"),
                    ["LLM 推理平台实习生 · 阿里巴巴平头哥半导体", "2026 / 09"])

    # ---- 目录（02 项模版原文为「半年 / 总结」两行，这里收成一行与 01 / 03 齐平）
    toc_items = [s for s in toc.shapes if s.name == "IT基础设施云化"]
    set_shape_lines(toc_items[1], ["工作总结"])

    # 说明：正文页追加在末尾，全部生成完成后再删除模版空白页、把「谢谢」页移到最后，
    # 这样可避免新建 slide 与模版既有 slide 抢占同一个 partname。
    n = 0

    # =========================== 01 个人介绍
    divider(prs, LAY_SEC, "01", "个人介绍", "PROFILE", [
        "教育背景与实习经历",
        "在平头哥的岗位职责",
        "技术栈与工具链",
    ])

    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "PROFILE", "个人介绍", n)
    half = (W - 0.60) / 2
    x2 = L + half + 0.60
    card(s, L, BODY_TOP, half, 3.95, "教育背景", [
        ("kv", "华东师范大学", "软件工程 硕士在读 · 2024.09 — 2027.06"),
        ("kv", "西安电子科技大学", "软件工程 学士 · 专业排名 21/332"),
        ("note", "学业奖学金 2024 / 2025；数学建模省一等奖"),
    ])
    card(s, x2, BODY_TOP, half, 3.95, "岗位职责", [
        ("t", "负责红区大模型推理平台基于 GitOps 的 PD 分离部署、调度架构与监控体系建设"),
        ("t", "支撑 Kimi-K2.6、Qwen3.5-397B 等 MoE 模型在自研 PPU 芯片上的在线推理服务"),
    ])
    card(s, L, 7.90, half, 5.95, "实习经历", [
        ("sub", "阿里巴巴平头哥半导体 · LLM 推理平台实习生"),
        ("t", "2026.06 — 至今，上海。推理服务部署、调度与可观测性建设，兼顾 Agent 工具链落地"),
        ("sub", "OPPO · 算法实习生"),
        ("t", "2025.10 — 2026.02。Qwen / Andes-ViT 在自研推理芯片上的量化压缩与精度校准"),
    ])
    card(s, x2, 7.90, half, 5.95, "技术栈", [
        ("kv", "推理引擎", "SGLang · vLLM · Dynamo（DGD）"),
        ("kv", "分布式传输", "Mooncake · RDMA / IB · 机内 ICN"),
        ("kv", "云原生", "Kubernetes · ArgoCD GitOps · Kustomize"),
        ("kv", "可观测性", "Prometheus · Grafana · DCGM Exporter"),
        ("kv", "开发", "Python · TypeScript · Shell · MySQL"),
    ])

    # =========================== 02 工作总结
    divider(prs, LAY_SEC, "02", "工作总结", "WORK SUMMARY", [
        "工作全景与成果速览",
        "PD 分离部署与参数调优",
        "Dynamo 智能调度架构迁移",
        "监控体系建设与疑难问题定位",
        "Warmup 方案、性能报告与 Agent 工具链",
    ])

    # ---- 工作全景
    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "BIG PICTURE", "工作全景：红区 AI Infra 分层视图", n)
    picture(s, IMG_INFRA, L, BODY_TOP, h=10.15)
    px = L + 10.15 * (3406 / 2886.0) + 0.55
    card(s, px, BODY_TOP, R - px, 10.15, "我的负责范围", [
        ("kv", "编排层", "自研 Deployment 版 PD 分离、Dynamo DGD 部署与调度演进"),
        ("kv", "度量层", "TTFT / ITL / 吞吐 / KV 命中率的 Prometheus 采集与 Grafana 看板"),
        ("kv", "运行时", "SGLang / vLLM 启动参数调优、Warmup 机制统一"),
        ("kv", "交付层", "Gitea + ArgoCD GitOps 声明式发布，多环境灰度"),
        ("kv", "Agent 侧", "Opencode 上报插件全链路、DeepSeek Harness 离线包"),
        ("note", "图示为团队整体 AI Infra 分层，上述为本人参与的部分"),
    ])

    # ---- 成果速览
    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "HIGHLIGHTS", "成果速览", n)
    sw = (W - 3 * 0.45) / 4
    stats = [
        ("4", "个看板", "Grafana 监控看板", "共 76 个面板，覆盖数据面与控制面"),
        ("7", "个模型", "性能基线覆盖", "跨 vLLM / SGLang 两套引擎"),
        ("4", "个 MoE", "PD 分离部署验证", "Kimi-K2.6 / Qwen3.5-397B 等"),
        ("3", "套环境", "Agent 上报链路上线", "dev / prod / B 红区全部验证"),
    ]
    for i, (v, u, lab, note) in enumerate(stats):
        stat_card(s, L + i * (sw + 0.45), BODY_TOP, sw, 3.45, v, u, lab, note)
    cw = (W - 2 * 0.5) / 3
    card(s, L, 7.55, cw, 6.30, "平台交付", [
        ("b", "DeepSeek-V4-Flash、Kimi-K2.6 等模型 PD 分离部署跑通并调优"),
        ("b", "MiniMax-M2.7 端到端上线：t-one 建应用 → GitOps 配置 → 域名白名单 → 四层转发"),
        ("b", "Dynamo v1.3.0 DGD 部署形态验证，为替换网关静态路由铺路"),
    ])
    card(s, L + cw + 0.5, 7.55, cw, 6.30, "性能与稳定性", [
        ("b", "去掉三处 disable 开关，TTFT / TPOT 明显改善"),
        ("b", "定位 CP 与 DP attention 互斥、fa3 算子不支持等引擎级约束"),
        ("b", "Warmup 真实请求录制回放方案，解决冷启动首请求慢的问题"),
        ("b", "周 / 日双周期性能报告 Skill，指标趋势自动产出"),
    ])
    card(s, L + 2 * (cw + 0.5), 7.55, cw, 6.30, "工具链效率", [
        ("b", "Opencode /report 插件 + 服务端 + 钉钉 + web-mgmt 全链路打通"),
        ("b", "DeepSeek Harness Web UI 离线包，一条命令在红区内网即开即用"),
        ("b", "4 份重复 ConfigMap 收敛为 1 份共享脚本，影响 15+ 部署清单"),
    ])

    # ---- PD 分离
    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "PD DISAGGREGATION", "PD 分离部署与参数调优", n)
    lw = 13.40
    rx = L + lw + 0.60
    rw = R - rx
    card(s, L, BODY_TOP, lw, BODY_BOT - BODY_TOP, None, [
        ("sub", "传输链路打通"),
        ("b", "SGLang PD 分离 + Mooncake 跨节点 KV Cache 传输，绑定 mlx5_bond_* 多网卡"),
        ("b", "机内场景启用 ICN：MC_FORCE_MNNVL / MC_USE_NVLINK_IPC，以 TRACE 日志验证链路真实生效"),
        ("b", "K8s 侧 hostNetwork / hostPID / hostIPC + ClusterFirstWithHostNet 是 RDMA 初始化的前提"),
        ("sub", "参数调优"),
        ("b", "去掉 disable-custom-all-reduce / radix-cache / shared-experts-fusion 三个开关，TTFT 与 TPOT 同步改善"),
        ("b", "P 端保留 NSA Context Parallel（attn-cp-size 8），D 端使用 DP attention + DP LM head"),
        ("b", "router 以 mini-lb 串联 P / D，按 round-robin 做 prefill 均衡"),
        ("sub", "沉淀"),
        ("b", "形成可复用的 P / D 最小可运行配置模板与排障清单"),
    ], body_size=25)
    card(s, rx, BODY_TOP, rw, 4.55, "覆盖模型", [
        ("t", "Kimi-K2.6 · DeepSeek-V4-Flash"),
        ("t", "Qwen3.5-397B-A17B-INT8（8 卡机内 ICN）"),
        ("t", "Qwen3-235B-A22B-INT8（16 卡跨节点）"),
        ("note", "engine：SGLang 0.5.16 / Dynamo 1.3.1"),
    ])
    card(s, rx, 8.75, rw, BODY_BOT - 8.75, "典型问题 → 解法", [
        ("b", "fa3 报 q_v only supported for Hopper → 拆成 flashmla decode + fa3 prefill"),
        ("b", "round-robin-split CP 下开 dp-size 报错 → P 端 dp-size 固定为 1"),
        ("b", "未开 host 网络时 Mooncake 退化、TTFT 极高 → 补齐 extraPodSpec"),
    ])

    # ---- Dynamo
    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "SCHEDULING", "Dynamo 智能调度架构迁移", n)
    lw = 12.00
    rx = L + lw + 0.60
    rw = R - rx
    card(s, L, BODY_TOP, lw, 6.15, "部署形态：DynamoGraphDeployment", [
        ("kv", "CRD", "nvidia.com/v1alpha1 · backendFramework: sglang"),
        ("kv", "拓扑", "Prefill / Decode 两个 Worker，各 1 副本 8 卡 PPU"),
        ("kv", "端口", "P 8100 · D 8101，disaggregation-mode 区分角色"),
        ("kv", "服务发现", "etcd；事件面 nats"),
        ("kv", "资源", "rdma/hca: 4，节点亲和 PPU + board.type=810e"),
        ("kv", "传输", "Mooncake，GPU 拓扑由注解注入"),
        ("note", "以 GitOps 声明式发布，ArgoCD 按环境分批 sync"),
    ], body_size=25)
    card(s, L, 10.30, lw, BODY_BOT - 10.30, "与自研 Deployment 版的差异", [
        ("b", "自研版：P / D 各一份 Deployment，靠 mini-lb 手工串联，副本与端口硬编码"),
        ("b", "DGD：一份声明由 Operator 展开出 Frontend / P / D 与配套 Service"),
        ("b", "控制面具备 Planner，为后续根据指标做扩缩容决策留出位置"),
    ], body_size=24)
    picture(s, IMG_DGD, rx, BODY_TOP, w=rw)
    ih = rw * (1632 / 4666.0)
    tb = textbox(s, rx, BODY_TOP + ih + 0.12, rw, 0.5)
    line(tb.text_frame, "DGD 资源树：一次声明展开为完整的 P / D 推理图", 20, MUTED, first=True)
    cy = BODY_TOP + ih + 0.85
    card(s, rx, cy, rw, BODY_BOT - cy, "调度演进", [
        ("b", "现状：Kong 网关静态 Hash 路由，无法感知 Worker 实际负载"),
        ("b", "方向：基于 KV Cache 占用率、队列长度的 KV-Aware Routing 动态分发"),
        ("b", "配套：Pod 级弹性 PD 部署，P / D 副本可独立伸缩"),
    ])

    # ---- 监控体系
    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "OBSERVABILITY", "监控体系建设：Prometheus + Grafana", n)
    dw = (W - 3 * 0.42) / 4
    boards = [
        ("Dynamo Dashboard", "28 面板 · 按 model 切分，看延迟 / 吞吐 / 缓存，零外部依赖"),
        ("Disaggregated Analysis", "21 面板 · 按 namespace 看 P/D 与 GPU、NVLink 利用率"),
        ("Planner Dashboard", "13 面板 · 控制面弹性决策，扩缩容预测与 SLA 达成"),
        ("Dynamo Operator", "14 面板 · CRD 调谐、准入校验与资源清单健康度"),
    ]
    for i, (t, d) in enumerate(boards):
        card(s, L + i * (dw + 0.42), BODY_TOP, dw, 3.55, None,
             [("sub", t), ("t", d)], pad=0.34, body_size=22)
    iw = 13.40
    picture(s, IMG_GRAFANA, L, 7.60, w=iw)
    ih = iw * (2236 / 4998.0)
    tb = textbox(s, L, 7.60 + ih + 0.10, iw, 0.5)
    line(tb.text_frame, "Frontend 行：RPS / E2E / TTFT / ITL / ISL / OSL / Cached Tokens", 20, MUTED, first=True)
    rx = L + iw + 0.60
    card(s, rx, 7.60, R - rx, BODY_BOT - 7.60, "指标与判读方法", [
        ("b", "接入 5 类指标族：frontend / component / router / planner / operator"),
        ("b", "硬件视角依赖 DCGM、node-exporter、kube-state-metrics"),
        ("b", "交叉校验：E2E ≈ TTFT + ITL × OSL，异常即怀疑采集口径"),
        ("b", "经验阈值：NVLink 带宽 < 1 GB/s 判定传输退化为 host 内存拷贝"),
    ])

    # ---- 疑难问题
    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "TROUBLESHOOTING", "疑难问题定位与根因修复", n)
    half = (W - 0.60) / 2
    x2 = L + half + 0.60
    ch = (BODY_BOT - BODY_TOP - 0.55) / 2
    y2 = BODY_TOP + ch + 0.55
    card(s, L, BODY_TOP, half, ch, "看板图例重复 · 采集层去重", [
        ("kv", "现象", "同名曲线出现三条且相位错开，sum() 结果放大 2~3 倍"),
        ("kv", "根因", "三个 ServiceMonitor 的 selector 过宽，同时命中 frontend Pod，以 5s/5s/15s 重复抓取"),
        ("kv", "处置", "只保留 Operator 原生 endpoint=http 的 ServiceMonitor，删除模型模板与平台侧两份"),
        ("note", "结论：采集层重复不应用面板层 max by 掩盖，否则冗余存储与相位错位仍在"),
    ], body_size=23)
    card(s, x2, BODY_TOP, half, ch, "Component Throughput 图例错乱", [
        ("kv", "现象", "图例硬编码，多 Worker 无法区分；曲线毛刺明显"),
        ("kv", "处置", "改为 {{worker_id}} 模板化，并把 rate 窗口修正为 [1m] 避免欠采样"),
    ], body_size=23)
    card(s, L, y2, half, ch, "Namespace 变量污染", [
        ("kv", "现象", "下拉出现 canary、v142-default 等历史 namespace，误选即无数据"),
        ("kv", "处置", "变量改用 label_values(dynamo_frontend_requests_total, dynamo_namespace) 动态收敛"),
    ], body_size=23)
    card(s, x2, y2, half, ch, "PD 链路不通 / TTFT 异常高", [
        ("kv", "现象", "Mooncake 无法初始化 RDMA 设备，或退化到低效路径"),
        ("kv", "处置", "补齐 host 网络三件套与 DNS 策略；以 MC_LOG_LEVEL=TRACE 复核内存注册日志"),
    ], body_size=23)

    # ---- Warmup
    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "COLD START", "Warmup：真实请求录制回放方案", n)
    lw = 13.40
    rx = L + lw + 0.60
    rw = R - rx
    card(s, L, BODY_TOP, lw, BODY_BOT - BODY_TOP, None, [
        ("sub", "问题"),
        ("b", "原 warmup 只发一条 1 万字静态纯文本，与真实的多轮对话 + system prompt + tool_calls + 长上下文差距大"),
        ("b", "四份 ConfigMap 逻辑 95% 重复，被 15+ 个 deploy.yaml 引用，改一处要改一片"),
        ("sub", "方案"),
        ("b", "litellm-proxy 新增 /capture/export-warmup：按模型筛选真实请求，去重、限长后导出 JSONL 到共享存储"),
        ("b", "统一 llm-warmup-scripts 共享 ConfigMap，支持 JSONL / Legacy 纯文本 / Skip 三种模式，env 全部带默认值，100% 向后兼容"),
        ("sub", "安全设计与灰度"),
        ("b", "warmup 失败只打 WARNING 并始终创建就绪标记，绝不阻塞 Pod Ready"),
        ("b", "export 限制 prompt 32K、脚本层 max_tokens cap 2048，串行发送避免启动期 OOM"),
        ("b", "pdev 单模型验证 → pprod → prod 分批迁移，ArgoCD 按 App 粒度控制节奏"),
    ], body_size=24)
    ch1 = 4.75
    c = card(s, rx, BODY_TOP, rw, ch1, "痛点实证", [])
    picture(s, IMG_WARM, rx + 0.42, BODY_TOP + 1.25, w=rw - 0.84)
    iw2 = rw - 0.84
    tb = textbox(s, rx + 0.42, BODY_TOP + 1.30 + iw2 * (410 / 2548.0), iw2, 1.6)
    line(tb.text_frame, "未预热实例的首次请求：一句「你好」端到端 3 分 56 秒",
         22, GRAY, first=True, spacing=1.25)
    cy = BODY_TOP + ch1 + 0.55
    card(s, rx, cy, rw, BODY_BOT - cy, "预期收益", [
        ("b", "首请求 TTFT 显著下降，算子 / kernel 缓存在 Ready 前完成填充"),
        ("b", "readinessProbe 与真实可服务状态对齐，避免流量打到未热实例"),
        ("b", "脚本单点维护，新模型接入只需一个环境变量"),
    ])

    # ---- 性能报告 Skill
    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "PERFORMANCE BASELINE", "性能分析报告 Skill", n)
    cw = (W - 2 * 0.5) / 3
    card(s, L, BODY_TOP, cw, 4.60, "采集范围", [
        ("b", "7 个在线模型，跨 vLLM 与 SGLang 两套引擎"),
        ("b", "直连 Prometheus range query，采样间隔 5 分钟"),
        ("b", "weekly（自然周对比上上周）与 daily（昨天对比前天）双模式"),
    ])
    card(s, L + cw + 0.5, BODY_TOP, cw, 4.60, "指标口径", [
        ("b", "TTFT / TPOT：直方图 sum 与 count 的比值换算为毫秒"),
        ("b", "Throughput：成功请求速率"),
        ("b", "KV Cache 利用率与命中率：分引擎适配不同指标名"),
    ])
    card(s, L + 2 * (cw + 0.5), BODY_TOP, cw, 4.60, "统计与呈现", [
        ("b", "Avg / Max / Min / Median / P95 / StdDev 六项统计"),
        ("b", "延迟类指标标注改善或恶化趋势与变化率"),
        ("b", "同时产出 Markdown 与 HTML 两份报告"),
    ])
    card(s, L, 8.80, (W - 0.6) / 2, BODY_BOT - 8.80, "关键计算方法", [
        ("b", "KV 指标按 Pod 独立取时间序列，先过滤值为 0 的时间点，再在相同时间点对全部 Pod 取平均"),
        ("b", "SGLang 按 (pod, engine_type) 维度独立计算后再聚合，避免 P / D 混算"),
        ("note", "目的：避免空闲副本把有效负载时段的均值拉平"),
    ])
    card(s, L + (W - 0.6) / 2 + 0.6, 8.80, (W - 0.6) / 2, BODY_BOT - 8.80, "价值与规划", [
        ("b", "把「看图判断」沉淀为可复现的量化口径，周期性输出趋势"),
        ("b", "报告按日期归档，可回溯任意周期的性能变化"),
        ("b", "后续与大模型性能分析平台结合，定时产出平台级性能基线"),
    ])

    # ---- Agent 工具链
    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "AGENT TOOLCHAIN", "Agent 工具链二次开发", n)
    fb = (W - 4 * 0.62) / 5
    steps = [
        "Opencode /report\n端侧采集与脱敏",
        "app-notifier\n落盘 + MySQL 持久化",
        "钉钉通知\n实时推送到群",
        "web-mgmt\n列表页 / 详情页",
        "状态闭环\nopen → resolved",
    ]
    for i, t in enumerate(steps):
        x = L + i * (fb + 0.62)
        flow_box(s, x, BODY_TOP + 0.15, fb, 1.95, t)
        if i < 4:
            arrow(s, x + fb, BODY_TOP + 0.15, 0.62, 1.95)
    y = BODY_TOP + 2.75
    half = (W - 0.60) / 2
    card(s, L, y, half, BODY_BOT - y, "Opencode 问题上报链路", [
        ("b", "插件侧：一条 curl 安装，/report 交互式收集日志与配置并脱敏"),
        ("b", "服务端：新建 issue_report 表与 3 个 API（分页列表 / 详情 / 状态更新），文件与数据库双写"),
        ("b", "前端：TanStack Query + 列表筛选分页，详情页用等宽日志与 Monaco 展示配置"),
        ("b", "修复 4 个上线阻塞问题：缺 report 接口、上报 403、安装脚本报错、时区错误"),
        ("b", "dev → prod → B 红区三套环境全部验证通过"),
    ])
    card(s, L + half + 0.60, y, half, BODY_BOT - y, "DeepSeek Harness Web UI 离线包", [
        ("b", "Node 运行时 + npm 应用闭包打包为自解压单文件，红区无外网机器一条命令即用"),
        ("b", "首启播种 settings.yaml，注册内部 6 个模型并指定默认模型；已存在时不覆写用户选择"),
        ("b", "注入 --port 0 由系统分配端口，规避多人同机冲突；远程访问走 ssh 端口转发"),
        ("b", "净环境（env -i，PATH 无 node）验证解压、播种、随机端口三步"),
        ("note", "已排除 pnpm deploy --prod、npx、SEA 单文件三种方案，均有硬阻塞"),
    ])

    # =========================== 03 未来规划
    divider(prs, LAY_SEC, "03", "未来规划", "WHAT'S NEXT", [
        "Warmup 全量落地与真实请求录制",
        "Dynamo 智能调度与多级缓存",
        "性能基线平台化",
    ])

    n += 1
    s = prs.slides.add_slide(LAY_PAGE)
    page_head(s, "WHAT'S NEXT", "未来规划", n)
    cw = (W - 2 * 0.5) / 3
    card(s, L, BODY_TOP, cw, 6.45, "近期 · 落地收口", [
        ("b", "录制 Opencode / QwenCode 真实请求，产出各模型 warmup 数据"),
        ("b", "统一 warmup 脚本从 pdev 推到 pprod、prod，完成 15+ 部署清单迁移"),
        ("b", "补齐 warmup 前后 TTFT 对比数据，量化收益"),
        ("b", "收敛模型模板中过宽的 ServiceMonitor selector，根治图例重复复发"),
    ])
    card(s, L + cw + 0.5, BODY_TOP, cw, 6.45, "中期 · 调度与缓存", [
        ("b", "Dynamo Platform 生产化部署，替换网关静态 Hash 路由"),
        ("b", "KV-Aware Routing 上线，按 KV 占用与队列长度动态分发"),
        ("b", "Prefix Cache 策略治理与 KVBM 多级缓存验证"),
        ("b", "卡量到位后扩大 PD 分离覆盖，推进 Pod 级弹性伸缩"),
    ])
    card(s, L + 2 * (cw + 0.5), BODY_TOP, cw, 6.45, "长期 · 平台化", [
        ("b", "性能基线平台化：报告定时产出，接入告警与 SLA 视图"),
        ("b", "PPU 拓扑调度插件与业务池弹性调度，提升整体卡利用率"),
        ("b", "把排障经验沉淀为可复用的部署模板与检查清单"),
    ])
    card(s, L, 10.65, W, BODY_BOT - 10.65, "个人成长", [
        ("b", "系统学习 CS336 与推理系统源码（SGLang 调度器、KV 管理），补齐从算子到调度的完整链路认知"),
        ("b", "持续沉淀笔记与方案文档，把「跑通」变成「可复现、可移交」"),
    ])

    # ---- 删除模版空白页（index 2），再把「谢谢」页（此时为 index 2）移到最后
    delete_slide(prs, 2)
    move_slide_to_end(prs, 2)
    prs.save(OUTPUT)
    print("saved:", OUTPUT, "slides:", len(prs.slides._sldIdLst))


if __name__ == "__main__":
    main()
