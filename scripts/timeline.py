#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同济足协杯 · 比赛时间轴生成器

用法:
    python3 timeline.py spec.json [-o 输出.png]

spec.json 里 events 支持的类型:
    {"minute": 23, "type": "sub",   "side": "home", "on": ["10-薛振宇"], "off": ["2-周子泙"]}
    {"minute": 28, "type": "goal",  "side": "home", "player": "10-薛振宇", "score": [1, 0]}
    {"minute": 45, "type": "ht",    "label": "HT"}
    {"minute": 48, "type": "card",  "side": "away", "player": "61-雷炎达", "kind": "黄牌"}
side 取 home / away；同一分钟双方都换人时，写在同一分钟的两条 sub 会自动合成一行。
goal 的 score 可省略，会按出现顺序自动累加。
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets", "timeline")
W, CX = 1080, 540
X_LEFT, X_RIGHT = 398, 690          # 左队文字右端 / 右队文字左端
BG, WHITE, BLACK, GREEN = (250, 250, 250), (255, 255, 255), (0, 0, 0), (21, 172, 57)
AA_GREEN = (57, 150, 79)
SIZE_TEXT, SIZE_NUM = 35, 31
PAD_TOP_BOTTOM = 26


def _pick_font():
    cands = [
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 2),
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 2),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf", 0),
        ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 0),
        ("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", 0),
        ("C:/Windows/Fonts/Deng.ttf", 0),
        ("/System/Library/Fonts/PingFang.ttc", 0),
    ]
    for path, idx in cands:
        if not os.path.exists(path):
            continue
        try:
            f = ImageFont.truetype(path, 35, index=idx)
            if f.getlength("薛") > 20:      # 必须能排出中文
                return path, idx
        except Exception:
            continue
    raise SystemExit("找不到可用的中文字体，请安装 fonts-noto-cjk")


FONT_PATH, FONT_INDEX = _pick_font()


def font(size):
    return ImageFont.truetype(FONT_PATH, size, index=FONT_INDEX)


_f_txt = font(SIZE_TEXT)


def fit(text, max_w, size=SIZE_TEXT):
    """文字过长时自动缩字号，保证不越过框边。"""
    while size > 18 and _f_txt.font_variant(size=size).getlength(text) > max_w:
        size -= 1
    return font(size)


def load(name):
    im = Image.open(os.path.join(ASSETS, name)).convert("RGB")
    if name in TRIM_BOTTOM:
        im = im.crop((0, 0, im.width, im.height - TRIM_BOTTOM[name]))
    return im


TRIM_BOTTOM = {"左队/左队换一人.png": 1}   # 素材最后一行的截图杂边


def plain(name):
    img = load(name)
    if name == "开场.png":
        img = img.crop((0, 1, 1080, 168))
    elif name == "终场.png":
        img = img.crop((0, 0, 1080, 112))
    return dict(img=img, minute=None, h=img.height, left=[], right=[])


def goal_row(minute, text, side):
    img = load("左队/左队进球.png" if side == "L" else "右队/右队进球.jpg")
    return dict(img=img, minute=minute, h=img.height,
                left=[(48, text)] if side == "L" else [],
                right=[(44, text)] if side == "R" else [])


def sub_row(minute, left_texts, right_texts):
    L = (load("左队/左队连换两人.png") if len(left_texts) > 2 else load("左队/左队换一人.png")) if left_texts else None
    R = (load("右队/右队连换两人.png") if len(right_texts) > 2 else load("右队/右队换一人.png")) if right_texts else None
    H = max(x.height for x in (L, R) if x)
    canvas = Image.new("RGB", (W, H), BG)
    if L and R:
        canvas.paste(L.crop((0, 0, CX, L.height)), (0, 0))
        canvas.paste(R.crop((CX, 0, W, R.height)), (CX, 0))
        if L.height != R.height:                       # 两侧行高不同，补齐中轴线
            y0 = min(L.height, R.height) - 8
            d = ImageDraw.Draw(canvas)
            d.rectangle([538, y0, 541, H - 1], fill=GREEN)
            d.rectangle([542, y0, 542, H - 1], fill=AA_GREEN)
    elif L:
        canvas.paste(L, (0, 0))
        ImageDraw.Draw(canvas).rectangle([575, 0, W, H], fill=BG)
    else:
        canvas.paste(R, (0, 0))
        ImageDraw.Draw(canvas).rectangle([0, 0, 505, H], fill=BG)
    yl = ([46, 102] if len(left_texts) <= 2 else [46, 105, 163, 221])[:len(left_texts)]
    yr = ([46, 103] if len(right_texts) <= 2 else [46, 103, 161, 219])[:len(right_texts)]
    return dict(img=canvas, minute=minute, h=H,
                left=list(zip(yl, left_texts)), right=list(zip(yr, right_texts)))


