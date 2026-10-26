# -*- coding: utf-8 -*-
"""watchlist.json の山を取得して public/data.json を作る（GitHub Actions 用・サーバー不要）

- 失敗した山は前回の data.json から引き継ぐ（サイト側の一時的な不調で欠けないように）
- 全山失敗したら何も書かずに exit 1（前回のデータを保持）
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import tenkura as T  # noqa: E402

PUB = os.path.join(ROOT, "public")
WEB = os.path.join(ROOT, "web")
DATA = os.path.join(PUB, "data.json")
WATCH = os.path.join(ROOT, "watchlist.json")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def copy_site():
    """web/ を public/ にコピー（data.json は消さない）"""
    import shutil
    os.makedirs(PUB, exist_ok=True)
    for name in os.listdir(WEB):
        src = os.path.join(WEB, name)
        dst = os.path.join(PUB, name)
        if os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def main():
    watch = load_json(WATCH, [])
    if not watch:
        print("watchlist.json が空です", file=sys.stderr)
        return 1

    prev = {m["code"]: m for m in load_json(DATA, {}).get("mountains", [])}

    out, fails = [], 0
    for m in watch:
        code, ba = m["code"], m.get("ba", "hr")
        got = None
        for attempt in range(3):
            try:
                got = T.mountain_page(code, ba)
                break
            except Exception as e:
                print(f"retry {attempt+1} {m['name']}: {type(e).__name__} {e}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        if got:
            got["code"] = code
            got["name"] = m.get("name") or got.get("name") or code
            got["ba"] = ba
            got["region"] = m.get("region", "")
            got["jma"] = m.get("jma", "")  # 麓の市町村（気象庁 class20s のエリアコード）
            out.append(got)
            print(f"OK   {got['name']} {got.get('altitude')}m")
        else:
            fails += 1
            if code in prev:
                old = dict(prev[code])
                old["stale"] = True
                old["jma"] = m.get("jma", old.get("jma", ""))
                out.append(old)
                print(f"STALE {m['name']} （前回データを使用）")
            else:
                out.append({"code": code, "name": m.get("name", code), "ba": ba,
                            "region": m.get("region", ""), "jma": m.get("jma", ""),
                            "error": "fetch failed", "days": []})
                print(f"FAIL {m['name']}")

        time.sleep(1.0)  # サイトへの配慮

    if fails == len(watch):
        print("全山失敗のため data.json は更新しません", file=sys.stderr)
        return 1

    payload = {"at": datetime.now(JST).isoformat(timespec="seconds"), "mountains": out}
    copy_site()
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {DATA} ({len(out)} mountains, {fails} failed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
