# 近畿POPUP 旅のしおり（自動生成）

Obsidian の `近畿POPUP.md` を元データに、旅のしおり（`index.html`）を自動生成し
GitHub Pages で公開する仕組み。

## 流れ
1. `近畿POPUP.md` を編集・保存する
2. Mac 常駐の launchd が変更を検知して `sync.sh` を実行
3. `build.py` が md をパースして `index.html` を再生成
4. 変更があれば自動で commit → push
5. GitHub Pages の公開URLが最新になる

## 手動で再生成したいとき
```
cd ~/projects/kinki-popup-shiori
./sync.sh
```

## 元データ（md）の書き方メモ
- 日付は `7/30` のように行頭に単独で書く
- 各項目は `・移動` `・POPUP` `・昼食` のように `・` で始める
- 移動は `【路線名】` の下に時刻と駅を書く
  - `5:46　加賀温泉駅発` 形式、または `15:40 - 15:50` の次行に `大津駅から草津駅` 形式
- `POPUP` は `11-14時　滋賀（大津駅）` 形式
- 店・宿は 店名 と Googleマップ等のURLを書けば地図ボタンになる
