#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
近畿POPUP.md を読み込み、旅のしおり index.html を生成する。
md のフォーマット（・セクション / 【路線名】/ 時刻 / URL）をパースして
既存デザインのコンポーネント（時刻表カード・POPUPバナー・スポット）に流し込む。
"""
import re
import os
import html

# --- パス設定（環境変数で上書き可）---
MD_PATH = os.environ.get(
    "MD_PATH",
    "/Users/takuya/Library/Mobile Documents/iCloud~md~obsidian/Documents/藤原拓矢/近畿POPUP.md",
)
OUT_PATH = os.environ.get(
    "OUT_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"),
)

YEAR = os.environ.get("SHIORI_YEAR", "2026")
ROUTE = "石川 → 滋賀 → 三重 → 奈良 →〈翌〉大阪"

KANSUJI = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]

URL_RE = re.compile(r"https?://\S+")
DATE_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})\s*$")
TIME_RANGE_RE = re.compile(r"(\d{1,2}:\d{2})\s*[-–~〜]\s*(\d{1,2}:\d{2})")
TIME_HEAD_RE = re.compile(r"^(\d{1,2}:\d{2})")
POPUP_RE = re.compile(r"(\d{1,2})\s*[-–~]\s*(\d{1,2})\s*時\s*(.*)")
TIMEBADGE_RE = re.compile(r"^\d{1,2}:\d{2}\s*[〜~]")


def esc(s):
    return html.escape(s, quote=True)


# ----------------------------------------------------------------------
# パース
# ----------------------------------------------------------------------
def parse(md):
    days = []
    cur_day = None
    cur_sec = None
    for raw in md.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = DATE_RE.match(line)
        if m:
            cur_day = {"date": (int(m.group(1)), int(m.group(2))), "sections": [], "subtitle": []}
            days.append(cur_day)
            cur_sec = None
            continue
        if line.startswith("・"):
            if cur_day is None:
                cur_day = {"date": None, "sections": [], "subtitle": []}
                days.append(cur_day)
            cur_sec = {"name": line[1:].strip(), "lines": []}
            cur_day["sections"].append(cur_sec)
            continue
        if cur_day is None:
            cur_day = {"date": None, "sections": [], "subtitle": []}
            days.append(cur_day)
        if cur_sec is None:
            # セクション（・）が始まる前の行＝その日の概要（サブタイトル）
            cur_day["subtitle"].append(line)
            continue
        cur_sec["lines"].append(line)
    return days


def section_kind(name):
    n = name
    if "移動" in n:
        return "move"
    if "POPUP" in n.upper() or "ポップアップ" in n:
        return "popup"
    if "宿" in n:
        return "stay"
    if any(k in n for k in ["デザート", "朝食", "昼食", "夜飯", "ディナー", "ランチ",
                            "カフェ", "ごはん", "ご飯", "飯", "ランチ", "食"]):
        return "eat"
    return "spot"


# ----------------------------------------------------------------------
# レンダリング：移動（時刻表カード）
# ----------------------------------------------------------------------
def render_move(lines):
    intro = []
    blocks = []
    cur = None
    for ln in lines:
        if ln.startswith("【"):
            cur = {"name": ln.strip("【】"), "rows": []}
            blocks.append(cur)
        elif cur is None:
            intro.append(ln)
        else:
            cur["rows"].append(ln)

    items = []
    for b in blocks:
        legs = build_legs(b["rows"])
        if not legs:
            continue
        leg_html = "\n".join(legs)
        items.append(
            '    <div class="item">\n'
            '      <div class="move">\n'
            f'        <span class="lineName">{esc(b["name"])}</span>\n'
            f"{leg_html}\n"
            "      </div>\n"
            "    </div>"
        )
    return intro, items


def build_legs(rows):
    legs = []
    i = 0
    while i < len(rows):
        r = rows[i]
        rng = TIME_RANGE_RE.search(r)
        if rng and "から" not in r:
            dep, arr = rng.group(1), rng.group(2)
            if i + 1 < len(rows) and "から" in rows[i + 1]:
                a, b = re.split("から", rows[i + 1], maxsplit=1)
                legs.append(leg_html(dep, a.strip(), "発"))
                legs.append(leg_html(arr, b.strip(), "着"))
                i += 2
                continue
            i += 1
            continue
        head = TIME_HEAD_RE.match(r)
        if head:
            t = head.group(1)
            rest = r[len(t):].strip("　 ").strip()
            suffix = ""
            for suf in ("発", "着"):
                if rest.endswith(suf):
                    rest = rest[:-1].strip()
                    suffix = suf
                    break
            legs.append(leg_html(t, rest, suffix))
            i += 1
            continue
        # 時刻なし＝経由駅（例：山科駅）
        legs.append(leg_html("–", r.strip(), "経由"))
        i += 1
    return legs


def leg_html(t, station, suffix):
    tt = "&nbsp;–" if t == "–" else esc(t)
    s = esc(station)
    if suffix:
        s += f' <small>{esc(suffix)}</small>'
    return f'        <div class="leg"><span class="t">{tt}</span><span class="s">{s}</span></div>'


# ----------------------------------------------------------------------
# レンダリング：POPUP バナー
# ----------------------------------------------------------------------
def render_popup(lines):
    items = []
    for ln in lines:
        m = POPUP_RE.search(ln)
        if not m:
            continue
        t = f"{int(m.group(1)):02d}:00 – {int(m.group(2)):02d}:00"
        place = m.group(3).strip()
        items.append(
            '    <div class="item event">\n'
            '      <div class="popup">\n'
            '        <span class="badge">POP UP</span>\n'
            f'        <span><span class="pt">{esc(t)}</span> &nbsp;/&nbsp; '
            f'<span class="pp">{esc(place)}</span></span>\n'
            "      </div>\n"
            "    </div>"
        )
    return items


# ----------------------------------------------------------------------
# レンダリング：スポット / 候補
# ----------------------------------------------------------------------
def render_spot(name, lines, kind):
    url = ""
    time = ""
    texts = []
    for ln in lines:
        u = URL_RE.search(ln)
        if u:
            url = u.group(0)
            continue
        if TIMEBADGE_RE.match(ln):
            time = ln
            continue
        texts.append(ln)

    spot_cls = "spot"
    btn_cls = "btn"
    if kind == "eat":
        spot_cls += " eat"
        btn_cls += " eat"
    elif kind == "stay":
        spot_cls += " stay"

    undecided = (not texts and not url) or any(t.startswith("未定") for t in texts)
    if undecided:
        note = texts[0] if texts else "未定"
        return (
            '    <div class="item">\n'
            f'      <div class="tbd">{esc(note)}</div>\n'
            "    </div>"
        )

    name_line = texts[0] if texts else ""
    note_parts = []
    if time:
        note_parts.append(time)
    note_parts += texts[1:]
    note = "　".join(note_parts)

    inner = [f'        <div class="kind">{esc(name)}</div>']
    if name_line:
        inner.append(f'        <div class="name">{esc(name_line)}</div>')
    if note:
        inner.append(f'        <p class="note">{esc(note)}</p>')
    if url:
        label = "地図をひらく ↗"
        if kind == "stay":
            label = "宿を見る ↗"
        inner.append(
            f'        <a class="{btn_cls}" href="{esc(url)}" target="_blank" '
            f'rel="noopener">{label}</a>'
        )
    inner_html = "\n".join(inner)
    return (
        '    <div class="item">\n'
        f'      <div class="{spot_cls}">\n'
        f"{inner_html}\n"
        "      </div>\n"
        "    </div>"
    )


# ----------------------------------------------------------------------
# 1日分をレンダリング
# ----------------------------------------------------------------------
def text_card(name, lines):
    """電車カードにならない自由記述（例：ゆうかの移動プラン）を、そのまま順番どおり出す。"""
    note = "<br>".join(esc(x) for x in lines)
    inner = ""
    if name:
        inner += f'        <div class="kind">{esc(name)}</div>\n'
    inner += f'        <p class="note">{note}</p>'
    return (
        '    <div class="item">\n'
        '      <div class="spot">\n'
        f"{inner}\n"
        "      </div>\n"
        "    </div>"
    )


def render_section(sec):
    """1セクションを描画。書かれた内容は落とさず、順番どおりに出す。"""
    name = sec["name"]
    kind = section_kind(name)
    lines = sec["lines"]
    if kind == "move":
        intro, items = render_move(lines)
        out = []
        if intro:                       # 【路線名】以外の文章もカードにして残す
            out.append(text_card(name, intro))
        out += items
        return name, out
    if kind == "popup":
        return "POPUP", render_popup(lines)
    return name, [render_spot(name, lines, kind)]


def render_day(day, index):
    num = (KANSUJI[index + 1] if index + 1 < len(KANSUJI) else str(index + 1)) + "日目"
    date_str = ""
    if day["date"]:
        mm, dd = day["date"]
        date_str = f"{mm} / {dd}"

    place = "　".join(day.get("subtitle", []))
    blocks_html = []
    for sec in day["sections"]:
        title, items = render_section(sec)
        if items:
            blocks_html.append(section_block(title, items))

    head_meta = f'      <span class="date">{esc(date_str)}</span>'
    if place:
        head_meta += f'\n      <span class="place">{esc(place)}</span>'

    day_head = (
        '  <div class="day">\n'
        f'    <div class="num">{esc(num)}</div>\n'
        '    <div class="meta">\n'
        f"{head_meta}\n"
        "    </div>\n"
        "  </div>"
    )
    return day_head + "\n\n" + "\n\n".join(blocks_html)


def section_block(title, items):
    items_html = "\n".join(items)
    return (
        f'  <p class="sub">▶ {esc(title)}</p>\n'
        '  <div class="tl">\n'
        f"{items_html}\n"
        "  </div>"
    )


# ----------------------------------------------------------------------
# ページ全体
# ----------------------------------------------------------------------
STYLE = r"""<style>
  :root {
    --paper: #f4efe2; --paper-2: #ece5d3; --ink: #26332e; --ink-soft: #5a675f;
    --rail: #16594a; --rail-deep: #0f3d33; --stamp: #c0392b; --gold: #b0872f;
    --line: #c9bfa4; --card: #fbf8ef; --shadow: rgba(40,50,40,.14); --dot: #16594a;
    --serif: "Hiragino Mincho ProN", "游明朝", "Yu Mincho", serif;
    --gothic: "Hiragino Sans", "游ゴシック体", "Yu Gothic", system-ui, sans-serif;
    --mono: "SF Mono", "Menlo", "Courier New", monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --paper: #1c211d; --paper-2: #161a17; --ink: #ece5d3; --ink-soft: #a9b3a8;
      --rail: #6fc4ae; --rail-deep: #9dd8c7; --stamp: #e5766a; --gold: #d4ac5e;
      --line: #3a453c; --card: #232a25; --shadow: rgba(0,0,0,.4); --dot: #6fc4ae;
    }
  }
  :root[data-theme="light"] {
    --paper: #f4efe2; --paper-2: #ece5d3; --ink: #26332e; --ink-soft: #5a675f;
    --rail: #16594a; --rail-deep: #0f3d33; --stamp: #c0392b; --gold: #b0872f;
    --line: #c9bfa4; --card: #fbf8ef; --shadow: rgba(40,50,40,.14); --dot: #16594a;
  }
  :root[data-theme="dark"] {
    --paper: #1c211d; --paper-2: #161a17; --ink: #ece5d3; --ink-soft: #a9b3a8;
    --rail: #6fc4ae; --rail-deep: #9dd8c7; --stamp: #e5766a; --gold: #d4ac5e;
    --line: #3a453c; --card: #232a25; --shadow: rgba(0,0,0,.4); --dot: #6fc4ae;
  }

  * { box-sizing: border-box; }
  body {
    margin: 0;
    background:
      radial-gradient(circle at 50% -10%, color-mix(in srgb, var(--rail) 6%, transparent), transparent 60%),
      var(--paper);
    color: var(--ink);
    font-family: var(--gothic);
    line-height: 1.75;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 760px; margin: 0 auto; padding: 0 20px 80px; }

  .cover {
    position: relative;
    margin: 0 -20px 12px;
    padding: 64px 28px 52px;
    background:
      repeating-linear-gradient(90deg, transparent 0 22px, color-mix(in srgb, var(--rail) 8%, transparent) 22px 24px),
      linear-gradient(160deg, var(--rail-deep), var(--rail));
    color: #f4efe2;
    text-align: center;
    overflow: hidden;
  }
  .cover::before, .cover::after {
    content: "";
    position: absolute; left: 0; right: 0; height: 16px;
    background: radial-gradient(circle at 8px 0, var(--paper) 7px, transparent 8px) repeat-x;
    background-size: 16px 16px;
  }
  .cover::before { top: -8px; }
  .cover::after { bottom: -8px; transform: rotate(180deg); }
  .cover .eyebrow {
    font-family: var(--mono); letter-spacing: .5em; font-size: 12px;
    opacity: .85; margin: 0 0 18px; padding-left: .5em;
  }
  .cover h1 {
    font-family: var(--serif); font-weight: 600;
    font-size: clamp(34px, 8vw, 56px); letter-spacing: .06em;
    margin: 0; text-wrap: balance; line-height: 1.3;
  }
  .cover .route { margin: 22px auto 0; font-size: 14px; letter-spacing: .18em; opacity: .92; max-width: 460px; }
  .cover .dates {
    display: inline-block; margin-top: 26px; padding: 7px 20px;
    border: 1px solid rgba(244,239,226,.5); border-radius: 2px;
    font-family: var(--mono); letter-spacing: .28em; font-size: 13px;
  }
  .stamp {
    position: absolute; top: 40px; right: 26px; width: 84px; height: 84px;
    border: 2.5px solid var(--stamp); border-radius: 50%; color: var(--stamp);
    display: grid; place-content: center; text-align: center;
    font-family: var(--serif); font-size: 12px; line-height: 1.4; letter-spacing: .12em;
    transform: rotate(-11deg); opacity: .92; background: rgba(244,239,226,.06);
  }
  .stamp b { display: block; font-size: 19px; letter-spacing: 0; }

  .lead {
    text-align: center; color: var(--ink-soft); font-size: 14.5px;
    margin: 26px auto 40px; max-width: 540px; line-height: 1.9;
  }

  .day {
    display: flex; align-items: baseline; gap: 16px;
    margin: 52px 0 8px; padding-bottom: 12px; border-bottom: 2px solid var(--ink);
  }
  .day .num {
    font-family: var(--serif); font-size: clamp(28px, 6.5vw, 44px); font-weight: 600;
    color: var(--rail); letter-spacing: .02em; line-height: 1; white-space: nowrap; flex-shrink: 0;
  }
  .day .meta { display: flex; flex-direction: column; min-width: 0; }
  .day .date { font-family: var(--mono); font-size: 13px; letter-spacing: .2em; color: var(--ink-soft); }
  .day .place { font-size: 15px; letter-spacing: .12em; font-weight: 600; }

  .tl { position: relative; margin: 26px 0 0; padding-left: 26px; }
  .tl::before { content: ""; position: absolute; left: 5px; top: 8px; bottom: 8px; width: 2px; background: var(--line); }
  .item { position: relative; margin-bottom: 20px; }
  .item::before {
    content: ""; position: absolute; left: -25px; top: 6px;
    width: 12px; height: 12px; border-radius: 50%;
    background: var(--paper); border: 2.5px solid var(--dot);
  }
  .item.event::before { background: var(--stamp); border-color: var(--stamp); }
  .item .time { font-family: var(--mono); font-size: 12.5px; letter-spacing: .1em; color: var(--ink-soft); font-variant-numeric: tabular-nums; }
  .item .head { font-size: 16px; font-weight: 600; letter-spacing: .04em; margin: 1px 0 2px; }

  .move { background: var(--card); border: 1px solid var(--line); border-radius: 4px; padding: 12px 14px; box-shadow: 0 1px 0 var(--shadow); }
  .move .lineName {
    display: inline-block; font-size: 11px; letter-spacing: .14em; font-weight: 700;
    color: var(--rail); background: color-mix(in srgb, var(--rail) 12%, transparent);
    padding: 2px 9px; border-radius: 999px; margin-bottom: 9px;
  }
  .leg { display: grid; grid-template-columns: 62px 1fr; gap: 4px 12px; font-variant-numeric: tabular-nums; align-items: center; padding: 3px 0; }
  .leg + .leg { border-top: 1px dashed var(--line); }
  .leg .t { font-family: var(--mono); font-size: 14px; letter-spacing: .04em; color: var(--ink); }
  .leg .s { font-size: 14px; letter-spacing: .04em; }
  .leg .s small { color: var(--ink-soft); font-size: 12px; letter-spacing: .06em; }

  .spot { background: var(--card); border: 1px solid var(--line); border-left: 4px solid var(--gold); border-radius: 4px; padding: 12px 14px; }
  .spot.eat { border-left-color: var(--stamp); }
  .spot.stay { border-left-color: var(--rail); }
  .spot .kind { font-size: 11px; letter-spacing: .18em; font-weight: 700; color: var(--ink-soft); text-transform: uppercase; }
  .spot .name { font-size: 15.5px; font-weight: 600; margin: 2px 0 6px; letter-spacing: .03em; }
  .spot .note { font-size: 13px; color: var(--ink-soft); margin: 0 0 8px; }

  a.btn {
    display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; letter-spacing: .06em;
    text-decoration: none; color: var(--rail); font-weight: 600;
    border: 1px solid color-mix(in srgb, var(--rail) 40%, transparent);
    border-radius: 999px; padding: 4px 12px; transition: background .15s, color .15s;
  }
  a.btn:hover { background: var(--rail); color: var(--paper); }
  a.btn.eat { color: var(--stamp); border-color: color-mix(in srgb, var(--stamp) 45%, transparent); }
  a.btn.eat:hover { background: var(--stamp); color: #fff; }
  a.btn:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }

  .tbd { font-size: 12px; letter-spacing: .1em; color: var(--ink-soft); border: 1px dashed var(--line); border-radius: 4px; padding: 8px 12px; background: transparent; }

  .popup { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; background: var(--card); border: 1.5px solid var(--stamp); border-radius: 4px; padding: 11px 15px; }
  .popup .badge { font-family: var(--serif); font-weight: 700; font-size: 13px; color: #fff; background: var(--stamp); padding: 3px 10px; border-radius: 3px; letter-spacing: .08em; white-space: nowrap; }
  .popup .pt { font-family: var(--mono); font-size: 13px; letter-spacing: .06em; }
  .popup .pp { font-weight: 600; letter-spacing: .06em; }

  .foot { margin-top: 60px; padding-top: 22px; border-top: 2px solid var(--ink); text-align: center; }
  .foot p { font-family: var(--serif); font-size: 15px; letter-spacing: .1em; color: var(--ink); margin: 0 0 6px; }
  .foot small { color: var(--ink-soft); font-size: 12px; letter-spacing: .12em; }

  .sub { font-size: 13px; letter-spacing: .16em; color: var(--ink-soft); margin: 34px 0 4px; font-weight: 700; }

  @media (max-width: 380px) {
    .cover { padding: 56px 20px 46px; }
    .cover .eyebrow { letter-spacing: .32em; font-size: 11px; }
    .cover .dates { letter-spacing: .16em; font-size: 12px; padding: 7px 14px; }
    .cover .route { letter-spacing: .1em; }
    .stamp { top: 26px; right: 16px; width: 70px; height: 70px; }
    .day { gap: 12px; }
    .day .num { font-size: 30px; }
    .leg { grid-template-columns: 56px 1fr; column-gap: 10px; }
  }
</style>"""


def build_page(days):
    body_days = "\n\n".join(render_day(d, i) for i, d in enumerate(days))

    # 日付レンジ
    date_pairs = [d["date"] for d in days if d["date"]]
    if date_pairs:
        (m1, d1) = date_pairs[0]
        (m2, d2) = date_pairs[-1]
        dates = f"{YEAR}.{m1:02d}.{d1:02d} – {m2:02d}.{d2:02d}"
        title_dates = f"{m1}.{d1}–{m2}.{d2}"
    else:
        dates = YEAR
        title_dates = ""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>西へ、途中下車。｜{esc(title_dates)}</title>
{STYLE}
</head>
<body>
<div class="wrap">

  <header class="cover">
    <div class="stamp"><span>途中下車<b>OK</b>各駅の旅</span></div>
    <p class="eyebrow">TWO DAYS, WESTBOUND</p>
    <h1>西へ、<br>途中下車。</h1>
    <p class="route">{esc(ROUTE)}</p>
    <div class="dates">{esc(dates)}</div>
  </header>

  <p class="lead">
    朝いちの各駅停車から、夜の奈良の地酒まで。<br>
    予定はゆるめ、寄り道は多め。時刻表どおりに、気ままにいきましょう。
  </p>

{body_days}

  <div class="foot">
    <p>いってらっしゃい。よい旅を。</p>
    <small>PLAN A ─ 予定は変わってもいい。ふたりのペースで。</small>
  </div>

</div>
</body>
</html>
"""


def main():
    import sys
    # 引数 '-' で標準入力から md を読む（launchd等がファイルを開いて渡す用）。
    if len(sys.argv) > 1 and sys.argv[1] == "-":
        md = sys.stdin.read()
    else:
        with open(MD_PATH, encoding="utf-8") as f:
            md = f.read()
    days = parse(md)
    page = build_page(days)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"built {OUT_PATH} ({len(days)} days, {len(page)} bytes)")


if __name__ == "__main__":
    main()
