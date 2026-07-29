#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
近畿POPUP.md を読み込み、旅のしおり index.html を生成する。
デザインは「47 CARAVAN 原点回帰」風の 黒 × ゴールド。
md のフォーマット（・セクション / 【路線名】/ 時刻 / URL）をパースして
コンポーネント（時刻表カード・POPUPバナー・スポット・自由記述）に流し込む。
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
MDLINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")   # [表示](URL) 記法
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
    if any(k in n.upper() for k in ("POPUP", "CARAVAN")) or any(k in n for k in ("ポップアップ", "キャラバン")):
        return "popup"
    if "宿" in n:
        return "stay"
    if any(k in n for k in ["デザート", "朝食", "昼食", "夜飯", "ディナー", "ランチ",
                            "カフェ", "ごはん", "ご飯", "飯", "食"]):
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
PLACE_RE = re.compile(r"^(.*?)[（(](.*?)[）)]\s*$")


def split_place(place):
    """「滋賀（古民家カフェツナグ 1F-穴太駅）」を
    見出し『滋賀 · 穴太駅』と会場名『古民家カフェツナグ 1F』に分ける。
    スマホで1行に収まらず折り返して不格好になるのを避けるため。"""
    m = PLACE_RE.match(place)
    if not m:
        return place, ""
    area = m.group(1).strip()
    inner = m.group(2).strip()
    # 最後の区切り以降を最寄駅とみなす（会場名にハイフンが入っていてもよい）
    parts = re.split(r"[-－−‐–—]", inner)   # 長音「ー」は区切りにしない（ニューヨッカイチビル等が壊れる）
    if len(parts) >= 2 and parts[-1].strip():
        venue = "-".join(p.strip() for p in parts[:-1]).strip()
        station = parts[-1].strip()
    else:
        venue, station = "", inner
    head = f"{area} · {station}" if area and station else (area or station)
    return head, venue


def _popup_banner(m):
    t = f"{int(m.group(1)):02d}:00 – {int(m.group(2)):02d}:00"
    head, venue = split_place(m.group(3).strip())
    inner = (
        f'        <span class="pinfo"><span class="pt">{esc(t)}</span>'
        f'<span class="pp">{esc(head)}</span></span>\n'
    )
    if venue:
        inner += f'        <span class="pvenue">{esc(venue)}</span>\n'
    return (
        '    <div class="item event">\n'
        '      <div class="popup">\n'
        '        <span class="badge">POP UP</span>\n'
        f"{inner}"
        "      </div>\n"
        "    </div>"
    )


def render_popup(lines):
    """POPUPの時間帯バナーに加え、会場名・住所・アクセス・MAPも出す。
    （以前はバナー行以外を捨てていたので、mdに書いた会場情報がサイトに出なかった）"""
    items = []
    pending = []          # バナー直後に続く会場情報

    def flush():
        if not pending:
            return
        intro, trains = render_move(list(pending))   # 【路線名】があれば時刻表カードに
        if intro:
            items.append(text_card("", intro))
        items.extend(trains)
        pending.clear()

    for ln in lines:
        m = POPUP_RE.search(ln)
        if m:
            flush()
            items.append(_popup_banner(m))
            continue
        pending.append(ln)
    flush()
    return items


