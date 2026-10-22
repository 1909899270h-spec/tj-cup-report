#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同济足协杯 · 战报 docx 生成器

用法:
    python3 report.py spec.json [-o 战报 xxx.docx]

spec.json 相关字段:
  match:  home / away / score:[2,3] / home_starters / away_starters
  report: title / lead / highlights:[{"text": "...", "video": "视频1"}] / closing
  output: timeline(时间轴 png 路径) / docx(输出路径)
"""
import json
import os
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "等线"


def _set_font(run, size=12, bold=False, color=None, italic=False):
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    if color:
        run.font.color.rgb = RGBColor(*color)


def _para(doc, align=None, after=6, line=1.6, indent=0, page_break=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(after)
    pf.space_before = Pt(0)
    pf.line_spacing = line
    if indent:
        pf.first_line_indent = Pt(indent)
    if page_break:
        pf.page_break_before = True
    if align is not None:
        p.alignment = align
    return p


def build(spec):
    m, r = spec["match"], spec.get("report", {})
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.8)
    sec.top_margin = sec.bottom_margin = Cm(2.54)

    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    home, away = m["home"], m["away"]
    sh, sa = m["score"]

    # 标题
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, after=16, line=1.4)
    _set_font(p.add_run(r["title"]), size=16, bold=True)

    # 比分
    p = _para(doc, after=10)
    _set_font(p.add_run("比分："), bold=True)
    _set_font(p.add_run(f"{home}{sh}:{sa}{away}"))

    # 赛事简讯
    p = _para(doc, after=4)
    _set_font(p.add_run("赛事简讯："), bold=True)
    p = _para(doc, after=10, indent=24)
    _set_font(p.add_run(r["lead"]))

    # 双方首发
    p = _para(doc, after=4)
    _set_font(p.add_run("双方首发："), bold=True)
    for name, starters in ((home, m["home_starters"]), (away, m["away_starters"])):
        p = _para(doc, after=2)
        _set_font(p.add_run(f"{name}："), bold=True)
        p = _para(doc, after=8 if name != away else 10, indent=24)
        _set_font(p.add_run(" ".join(starters)))

    # 比赛进程（时间轴独占一页）
    p = _para(doc, after=4, page_break=True)
    _set_font(p.add_run("比赛进程："), bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    tl = r.get("timeline") or spec.get("output", {}).get("timeline")
    if not tl:
        raise SystemExit("spec 里缺少时间轴路径：output.timeline 或 report.timeline")
    p.add_run().add_picture(tl, width=Cm(r.get("timeline_width_cm", 9.2)))

    # 精彩瞬间
    p = _para(doc, after=6)
    _set_font(p.add_run("精彩瞬间："), bold=True)
    for h in r.get("highlights", []):
        p = _para(doc, after=2, indent=24)
        _set_font(p.add_run(h["text"]), bold=True)
        p = _para(doc, after=10)
        _set_font(p.add_run(f"（{h['video']}）"))

    if r.get("closing"):
        p = _para(doc, after=4, indent=24)
        _set_font(p.add_run(r["closing"]))

    out = spec.get("output", {}).get("docx", "战报.docx")
    doc.save(out)
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        spec = json.load(f)
    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None
    if out:
        spec.setdefault("output", {})["docx"] = out
    print("战报已生成:", build(spec))


if __name__ == "__main__":
    main()
