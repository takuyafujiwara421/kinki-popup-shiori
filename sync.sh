#!/bin/zsh
# 近畿POPUP.md の変更を検知して しおり を再生成し、GitHub へ push する。
# launchd の WatchPaths から呼ばれる（手動実行も可）。
set -e
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
REPO="/Users/takuya/projects/kinki-popup-shiori"
MD="/Users/takuya/Library/Mobile Documents/iCloud~md~obsidian/Documents/藤原拓矢/近畿POPUP.md"
cd "$REPO"

# md はシェル（zsh）がリダイレクトで開いて python に標準入力で渡す。
# こうすると TCC の対象が zsh だけになり、フルディスクアクセスは /bin/zsh 一つで済む。
/usr/bin/python3 build.py - < "$MD" >> sync.log 2>&1

if [ -n "$(git status --porcelain index.html)" ]; then
  git add index.html
  git commit -m "auto: update shiori $(date '+%Y-%m-%d %H:%M')" >> sync.log 2>&1
  git push origin main >> sync.log 2>&1
  echo "$(date '+%F %T') pushed" >> sync.log
else
  echo "$(date '+%F %T') no change" >> sync.log
fi
