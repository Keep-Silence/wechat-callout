# wechat-callout

Wayland（KDE Plasma）下微信窗口**一键呼出**工具。纯 Python + D-Bus 消息机制，
无 X11 / 截图 / 坐标 / wmctrl / xdotool 依赖。

## 原理

Wayland 合成器把**激活已存在窗口**限制为必须携带真实输入产生的
xdg-activation token；纯 D-Bus 无法伪造这样的 token，因此直接调用微信托盘
接口无法把已存在的窗口置顶。本工具改走 **KWin 脚本接口**（合成器信任的通道），
可直接操作窗口，效果等价于用户点击任务栏图标：

1. 在 StatusNotifierWatcher 注册表中定位微信的托盘项（StatusNotifierItem）。
2. 把托盘项注入一段 KWin 脚本并执行（**toggle** 逻辑）：
   - **当前激活窗口是微信** → 关闭它（微信为托盘应用，隐藏回托盘）；
   - **窗口列表中存在微信窗口**（`class/name=wechat`，标题 `微信`）
     → 还原最小化并将它设为活动窗口（`workspace.activeWindow`）；
   - **没有窗口** → 调用托盘项 `SNI Activate`（等效用户左键点击托盘图标，
     签名 `(i,i)`，可被脚本 `callDBus` 直接构造）创建窗口，随后轮询激活。

> 说明：不使用微信 DBusMenu 菜单项的 `Event(i,s,v,u)` 来建窗，因为它要求
> variant 类型参数，而 `callDBus` 无法构造 variant。

## 用法

```bash
python3 /path/to/wechat-callout.py
```

建议在 KDE **系统设置 → 快捷键 → 自定义快捷键**绑定一个全局快捷键，
实现"呼出/隐藏"一键切换：微信未激活时显示并置顶，已在最前时隐藏回托盘。

**退出码**：`0` 成功 · `1` 无会话总线或 KWin 脚本失败 · `2` 未找到微信托盘项（微信未运行）

## 依赖

- Python 3 + pygobject（Gio）
- KDE Plasma 6（Wayland），含 SNI 系统托盘
- KWin 6（脚本接口按**文件路径**加载）
- 微信 Linux 客户端（wechat / wechat-universal）

## 许可

MIT License，见 [LICENSE](LICENSE)。
