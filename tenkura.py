# -*- coding: utf-8 -*-
"""てんきとくらす (tenkura.n-kishou.co.jp) 山の天気 取得・解析ライブラリ"""
import re
import time
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
BASE = "https://tenkura.n-kishou.co.jp/tk/kanko/"
REGIONS = {"hk": "北海道", "th": "東北", "hr": "北陸", "kk": "関東・甲信",
           "tk": "東海", "kn": "近畿", "cg": "中国", "sk": "四国", "ks": "九州・沖縄"}
IDX = {"mnt1": "A", "mnt2": "B", "mnt3": "C"}
RANK = {"A": 3, "B": 2, "C": 1}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "ja,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("shift_jis", "euc-jp", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("shift_jis", errors="replace")


def clean(t):
    t = re.sub(r"<br\s*/?>", " ", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", t).strip()


def tds(row):
    return re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)


def trs(block):
    return re.findall(r"<tr[^>]*>(.*?)</tr>", block, re.S)


def num(cell):
    """セルから数値を取り出す ('-7℃' -> -7.0, '静穏' -> 0.0, '' -> None)"""
    t = clean(cell)
    if not t:
        return None
    if "静穏" in t:
        return 0.0
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    return float(m.group(0)) if m else None


def parse_mountain(html, code):
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    name = clean(title.group(1)).split("の天気")[0] if title else code
    m = re.search(r"(\d{3,4})\s*m\s*付近", html)
    altitude = int(m.group(1)) if m else None
    m = re.search(r"近隣市町村の気象情報[^<]*<span>\(([^)]+)\)</span>", html)
    municipality = m.group(1) if m else None

    blocks = []
    for chunk in re.split(r'<div class="kad_tbl2"', html)[1:]:
        chunk = chunk.split('<div class="kad_tbl2"')[0]
        if not re.search(r"tozan/mnt\d\.gif", chunk):
            continue
        table = chunk.split("</table>")[0]          # PC版テーブルのみ
        label = ""
        m = re.search(r'<tr class="tit_day">(.*?)</tr>', table, re.S)
        if m:
            c = tds(m.group(1))
            label = clean(c[0]) if c else ""
        for row in trs(table):
            cells = tds(row)
            if not cells:
                continue
            txt = [clean(c) for c in cells]
            if any(t.startswith("時 間") or t.startswith("時間") for t in txt):
                blocks.append({"label": label, "kind": "hourly",
                               "header": txt[1:], "index": [], "temp": [], "wind": []})
            elif any(t.startswith("日 付") or t.startswith("日付") for t in txt):
                blocks.append({"label": label, "kind": "daily",
                               "header": txt[1:], "index": [], "temp": [], "wind": []})
            elif not blocks:
                continue
            elif txt[0].startswith("登山指数"):
                b = blocks[-1]
                b["index"] = []
                for c in cells[1:]:
                    mm = re.search(r"tozan/(mnt\d)\.gif", c)
                    b["index"].append(IDX.get(mm.group(1)) if mm else None)
            elif any(t == "気温" for t in txt) and not blocks[-1]["temp"]:
                blocks[-1]["temp"] = [num(c) for c in cells[-len(blocks[-1]["header"]):]]
            elif (txt[0].startswith("風") or txt[0].startswith("風速")) and not blocks[-1]["wind"]:
                blocks[-1]["wind"] = [num(c) for c in cells[-len(blocks[-1]["header"]):]]

    days = []
    for b in blocks:
        n = len(b["header"])
        idx = (b["index"] + [None] * n)[:n]
        temp = (b["temp"] + [None] * n)[:n]
        wind = (b["wind"] + [None] * n)[:n]
        if b["kind"] == "hourly":
            slots = [(h, i, t, w) for h, i, t, w in zip(b["header"], idx, temp, wind)
                     if h in ("06", "09", "12", "15")]
            if not any(s[1] for s in slots):
                slots = [(h, i, t, w) for h, i, t, w in zip(b["header"], idx, temp, wind) if i]
            letters = [s[1] for s in slots if s[1]]
            temps = [s[2] for s in slots if s[2] is not None]
            winds = [s[3] for s in slots if s[3] is not None]
            dt = re.search(r"(\d{1,2}/\d{1,2})", b["label"])
            days.append({
                "date": dt.group(1) if dt else b["label"],
                "label": b["label"],
                "index": min(letters, key=lambda x: RANK[x]) if letters else None,
                "hours": {h: i for h, i in zip(b["header"], idx) if i},
                "temp_max": max(temps) if temps else None,
                "temp_min": min(temps) if temps else None,
                "wind_max": max(winds) if winds else None,
            })
        else:
            for k, date in enumerate(b["header"]):
                days.append({
                    "date": date,
                    "label": "週間",
                    "index": idx[k],
                    "hours": {},
                    "temp_max": temp[k],
                    "temp_min": temp[k],
                    "wind_max": wind[k],
                })

    # 重複日を除去（時間別の詳細がある今日/明日を優先）
    seen, uniq = set(), []
    for d in days:
        if d["date"] in seen:
            continue
        seen.add(d["date"])
        uniq.append(d)

    return {"code": code, "name": name, "altitude": altitude,
            "municipality": municipality, "days": uniq, "rain": parse_rain(html),
            "fetched": time.strftime("%Y-%m-%dT%H:%M:%S")}


def parse_rain(html):
    """近隣市町村の週間降水確率 {date: %}"""
    out = {}
    idx = html.find("近隣市町村の気象情報")
    if idx < 0:
        return out
    for chunk in re.split(r'<div class="kad_tbl2"', html[idx:])[1:]:
        table = chunk.split("</table>")[0]
        dates, rain = [], []
        for row in trs(table):
            cells = tds(row)
            txt = [clean(c) for c in cells]
            if any(t.startswith("日 付") for t in txt):
                dates = txt[1:]
            elif any("降水確率" in t for t in txt):
                rain = [num(c) for c in cells[-len(dates):]] if dates else []
        if dates and rain:
            for d, r in zip(dates, rain):
                out.setdefault(d, r)
    return out


def mountain_page(code, ba="hr"):
    return parse_mountain(fetch(f"{BASE}kad.html?code={code}&type=15&ba={ba}"), code)


def region_mountains(ba):
    html = fetch(f"{BASE}kasel.html?ba={ba}&type=15")
    out, seen = [], set()
    for code, txt in re.findall(r'<a[^>]+href="kad\.html\?code=(\d+)[^"]*"[^>]*>(.*?)</a>',
                                html, re.S):
        name = clean(txt)
        if name and (name, code) not in seen:
            seen.add((name, code))
            out.append({"name": name, "code": code, "ba": ba,
                        "region": REGIONS.get(ba, ba)})
    return out


if __name__ == "__main__":
    import sys
    for code in sys.argv[1:]:
        m = mountain_page(code)
        print(f"{m['name']}  {m['altitude']}m  {m['municipality']}")
        for s in m["days"]:
            print("   ", s["date"], s["label"][:10], s["index"], s["hours"],
                  s["temp_max"], s["wind_max"], "雨", m["rain"].get(s["date"]))
