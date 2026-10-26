# 山の天気まとめ（クラウド版）

てんきとくらすの登山指数を毎日自動取得して、静的サイトとして配信する構成です。
**PCの電源は不要**。GitHub Actions が定期的にデータを取り、GitHub Pages が配信します。

## 仕組み

```
GitHub Actions (1日5回)
   └─ build.py: watchlist.json の山を取得 → public/data.json
        └─ 変更があればコミット
             └─ GitHub Pages が public/ を配信（HTTPS）
```

取得タイミングは、てんきとくらす公式の更新時刻（JST 1・4・7・13・19 時ごろ）に
+20分ずらして合わせています（UTC cron: `20 16,19,22,4,10 * * *`）。

## ファイル

| パス | 役割 |
|---|---|
| `watchlist.json` | 表示したい山のリスト（**ここを編集すると山を増減できます**） |
| `build.py` | 取得して `public/data.json` を作る |
| `tenkura.py` | てんきとくらすの取得・解析ライブラリ |
| `web/` | 画面（HTML/CSS/JS、PWA対応） |
| `public/` | 生成物（Pagesが配信するディレクトリ） |
| `.github/workflows/build.yml` | 定期実行とデプロイ |

## 山を追加・削除する

`watchlist.json` を編集して保存（GitHubの画面から直接編集できます）。

```json
{"name": "槍ヶ岳", "code": "20150022", "ba": "kk", "region": "関東・甲信"}
```

`code` と `ba` は てんきとくらす の山ページURLから取れます。

```
https://tenkura.n-kishou.co.jp/tk/kanko/kad.html?code=20150022&type=15&ba=kk
                                                        ^^^^^^^^         ^^
```

`ba` は地域コード: `hk`北海道 / `th`東北 / `hr`北陸 / `kk`関東・甲信 /
`tk`東海 / `kn`近畿 / `cg`中国 / `sk`四国 / `ks`九州・沖縄

## 初回セットアップ

1. このリポジトリを GitHub に push（public）
2. **Settings → Pages → Source を「GitHub Actions」** に変更
3. **Actions タブ → build-and-deploy → Run workflow** で初回実行
4. 数十秒で `https://<ユーザー名>.github.io/tenkura-list/` が公開される
5. スマホのChromeで開く → ⋮ → **「アプリをインストール」**（HTTPSなので本物のPWAになります）

## ローカルで試す

```
python build.py
cd public && python -m http.server 8790
# → http://127.0.0.1:8790/
```

## 注意

- てんきとくらすの非公式取得です。1日5回・山ごとに1リクエスト、間に1秒の待機を入れて負荷を抑えています
- 取得に失敗した山は**前回のデータを引き継ぎ**、サイトが欠けないようにしています
- 全山失敗した場合は `data.json` を更新せず、前回の内容を保持します
- 登山指数は目安です。実際の判断は必ず公式情報と現地の状況で
