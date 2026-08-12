#!/usr/bin/env python3
"""把 Markdown 里的行内 LaTeX 公式抽出来，配合钉钉文档「插入公式」逐个粘贴。

用法:
    python3 .tools/dingtalk_formula.py <md 文件>            # 生成钉钉版(带标记) + 公式清单
    python3 .tools/dingtalk_formula.py <md 文件> --feed      # 依次把公式喂给剪贴板
    python3 .tools/dingtalk_formula.py <md 文件> --feed -s 20  # 从第 20 个开始(断点续传)

生成物都放在 .tools/out/ 下，不污染笔记库。
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# 行内公式：$...$，不跨行，排除 \$ 转义
FORMULA_RE = re.compile(r"(?<!\\)\$([^$\n]+?)(?<!\\)\$")
MARKER = "〖{}〗"


def context_of(line: str, headings: list[str]) -> str:
    """给公式一个位置提示：表格行取第一列，否则取最近的标题。"""
    if line.lstrip().startswith("|"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0]:
            return cells[0]
    return headings[-1] if headings else "正文"


def extract(md_path: Path):
    formulas = []  # [(序号, latex, 位置提示)]
    out_lines = []
    headings = []

    for line in md_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            headings.append(line.lstrip("# ").strip())

        ctx = context_of(line, headings)

        def sub(m):
            formulas.append((len(formulas) + 1, m.group(1).strip(), ctx))
            return MARKER.format(len(formulas))

        out_lines.append(FORMULA_RE.sub(sub, line))

    return formulas, "\n".join(out_lines) + "\n"


def write_outputs(md_path: Path, formulas, marked_text: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    marked = out_dir / f"{md_path.stem}-钉钉版.md"
    marked.write_text(marked_text, encoding="utf-8")

    # 清单：按公式内容分组，完全相同的公式只需插一次，其余位置复制粘贴即可
    groups: dict[str, list[int]] = {}
    for idx, latex, _ in formulas:
        groups.setdefault(latex, []).append(idx)

    lines = [f"# {md_path.stem} · 公式清单（共 {len(formulas)} 处，去重后 {len(groups)} 个）", ""]
    lines += ["| 标记 | 位置 | LaTeX | 相同公式的其他标记 |", "| --- | --- | --- | --- |"]
    for idx, latex, ctx in formulas:
        same = [str(i) for i in groups[latex] if i != idx]
        code = latex.replace("|", "\\|")
        lines.append(f"| 〖{idx}〗 | {ctx} | `{code}` | {'、'.join(same) or '-'} |")

    listing = out_dir / f"{md_path.stem}-公式清单.md"
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return marked, listing, groups


def pbcopy(text: str):
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def feed(formulas, start: int):
    total = len(formulas)
    if not 1 <= start <= total:
        sys.exit(f"起始序号需在 1~{total} 之间")

    print(f"共 {total} 个公式，从第 {start} 个开始。")
    print("每次已复制到剪贴板：在钉钉里选中标记 → 输入 /公式 → ⌘V → 回车")
    print("然后回到这里敲回车继续，输入 q 退出。\n")

    for idx, latex, ctx in formulas[start - 1:]:
        pbcopy(latex)
        print(f"[{idx}/{total}] 〖{idx}〗 {ctx}\n    {latex}")
        if input("    回车继续 > ").strip().lower() == "q":
            print(f"\n已停在第 {idx} 个，下次用 --feed -s {idx} 续上。")
            return
    print("\n全部完成。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md", type=Path)
    ap.add_argument("--feed", action="store_true", help="逐个把公式送进剪贴板")
    ap.add_argument("-s", "--start", type=int, default=1, help="从第几个公式开始")
    args = ap.parse_args()

    if not args.md.exists():
        sys.exit(f"找不到文件：{args.md}")

    formulas, marked_text = extract(args.md)
    if not formulas:
        sys.exit("没有找到 $...$ 行内公式")

    out_dir = Path(__file__).parent / "out"
    marked, listing, groups = write_outputs(args.md, formulas, marked_text, out_dir)

    print(f"公式 {len(formulas)} 处，去重后 {len(groups)} 个")
    print(f"钉钉版（公式已替换为 〖n〗）：{marked}")
    print(f"公式清单：{listing}")

    if args.feed:
        print()
        feed(formulas, args.start)


if __name__ == "__main__":
    main()
