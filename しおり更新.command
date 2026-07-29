#!/bin/zsh
# ダブルクリックで しおり を再生成して GitHub に反映する（手動更新用）。
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
cd "/Users/takuya/projects/kinki-popup-shiori"
echo "しおりを更新しています..."
./sync.sh
echo ""
echo "完了しました。1〜2分で公開ページに反映されます。"
echo "  https://takuyafujiwara421.github.io/kinki-popup-shiori/"
echo ""
echo "このウィンドウは閉じて大丈夫です。"
