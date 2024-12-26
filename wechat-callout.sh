#!/bin/bash

# 判断 /usr/bin/wechat 进程不存在直接结束
ps -ef | grep '/usr/bin/wechat' | grep -v grep > /dev/null
if [ $? -eq 1 ]; then
    exit 0
fi

# 使用 wmctrl 查询名为 'wechat.wechat' 的窗口
wechat_window=$(wmctrl -lx | grep 'wechat.wechat')
script_dir=$(cd "$(dirname "$0")";pwd)
cd $script_dir

# 判断是否找到名为 '微信' 的窗口
if [[ -n "$wechat_window" ]]; then
    # 使用 xdotool 查询名为 '微信' 的窗口
    wechat_window=$(xdotool search --name '微信' | tail -n 1)

    # 获取当前激活窗口的ID
    current_window=$(xdotool getactivewindow)

    # 如果当前窗口是 '微信'，则关闭它
    if [[ "$current_window" == "$wechat_window" ]]; then
        # 获取窗口的位置信息（左上角坐标和窗口尺寸）
        window_geometry=$(xdotool getwindowgeometry "$wechat_window")

        # 提取窗口左上角的 x, y 坐标和窗口的宽度、高度
        window_xy=$(echo "$window_geometry" | grep -oP 'Position: \K[0-9,]+' | head -n 1)
        window_x=$(echo $window_xy | cut -d ',' -f 1)
        window_y=$(echo $window_xy | cut -d ',' -f 2)
        window_width=$(echo "$window_geometry" | grep -oP 'Geometry: \K[0-9]+' | head -n 1)

        # 计算右上角的 x 坐标（左上角的 x 坐标 + 宽度）
        right_top_x=$((window_x + window_width - 24))
        right_top_y=$((window_y + 24))  # 右上角的 y 坐标不变

        # 移动鼠标到右上角并点击（右上角即点击窗口的关闭按钮）
        xdotool mousemove "$right_top_x" "$right_top_y" click 1
        echo "在窗口的右上角点击左键"
    else
        # 如果当前窗口不是 '微信'，则激活 '微信' 窗口
        xdotool windowactivate "$wechat_window"
        echo "激活 '微信' 窗口"
    fi
else
    # 如果没有找到 '微信' 窗口，使用外部命令 'find' 获取坐标
    coord=$(./wechat-callout)  # 替换为实际的 find 命令
    # 分割坐标（假设 find 输出是 'x y' 格式）
    x=$(echo $coord | cut -d ' ' -f 1)
    y=$(echo $coord | cut -d ' ' -f 2)
    if [[ -n "$x" ]]; then
      # 使用 xdotool 移动鼠标并右键点击
      xdotool mousemove $x $y click 1
      echo "在 ($x, $y) 位置点击左键"
    fi
fi
