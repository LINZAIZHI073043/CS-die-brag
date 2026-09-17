# -*- coding: utf-8 -*-
"""
CS2 死后自动狡辩工具
------------------------------------
原理：
  1. 通过 CS2 官方的 Game State Integration (GSI)，游戏会把你的
     血量/存活状态实时 POST 到本地 HTTP 端口（不读内存，不碰反作弊）。
  2. 检测到"我"从活着变成血量 0（即刚死）时，自动把一句借口写进剪贴板，
     然后模拟按键：打开聊天框 -> Ctrl+V 粘贴 -> 回车发送。

中文之所以用"复制+粘贴"而不是逐字模拟按键，是因为游戏里模拟中文输入几乎
不可能，走剪贴板粘贴最稳。
"""

import json
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pydirectinput
import pyperclip

# ============ 可配置项 ============

# 监听端口，必须和 .cfg 里的 uri 端口一致
PORT = 3000

# 打开聊天框的按键：'y' = 全局聊天(all chat)，'u' = 队伍聊天(team)
CHAT_KEY = "y"

# 两次狡辩之间的最短间隔（秒），防止一次死亡触发多条
COOLDOWN = 3.0

# 借口从同目录的 excuses.txt 读取（一行一句，# 开头是注释）。
# 增删借口：用记事本改 excuses.txt，或双击"编辑借口.bat"用图形界面改；改完立即生效。
EXCUSES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "excuses.txt")

# excuses.txt 读不到 / 为空时用的内置后备借口
DEFAULT_EXCUSES = [
    # —— 状态/手感类 ——
    "手还没热，再给我两把",
    "刚打完瓦不适应，枪都是飘的",
    "复健中复健中，别催",
    "换了个新鼠标，DPI 还没调过来",
    "刚起床手是僵的，别急",
    "今天状态没了，热身赛都不算",
    "键盘手感不对，回头得换",
    "这灵敏度是队友帮我调的，不是我的锅",
    "刚吃完饭有点困，下把清醒",
    "手心出汗了，鼠标打滑",

    # —— 甩锅队友/环境类 ——
    "队友不补枪能怪我？",
    "队友不给烟，光让我上",
    "让一下让一下，这枪打不动",
    "你们不报点我怎么知道人在哪",
    "全靠我一个人扛，累了",
    "刚接了个电话没看屏幕",
    "外卖到了我去开个门",
    "室友喊我一句，分神了",

    # —— 甩锅硬件/网络类 ——
    "刚才卡了一下，网络问题",
    "鼠标突然飘了，硬件问题",
    "延迟 200 你让我怎么打",
    "耳机没声音，听不到脚步",
    "屏幕帧数掉了，画面一顿",
    "网卡了半秒，人瞬移过来的",
    "显示器刷新率没开满，跟不上",

    # —— 阴阳/战术类 ——
    "我这把演员，别催",
    "我是去卡视野的，战术性牺牲",
    "我这是为了拿情报，值了",
    "我在给你们当诱饵，懂？",
    "送一个换你们两个，血赚",
    "对面开挂了兄弟，这枪线不正常",
    "下一把下一把，热身还没结束",
    "这地图设计有问题，全是死角",
    "我这是故意的，你细品",
    "赢了是我们的，输了是节奏问题",
]


def load_excuses():
    """从 excuses.txt 读取借口（去掉空行与 # 注释）；读不到就用内置后备。"""
    try:
        with open(EXCUSES_FILE, encoding="utf-8") as f:
            items = [line.strip() for line in f]
        items = [line for line in items if line and not line.startswith("#")]
        if items:
            return items
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[警告] 读取 excuses.txt 失败，改用内置借口：{e}")
    return DEFAULT_EXCUSES


# 各步骤之间的等待（秒）。想更快就调小；但太小可能"来不及"导致发不出去/打进游戏里
DELAY_OPEN_CHAT = 0.10   # 按下聊天键后等聊天框弹出（若发不出去/内容打进游戏，把它调大）
DELAY_AFTER_PASTE = 0.05 # 粘贴后等文字出现再回车

# pydirectinput 每次按键后的内置停顿，默认 0.1 秒（一条消息 5 步就白等 0.5 秒！），压到很小
pydirectinput.PAUSE = 0.01
# ==================================


class DeathWatcher:
    """维护存活状态，判断死亡的瞬间。"""

    def __init__(self):
        self.lock = threading.Lock()
        self.was_alive = False       # 上一帧"我"是否活着
        self.armed = True            # 是否允许触发（死后置 False，复活后重置）
        self.last_brag = 0.0         # 上次狡辩时间

    def update(self, payload: dict):
        provider = payload.get("provider") or {}
        player = payload.get("player") or {}

        my_steamid = provider.get("steamid")
        cur_steamid = player.get("steamid")
        state = player.get("state") or {}
        health = state.get("health")

        # 只在"当前观察的玩家就是我自己"时更新血量。
        # 死后 GSI 会开始报告被观战对象的数据，这时 steamid 不等于我，直接跳过，
        # 避免把别人的血量误当成自己的。
        if not my_steamid or cur_steamid != my_steamid or health is None:
            return

        with self.lock:
            if health > 0:
                self.was_alive = True
                self.armed = True          # 活着就重新上膛
            elif health == 0 and self.was_alive and self.armed:
                # 从活着 -> 血量 0：刚死
                self.was_alive = False
                now = time.time()
                if now - self.last_brag >= COOLDOWN:
                    self.armed = False
                    self.last_brag = now
                    threading.Thread(target=self._brag, daemon=True).start()

    def _brag(self):
        excuse = random.choice(load_excuses())
        print(f"[死亡] 开始狡辩: {excuse}")
        try:
            pyperclip.copy(excuse)
            time.sleep(0.02)
            pydirectinput.press(CHAT_KEY)
            time.sleep(DELAY_OPEN_CHAT)
            pydirectinput.keyDown("ctrl")
            pydirectinput.press("v")
            pydirectinput.keyUp("ctrl")
            time.sleep(DELAY_AFTER_PASTE)
            pydirectinput.press("enter")
        except Exception as e:
            print(f"[错误] 发送失败: {e}")


watcher = DeathWatcher()


class GSIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        self.send_response(200)
        self.end_headers()
        try:
            payload = json.loads(raw.decode("utf-8"))
            watcher.update(payload)
        except Exception as e:
            print(f"[警告] 解析失败: {e}")

    # 关掉默认的访问日志刷屏
    def log_message(self, fmt, *args):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), GSIHandler)
    print("=" * 42)
    print(" CS2 死后自动狡辩 已启动")
    print(f" 监听 http://127.0.0.1:{PORT}")
    print(f" 聊天键: {CHAT_KEY}  ('y'=全局, 'u'=队伍)")
    print(f" 已加载借口: {len(load_excuses())} 条（来自 excuses.txt）")
    print(" 进游戏就会自动生效，Ctrl+C 退出")
    print("=" * 42)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出。")
        server.shutdown()


if __name__ == "__main__":
    main()
