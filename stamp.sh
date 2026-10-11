#!/bin/sh
# 公開前に index.html の版番号（APP_VER）を現在時刻に更新する
V=$(TZ=Asia/Tokyo date +%Y%m%d%H%M%S)
sed -i "s/const APP_VER = \"[^\"]*\";/const APP_VER = \"$V\";/" "$(dirname "$0")/index.html"
echo "$V"
