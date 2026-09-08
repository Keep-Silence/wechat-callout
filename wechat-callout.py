#!/usr/bin/env python3
"""微信呼出脚本（Wayland 原生，纯 D-Bus 消息机制）。

原理：Wayland 下窗口激活必须携带真实输入产生的 xdg-activation token，
纯 D-Bus 无法伪造；但 KWin 脚本接口是合成器信任的通道，可直接把
微信窗口置顶（`workspace.activeWindow`），等于"点了任务栏图标"。

本脚本流程（全部通过 D-Bus 消息完成，无截图、无坐标、无 uinput）：
1. 定位微信的 StatusNotifierItem 托盘项；
2. 把托盘项注入一段 KWin JS，交给 KWin 脚本接口执行（toggle 逻辑）：
   - 当前激活窗口就是微信 → 关闭它（微信为托盘应用，隐藏回托盘）；
   - 窗口列表中存在微信窗口(class/name=wechat) → 还原最小化并置顶；
   - 没有窗口 → 调用 SNI Activate（=用户点击托盘图标左键，签名无 variant
     兼容 callDBus）创建窗口，随后轮询激活。

用法（绑定全局快捷键后即"呼出/隐藏"切换）：
    wechat-callout.py   # 微信未激活→显示，已激活→隐藏
退出码：0=成功  1=无会话总线/脚本失败  2=未找到微信托盘项(微信未运行)
"""
import sys

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

WATCHER_SVC = "org.kde.StatusNotifierWatcher"
WATCHER_PATH = "/StatusNotifierWatcher"
WATCHER_IFACE = "org.kde.StatusNotifierWatcher"
SNI_IFACE = "org.kde.StatusNotifierItem"
K = "org.kde.KWin"
SCRIPT_PATH = "/Scripting"
SCRIPT_IFACE = "org.kde.kwin.Scripting"
SCRIPT_NAME = "wc-callout"
SCRIPT_FILE = "/tmp/wc-callout.js"

# 注入给 KWin JS 的匹配规则：微信窗口的 class/name/caption
WC_MATCH_JS = """
function __isWc(w){
  var cls = new String(w.resourceClass).toLowerCase();
  var nm  = new String(w.resourceName).toLowerCase();
  var cap = new String(w.caption);
  return cls === "wechat" || nm === "wechat" || cap.indexOf("微信") === 0;
}
function __findWc(){
  var list = workspace.windowList();
  for (var i=0;i<list.length;i++){
    var w = list[i];
    if (__isWc(w)) return w;
  }
  return null;
}
function __bring(w){
  if (w.minimized) w.minimized = false;
  workspace.activeWindow = w;
}
"""


def call(conn, dest, path, iface, meth, sig, args, rtype=None):
    return conn.call_sync(dest, path, iface, meth, GLib.Variant(sig, args),
                          GLib.VariantType(rtype) if rtype else None,
                          Gio.DBusCallFlags.NONE, 2000, None)


def get_prop(conn, dest, path, iface, prop):
    reply = call(conn, dest, path, "org.freedesktop.DBus.Properties", "Get",
                 "(ss)", (iface, prop), "(v)")
    return reply.get_child_value(0).unpack()


def find_wechat_item(conn):
    """在 StatusNotifierWatcher 注册表中定位微信托盘项 → (owner, object_path)。"""
    entries = get_prop(conn, WATCHER_SVC, WATCHER_PATH, WATCHER_IFACE,
                       "RegisteredStatusNotifierItems")
    for entry in entries:
        owner, _, path = str(entry).partition("/")
        path = "/" + path
        try:
            sid = get_prop(conn, owner, path, SNI_IFACE, "Id")
            title = get_prop(conn, owner, path, SNI_IFACE, "Title")
        except GLib.Error:
            continue
        if any("wechat" in str(v).lower() for v in (sid, title)):
            return owner, path
    return None


def build_kwin_js(owner):
    """生成 KWin 脚本：窗口存在→置顶；不存在→SNI Activate 建窗后轮询激活。"""
    esc = owner.replace("\\", "\\\\").replace('"', '\\"')
    return f"""{WC_MATCH_JS}
var __owner = "{esc}";

var w = __findWc();
var act = workspace.activeWindow;
if (w && act && __isWc(act)) {{
  // 当前激活窗口就是微信 → 关闭（微信为托盘应用，隐藏回托盘）
  w.closeWindow();
}} else if (w) {{
  // 微信窗口存在但未激活 → 还原最小化并置顶
  __bring(w);
}} else {{
  // 窗口不存在：调用 SNI Activate(= 点击托盘图标左键) 建窗。
  // 用 Activate 而非 DBusMenu Event，因 callDBus 无法构造 variant 参数，
  // 而 Event(i,s,v,u) 必须传 variant；Activate 签名仅为 (i,i)。
  callDBus(__owner, "/StatusNotifierItem", "org.kde.StatusNotifierItem", "Activate", 0, 0);
  var tries = 0;
  var timer = setInterval(function(){{
    tries += 1;
    var w2 = __findWc();
    if (w2) {{ __bring(w2); clearInterval(timer); }}
    else if (tries >= 12) {{ clearInterval(timer); }}
  }}, 200);
}}
"""


def run_kwin_script(conn, js):
    """把 KWin 脚本写入文件并按路径加载执行（KWin 6 只接受路径）。"""
    with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(js)
    # 清理上一次的同名脚本，避免重名冲突(id=-1)
    try:
        call(conn, K, SCRIPT_PATH, SCRIPT_IFACE, "unloadScript", "(s)", (SCRIPT_NAME,), "(b)")
    except GLib.Error:
        pass
    call(conn, K, SCRIPT_PATH, SCRIPT_IFACE, "loadScript",
         "(ss)", (SCRIPT_FILE, SCRIPT_NAME), "(i)")
    call(conn, K, SCRIPT_PATH, SCRIPT_IFACE, "start", "()", ())


def main():
    try:
        conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    except GLib.Error as e:
        print(f"无法连接会话总线: {e}", file=sys.stderr)
        return 1

    found = find_wechat_item(conn)
    if found is None:
        print("未找到微信托盘项（微信未运行？）", file=sys.stderr)
        return 2
    owner, _path = found

    try:
        run_kwin_script(conn, build_kwin_js(owner))
    except GLib.Error as e:
        print(f"KWin 脚本执行失败: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