# ----------------------------------------------------------------------
# レンダリング：スポット / 候補
# ----------------------------------------------------------------------
def render_spot(name, lines, kind):
    url = ""
    time = ""
    texts = []
    for ln in lines:
        m = MDLINK_RE.search(ln)          # [表示](URL) 記法にも対応
        if m:
            url = m.group(2)
            continue
        u = URL_RE.search(ln)
        if u:
            url = u.group(0).rstrip("）)。、,")
            continue
        if TIMEBADGE_RE.match(ln):
            time = ln
            continue
        texts.append(ln)

    spot_cls = "spot"
    if kind == "eat":
        spot_cls += " eat"
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
        label = "MAP ↗"
        if kind == "stay":
            label = "宿を見る ↗"
        inner.append(
            f'        <a class="btn" href="{esc(url)}" target="_blank" '
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


def text_card(name, lines):
    """電車カードにならない自由記述（例：ゆうかの移動プラン）を、そのまま順番どおり出す。
    URL は文中に長いまま出さず、下の MAP ボタンにまとめる。"""
    body = []
    urls = []
    for ln in lines:
        # [表示テキスト](URL) の記法 → URLを拾って本文からは消す
        for m in MDLINK_RE.finditer(ln):
            urls.append(m.group(2))
        ln = MDLINK_RE.sub("", ln)
        # 生のURL → 同じく拾って本文からは消す
        for m in URL_RE.finditer(ln):
            urls.append(m.group(0))
        ln = URL_RE.sub("", ln)
        # 「乗車地地図URL：」のような、URLを消したら用済みになるラベル行は捨てる
        ln = re.sub(r"[：:]\s*$", "", ln.strip())
        if len(ln) <= 12 and re.search(r"(URL|url|リンク)$", ln):
            ln = ""
        if ln:
            body.append(ln)

    seen, links = set(), []
    for u in urls:
        u = u.rstrip("）)。、,")
        if u not in seen:
            seen.add(u)
            links.append(u)

    inner = ""
    if name:
        inner += f'        <div class="kind">{esc(name)}</div>\n'
    if body:
        inner += '        <p class="note">%s</p>\n' % "<br>".join(esc(x) for x in body)
    for u in links:
        label = "MAP ↗" if "maps" in u or "map" in u else "リンク ↗"
        inner += (
            f'        <a class="btn" href="{esc(u)}" target="_blank" '
            f'rel="noopener">{label}</a>\n'
        )
    return (
        '    <div class="item">\n'
        '      <div class="spot">\n'
        f"{inner.rstrip()}\n"
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
        return name, render_popup(lines)
    # スポット系でも【路線名】が混ざっていたら、時刻表カードとして切り出す
    intro, trains = render_move(lines)
    if trains:
        out = []
        if intro:
            out.append(render_spot(name, intro, kind))
        out += trains
        return name, out
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
        f'  <p class="sub"><span>{esc(title)}</span></p>\n'
        '  <div class="tl">\n'
        f"{items_html}\n"
        "  </div>"
    )


# ----------------------------------------------------------------------
# ページ全体（黒 × ゴールド）
# ----------------------------------------------------------------------
STYLE = r"""<style>
  :root {
    --bg: #0a0a0c;
    --panel: #141216;
    --panel-2: #1a171e;
    --gold: #d7b45a;
    --gold-b: #f3e0a0;
    --gold-d: #9c7a30;
    --ink: #f3eee2;
    --ink-soft: #b7ad94;
    --ink-dim: #877d66;
    --line: rgba(215,180,90,.28);
    --line-strong: rgba(215,180,90,.55);
    --serif: "Hiragino Mincho ProN", "游明朝", "Yu Mincho", serif;
    --gothic: "Hiragino Sans", "游ゴシック体", "Yu Gothic", system-ui, sans-serif;
    --mono: "SF Mono", "Menlo", "Courier New", monospace;
    --gold-grad: linear-gradient(172deg, #f7e7ad 0%, #e3c56e 42%, #b9902f 100%);
  }

  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body {
    margin: 0;
    background:
      radial-gradient(1100px 460px at 50% -6%, rgba(215,180,90,.13), transparent 62%),
      radial-gradient(760px 620px at 108% 102%, rgba(215,180,90,.06), transparent 70%),
      radial-gradient(680px 560px at -8% 90%, rgba(215,180,90,.05), transparent 70%),
      var(--bg);
    color: var(--ink);
    font-family: var(--gothic);
    line-height: 1.75;
    -webkit-font-smoothing: antialiased;
  }
  /* ポスター外枠 */
  body::before {
    content: "";
    position: fixed; inset: 7px;
    border: 1px solid var(--line);
    pointer-events: none; z-index: 50;
  }
  .wrap { max-width: 760px; margin: 0 auto; padding: 0 20px 88px; }

  .gold { background: var(--gold-grad); -webkit-background-clip: text; background-clip: text; color: transparent; }

  /* ===== 表紙 ===== */
  .cover {
    position: relative;
    margin: 22px 0 12px;
    padding: 54px 26px 46px;
    background: linear-gradient(158deg, #17141a 0%, #0c0b0e 72%);
    border: 1px solid var(--line-strong);
    text-align: center;
    overflow: hidden;
  }
  .cover::before {
    content: "";
    position: absolute; inset: 9px;
    border: 1px solid var(--line);
    pointer-events: none;
  }
  .cover::after {
    content: "";
    position: absolute; left: 0; right: 0; top: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--gold), transparent);
    opacity: .8;
  }
  .cover .eyebrow {
    position: relative;
    font-family: var(--mono); letter-spacing: .42em; font-size: 11px;
    color: var(--gold); opacity: .92; margin: 0 0 20px; padding-left: .42em;
  }
  .cover h1 {
    position: relative;
    font-family: var(--serif); font-weight: 700;
    font-size: clamp(38px, 9vw, 62px); letter-spacing: .04em;
    margin: 0; line-height: 1.28; text-wrap: balance;
    background: var(--gold-grad); -webkit-background-clip: text; background-clip: text; color: transparent;
    text-shadow: 0 1px 26px rgba(215,180,90,.22);
  }
  .cover .rule {
    position: relative;
    display: flex; align-items: center; justify-content: center; gap: 12px;
    margin: 20px auto 18px; max-width: 320px; color: var(--gold);
  }
  .cover .rule::before, .cover .rule::after {
    content: ""; flex: 1; height: 1px;
    background: linear-gradient(90deg, transparent, var(--line-strong), transparent);
  }
  .cover .rule span { font-size: 11px; letter-spacing: .2em; }
  .cover .route {
    position: relative;
    margin: 0 auto; font-family: var(--serif); font-size: 15px;
    letter-spacing: .16em; color: var(--ink); max-width: 480px;
  }
  .cover .dates {
    position: relative;
    display: inline-block; margin-top: 24px; padding: 7px 22px;
    border: 1px solid var(--line-strong); border-radius: 1px;
    font-family: var(--mono); letter-spacing: .26em; font-size: 12.5px;
    color: var(--gold-b);
  }

  .lead {
    text-align: center; color: var(--ink-soft); font-size: 14px;
    margin: 26px auto 34px; max-width: 540px; line-height: 1.95;
    font-family: var(--serif);
  }

  /* ===== 日ラベル ===== */
  .day {
    display: flex; align-items: baseline; gap: 16px;
    margin: 56px 0 8px; padding-bottom: 14px;
    border-bottom: 1px solid var(--line-strong);
  }
  .day .num {
    font-family: var(--serif); font-size: clamp(30px, 7vw, 46px); font-weight: 700;
    letter-spacing: .04em; line-height: 1; white-space: nowrap; flex-shrink: 0;
    background: var(--gold-grad); -webkit-background-clip: text; background-clip: text; color: transparent;
    text-shadow: 0 1px 20px rgba(215,180,90,.18);
  }
  .day .meta { display: flex; flex-direction: column; min-width: 0; gap: 2px; }
  .day .date { font-family: var(--mono); font-size: 12.5px; letter-spacing: .2em; color: var(--gold); }
  .day .place { font-size: 14px; letter-spacing: .1em; font-weight: 600; color: var(--ink); }

  /* ===== セクション見出し（──◆ 見出し ◆──）===== */
  .sub {
    display: flex; align-items: center; justify-content: center; gap: 16px;
    margin: 40px 0 8px;
  }
  .sub::before, .sub::after {
    content: ""; flex: 1; height: 1px; max-width: 160px;
    background: linear-gradient(90deg, transparent, var(--line-strong));
  }
  .sub::after { background: linear-gradient(90deg, var(--line-strong), transparent); }
  .sub span {
    font-family: var(--serif); font-size: 14px; letter-spacing: .22em;
    color: var(--gold-b); white-space: nowrap;
  }
  .sub span::before { content: "◆"; color: var(--gold); font-size: 8px; vertical-align: 3px; margin-right: 12px; }
  .sub span::after  { content: "◆"; color: var(--gold); font-size: 8px; vertical-align: 3px; margin-left: 12px; }

  /* ===== タイムライン ===== */
  .tl { position: relative; margin: 22px 0 0; padding-left: 26px; }
  .tl::before {
    content: ""; position: absolute; left: 5px; top: 8px; bottom: 8px;
    width: 1px; background: linear-gradient(var(--line-strong), var(--line));
  }
  .item { position: relative; margin-bottom: 18px; }
  .item::before {
    content: ""; position: absolute; left: -25px; top: 7px;
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--bg); border: 1.5px solid var(--gold-d);
    box-shadow: 0 0 0 3px rgba(215,180,90,.08);
  }
  .item.event::before {
    background: radial-gradient(circle, var(--gold-b), var(--gold));
    border-color: var(--gold-b);
    box-shadow: 0 0 10px rgba(215,180,90,.55);
  }

  /* 移動カード（時刻表） */
  .move {
    background: linear-gradient(160deg, var(--panel), #0f0d11);
    border: 1px solid var(--line); border-radius: 3px;
    padding: 13px 15px;
  }
  .move .lineName {
    display: inline-block; font-size: 11px; letter-spacing: .16em; font-weight: 700;
    color: var(--gold-b); border: 1px solid var(--line-strong);
    padding: 2px 10px; border-radius: 999px; margin-bottom: 10px;
  }
  .leg {
    display: grid; grid-template-columns: 62px 1fr; gap: 4px 12px;
    font-variant-numeric: tabular-nums; align-items: center; padding: 4px 0;
  }
  .leg + .leg { border-top: 1px dashed var(--line); }
  .leg .t { font-family: var(--mono); font-size: 14px; letter-spacing: .04em; color: var(--gold); }
  .leg .s { font-size: 14px; letter-spacing: .05em; color: var(--ink); }
  .leg .s small { color: var(--ink-dim); font-size: 11.5px; letter-spacing: .06em; margin-left: 2px; }

  /* スポット / 候補 / 自由記述 */
  .spot {
    position: relative;
    background: linear-gradient(160deg, var(--panel), #0f0d11);
    border: 1px solid var(--line); border-left: 2px solid var(--gold);
    border-radius: 3px; padding: 12px 15px;
  }
  .spot.eat  { border-left-color: var(--gold-b); }
  .spot.stay { border-left-color: var(--gold-d); }
  .spot .kind { font-size: 10.5px; letter-spacing: .2em; font-weight: 700; color: var(--gold); text-transform: uppercase; }
  .spot .name { font-family: var(--serif); font-size: 16px; font-weight: 600; margin: 3px 0 6px; letter-spacing: .03em; color: var(--ink); }
  .spot .note { font-size: 13px; color: var(--ink-soft); margin: 0 0 8px; line-height: 1.85; }

  a.btn {
    display: inline-flex; align-items: center; gap: 6px; font-family: var(--mono);
    font-size: 11.5px; letter-spacing: .12em; text-decoration: none;
    color: var(--gold-b); font-weight: 600;
    border: 1px solid var(--line-strong); border-radius: 999px; padding: 4px 14px;
    transition: background .18s, color .18s, border-color .18s;
  }
  a.btn:hover { background: var(--gold); color: #17130a; border-color: var(--gold); }
  a.btn:focus-visible { outline: 2px solid var(--gold-b); outline-offset: 2px; }

  .tbd {
    font-size: 12px; letter-spacing: .08em; color: var(--ink-dim);
    border: 1px dashed var(--line); border-radius: 3px;
    padding: 9px 13px; background: rgba(255,255,255,.012);
  }

  /* POPUPバナー */
  .popup {
    display: flex; align-items: center; flex-wrap: wrap; gap: 10px 14px;
    background: linear-gradient(160deg, #1c1710, #0e0b07);
    border: 1px solid var(--gold-d); border-radius: 3px; padding: 12px 16px;
    box-shadow: inset 0 0 22px rgba(215,180,90,.06);
  }
  .popup .badge {
    font-family: var(--serif); font-weight: 700; font-size: 12px;
    color: #17130a; background: var(--gold-grad);
    padding: 4px 12px; border-radius: 2px; letter-spacing: .14em; white-space: nowrap;
  }
  .popup .pinfo { display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 14px; }
  .popup .pt { font-family: var(--mono); font-size: 13px; letter-spacing: .06em; color: var(--gold-b); }
  .popup .pp { font-family: var(--serif); font-weight: 600; letter-spacing: .08em; color: var(--ink); }
  /* 会場名は見出しの下に小さく置く（長くても行が割れて見えないように） */
  .popup .pvenue {
    flex-basis: 100%; font-family: var(--serif); font-size: 13px; line-height: 1.7;
    letter-spacing: .04em; color: var(--gold-b); opacity: .92;
    padding-left: 2px; word-break: normal; overflow-wrap: anywhere;
  }
  @media (max-width: 480px) {
    .popup { gap: 8px 10px; padding: 12px 13px; }
    .popup .badge { font-size: 11px; padding: 3px 10px; }
    .popup .pinfo { gap: 2px 10px; }
    .popup .pp { font-size: 15px; line-height: 1.6; }
    .popup .pvenue { font-size: 12.5px; }
  }

  /* しめ */
  .foot {
    margin-top: 62px; padding-top: 26px; text-align: center;
    border-top: 1px solid var(--line-strong);
  }
  .foot p { font-family: var(--serif); font-size: 15px; letter-spacing: .12em; margin: 0 0 8px;
            background: var(--gold-grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .foot small { color: var(--ink-dim); font-size: 11.5px; letter-spacing: .14em; font-family: var(--mono); }

  @media (max-width: 380px) {
    .wrap { padding: 0 16px 70px; }
    .cover { padding: 46px 18px 40px; }
    .cover .eyebrow { letter-spacing: .28em; font-size: 10px; }
    .cover .dates { letter-spacing: .14em; font-size: 11.5px; padding: 7px 15px; }
    .day { gap: 12px; }
    .day .num { font-size: 32px; }
    .sub::before, .sub::after { max-width: 60px; }
    .sub span { font-size: 13px; letter-spacing: .16em; }
    .leg { grid-template-columns: 56px 1fr; column-gap: 10px; }
  }
</style>"""


def build_page(days):
    body_days = "\n\n".join(render_day(d, i) for i, d in enumerate(days))

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
<meta name="theme-color" content="#0a0a0c">
<title>西へ、途中下車。｜{esc(title_dates)}</title>
{STYLE}
</head>
<body>
<div class="wrap">

  <header class="cover">
    <p class="eyebrow">TWO DAYS · WESTBOUND CARAVAN</p>
    <h1>西へ、<br>途中下車。</h1>
    <div class="rule"><span>原点回帰</span></div>
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
    <small>PLAN A — 予定は変わってもいい。ふたりのペースで。</small>
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