def card_row(minute, text, side, kind="黄牌"):
    names = {"黄牌": ("左队/左队黄牌.png", "右队/右队黄牌.png"),
             "直接红牌": ("左队/左队直接红牌.png", "右队/右队直接红牌.png"),
             "两黄变一红": ("左队/左队两黄变一红.png", "右队/右队两黄变一红.png")}
    img = load(names[kind][0 if side == "L" else 1])
    return dict(img=img, minute=minute, h=img.height,
                left=[(46, text)] if side == "L" else [],
                right=[(46, text)] if side == "R" else [])


def ht_row(label="HT"):
    H, S = 150, 4
    tmp = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.rectangle([538 * S, 0, 541 * S + S - 1, H * S], fill=GREEN + (255,))
    d.rectangle([542 * S, 0, 542 * S + S - 1, H * S], fill=AA_GREEN + (255,))
    d.ellipse([(CX - 28) * S, 3 * S, (CX + 28) * S - 1, 59 * S - 1], fill=GREEN + (255,))
    f = ImageFont.truetype(FONT_PATH, 22 * S, index=FONT_INDEX)
    d.text((CX * S, 31 * S), label, font=f, fill=WHITE + (255,), anchor="mm")
    tmp = tmp.resize((W, H), Image.LANCZOS)
    img = Image.alpha_composite(Image.new("RGBA", (W, H), BG + (255,)), tmp).convert("RGB")
    return dict(img=img, minute=None, h=H, left=[], right=[])


def build(rows, out):
    H = sum(r["h"] for r in rows) + PAD_TOP_BOTTOM
    canvas = Image.new("RGB", (W, H), BG)
    y = 0
    for r in rows:
        canvas.paste(r["img"], (0, y))
        y += r["h"]
    d = ImageDraw.Draw(canvas)
    y = 0
    for r in rows:
        if r["minute"]:
            d.text((CX, y + (32 if r["h"] > 300 else 31)), str(r["minute"]),
                   font=font(SIZE_NUM), fill=WHITE, anchor="mm")
        for ly, t in r["left"]:
            d.text((X_LEFT, y + ly), t, font=fit(t, 340), fill=BLACK, anchor="rm")
        for ly, t in r["right"]:
            d.text((X_RIGHT, y + ly), t, font=fit(t, 340), fill=BLACK, anchor="lm")
        y += r["h"]
    canvas.save(out)
    return out, canvas.size


def rows_from_events(events):
    evs = sorted(events, key=lambda e: (e["minute"], 0 if e.get("type") == "ht" else 1))
    rows, i = [], 0
    score = [0, 0]
    while i < len(evs):
        e = evs[i]
        minute, typ = e["minute"], e.get("type")
        if typ == "ht":
            rows.append(ht_row(e.get("label", "HT")))
            i += 1
            continue
        # 同一分钟、双方各一条 sub → 合成一行
        if typ == "sub" and i + 1 < len(evs) and evs[i + 1].get("type") == "sub" \
                and evs[i + 1]["minute"] == minute and evs[i + 1]["side"] != e["side"]:
            pair = [e, evs[i + 1]]
            home = next(x for x in pair if x["side"] == "home")
            away = next(x for x in pair if x["side"] == "away")
            rows.append(sub_row(minute, home.get("on", []) + home.get("off", []),
                                away.get("on", []) + away.get("off", [])))
            i += 2
            continue
        if typ == "sub":
            on, off = e.get("on", []), e.get("off", [])
            if e["side"] == "home":
                rows.append(sub_row(minute, on + off, []))
            else:
                rows.append(sub_row(minute, [], on + off))
        elif typ == "goal":
            if "score" in e:
                score = list(e["score"])
            else:
                score[0 if e["side"] == "home" else 1] += 1
            txt = f"（{score[0]}:{score[1]}）{e['player']}" if e["side"] == "home" \
                else f"{e['player']}（{score[0]}:{score[1]}）"
            rows.append(goal_row(minute, txt, "L" if e["side"] == "home" else "R"))
        elif typ == "card":
            rows.append(card_row(minute, e["player"], "L" if e["side"] == "home" else "R",
                                 e.get("kind", "黄牌")))
        else:
            raise SystemExit(f"未知事件类型: {typ}")
        i += 1
    return rows


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    spec_path = sys.argv[1]
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else \
        spec.get("output", {}).get("timeline", "比赛进程.png")
    rows = [plain("开场.png")] + rows_from_events(spec.get("events", [])) + [plain("终场.png")]
    path, size = build(rows, out)
    print(f"时间轴已生成: {path}  {size[0]}x{size[1]}")


if __name__ == "__main__":
    main()
