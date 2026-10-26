# 山の天気まとめ（tenkura-list）— 開発引き継ぎ資料

このファイルは Hermes / Claude Code などのエージェントが、このディレクトリで作業を始めたときに自動で読む前提の資料です。
**新しいセッションで続きをやるときは、まずこれを読む。**

---

## これは何か

「てんきとくらす」の登山指数を **8山 × 8日分** 一覧表示する PWA（スマホにインストールできるWebアプリ）。
GitHub Actions が1日5回データを取得し、GitHub Pages が配信する。**このPCの電源は不要**。

| | |
|---|---|
| 本番URL | https://hekominet-del.github.io/tenkura-list/ |
| リポジトリ | https://github.com/hekominet-del/tenkura-list （public） |
| ローカル | `C:\Users\info\projects\tenkura-list-cloud` |
| 旧ローカル版 | `C:\Users\info\projects\tenkura-list`（PC内サーバー版・port 8765。もう不要だが実装の参考になる） |

## 構成

```
web/                     画面のソース（編集するのはここ）
  index.html             本体（CSS/JS込み・1ファイル）
  manifest.webmanifest   PWA定義（アイコン192/512 PNG必須）
  sw.js                  Service Worker（data.jsonはネットワーク優先）
  icon-192.png / icon-512.png / apple-touch-icon.png
build.py                 watchlist.json の山を取得 → public/data.json、web/ を public/ へコピー
tenkura.py               てんきとくらすの取得・解析（標準ライブラリのみ・pip不要）
watchlist.json           表示する山のリスト（名前 / code / ba / region）
public/                  ビルド成果物＝Pagesが配信するディレクトリ
.github/workflows/build.yml  定期実行＆デプロイ
```

### 定期実行

`cron: '20 16,19,22,4,10 * * *'`（**UTC**）＝ JST **1:20 / 4:20 / 7:20 / 13:20 / 19:20**
てんきとくらすの更新時刻（1・4・7・13・19時ごろ）に +20分ずらしてある。
手動実行: `gh workflow run build.yml --repo hekominet-del/tenkura-list`

## 開発の回し方

```bash
export PATH="$PATH:/c/Users/info/tools/gh"   # gh はポータブル版
cd "C:/Users/info/projects/tenkura-list-cloud"

# 1. web/ や build.py を編集したらローカル確認
python build.py
cd public && python -m http.server 8790     # → http://127.0.0.1:8790/

# 2. コミット（★下の注意参照）
git add -A
git commit -m "変更内容"

# 3. push（Actionsが自動でビルド＆デプロイ、約40秒）
git push origin main

# 4. 確認
gh run list --repo hekominet-del/tenkura-list --limit 3
curl -s https://hekominet-del.github.io/tenkura-list/data.json | head -c 100
```

### ★ push 前の必須手順（生成物の競合回避）

Actions が `public/data.json` をコミットし返すため、そのまま push すると必ず競合する。
**生成物は手でマージしない**。次のどちらかで解決する。

```bash
git fetch origin && git reset --soft origin/main && git commit -m "変更内容" && git push
```

## データ仕様（public/data.json）

```json
{"at": "2026-10-26T17:35:43+09:00",
 "mountains": [
   {"code": "16150013", "name": "立山", "altitude": 3015, "municipality": "立山町",
    "ba": "hr", "region": "北陸", "jma": "1632300",
    "fetched": "2026-10-26T17:35:41", "stale": false,
    "days": [{"date": "10/26", "label": "今 日 10/26(月)", "index": "A",
              "hours": {"18": "A", "21": "A"},
              "temp_max": 6, "temp_min": 5, "wind_max": 3}],
    "rain": {"10/28(水)": 30}}
 ]}
```

## 設計上の決め事（変えるときは理由を残す）

- **表示する山は固定リスト**（`watchlist.json`）。UIからの追加は廃止した。増やすときはこのファイルに1行足す
- **`code` と `ba` は山ページのURLから取る**
  `https://tenkura.n-kishou.co.jp/tk/kanko/kad.html?code=16150013&type=15&ba=hr`
  `ba`: hk北海道 / th東北 / hr北陸 / kk関東・甲信 / tk東海 / kn近畿 / cg中国 / sk四国 / ks九州・沖縄
- **時刻は必ずJSTオフセット付き**（`+09:00`）。ActionsはUTCなので naive な文字列にするとブラウザ側で9時間ずれる
- **`jma` は気象庁の市町村予報エリアコード**（class20s）。`watchlist.json` に手で持たせ、`build.py` が data.json へ素通しする。詳細画面の「麓: ○○町 気象庁 ↗」はこれで `https://www.jma.go.jp/bosai/forecast/#area_type=class20s&area_code=<jma>` を開く。山の麓名（municipality）から引くときは `https://www.jma.go.jp/bosai/common/const/area.json` の `class20s` を名前一致で検索
- **取得失敗時は前回データを引き継ぐ**（`stale: true`）。全山失敗なら data.json を更新せず exit 1
- **アセットはすべて相対パス**。Pagesはサブパス（`/tenkura-list/`）配信なので `/icon.png` は404になる（凡例アイコンを `/img/mnt1.gif` と書いて404にした実例あり。表内は `img/mnt1.gif` で正しかった）
- **`web/index.html` を変えたら `web/sw.js` の `CACHE` を上げる**（`tenkura-v2` → `v3`）。SWはアプリ本体をキャッシュ優先で返すので、上げないとスマホのインストール済みPWAは古い画面のまま
- **取得は1日5回まで**。非公式取得なので、増やす場合はサイト負荷とブロックリスクを天秤にかける

## ハマりどころ（実際に踏んだ）

- `winget install GitHub.cli` は**ハングする**。GitHub Releases の zip を展開して `C:\Users\info\tools\gh\gh.exe` を使う
- **`GITHUB_TOKEN` のpushはワークフローを再トリガーしない** → 生成物をコミットし返しても無限ループにならない。むしろこのコミットが「60日間活動なしでスケジュール停止」を防いでいる
- ChromeのPWAインストールには **PNG 192/512 のアイコン**が要る。SVGだけだと「インストール」が出ずショートカット止まりになる
- ローカルサーバー版（`tenkura-list`）は `http://LAN-IP:8765` なので**家の外からは見られない**。HTTPSでないとPWAインストールも不可

## 次にやると良いこと（候補）

1. 山の並び替え・お気に入り固定（localStorageで完結）
2. 詳細画面に tenki.jp / 山と高原地図 など外部リンク追加（雨雲レーダー・windy・気象庁は追加済み）
3. 危険な山（指数C）だけTelegramに通知（Hermesのcronjobから data.json を読む）
4. 週末だけ表示・「行く予定の山」モード
5. watchlist編集をGitHub API経由でUIから（トークンが必要になるので慎重に）

## 履歴

- 2026-10-26: ローカル版（PC内サーバー）から GitHub Pages + Actions + PWA へ移行して公開。8山・1日5回更新で稼働中
- 2026-10-26: ①凡例アイコンの404修正（絶対パス→相対パス）②雨雲レーダーを大きなボタンに ③windy（風・積雪）リンクを隣に追加 ④詳細画面の麓の横に気象庁リンク（jma コード導入）
