from __future__ import annotations

import ctypes
import json
import logging
import os
import sys
import threading
import time
from ctypes import wintypes
from datetime import datetime

# ★ 必须先声明 DPI 感知，否则高缩放屏下 Win32 坐标和截图坐标对不上
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _init_console() -> None:
    """其他用户计算机上的控制台默认是 GBK，直接 print ⚠ ✔ 会 UnicodeEncodeError 崩掉。"""
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    # PIL 每次 resize 都会打 "Ignore caches that are heterogeneous"，别吓人
    try:
        logging.getLogger("PIL").setLevel(logging.ERROR)
    except Exception:
        pass


_init_console()

import cv2
import numpy as np
import win32con
import win32gui
import win32process
from PIL import ImageGrab

# 打包成 exe 后 __file__ 指向临时解压目录，配置和模板必须跟着 exe 走
if getattr(sys, "frozen", False):
    BASE = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

TPL_DIR = os.path.join(BASE, "templates")
OUT_DIR = os.path.join(BASE, "out")
CFG_PATH = os.path.join(BASE, "afk_config.json")

HOTKEY = "Ctrl+Alt+Q"

# ------------------------------------------------------------------ 默认配置

DEFAULT_STATES = [
    {
        "name": "房间里-开始",
        "template": "1_start.png",
        "note": "房间里的【开始 / 准备】按钮",
        "action": "click",
        "cooldown": 6.0,
        "offset": [0, 0],
    },
    {
        "name": "匹配中",
        "template": "2_matching.png",
        "note": "匹配等待界面（取消匹配按钮或转圈）",
        "action": "none",
        "cooldown": 0.0,
        "offset": [0, 0],
    },
    {
        "name": "比赛中",
        "template": "3_racing.png",
        "note": "比赛中的 HUD（计时器 / 名次 / 小地图任选一块不变的）",
        "action": "none",
        "cooldown": 0.0,
        "offset": [0, 0],
    },
    {
        "name": "排名结算-确认",
        "template": "4_rank_confirm.png",
        "note": "比赛打完自动弹的排名结算界面，框【确认】按钮",
        "action": "click",
        "cooldown": 8.0,
        "offset": [0, 0],
    },
    {
        "name": "奖励结算-任意点",
        "template": "5_reward_click.png",
        "note": "奖励结算界面，框界面上固定不动的一块（标题 / 图标，别框奖励物品）",
        "action": "click_anywhere",
        "cooldown": 12.0,
        "point": [0.5, 0.55],
        "count_round": True,
        "offset": [0, 0],
    },
]

DEFAULT_CFG = {
    "window": {"title_keyword": "NFS-", "exe_keyword": "SpeedGame-Win64-Shipping.exe"},
    "match": {"threshold": 0.82},
    "loop": {"poll_ms": 100, "stuck_warn_sec": 300, "max_rounds": 0,
             "hold_grace": 1.5, "auto_focus": False, "dump_after": 45,
             "click_mode": "sendinput"},
    "states": DEFAULT_STATES,
}

# 通用小工具

def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


class Log:
    """控制台 + 文件，双写。"""

    def __init__(self, path: str = ""):
        self.fh = None
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.fh = open(path, "a", encoding="utf-8")

    def __call__(self, msg: str = "") -> None:
        line = f"[{_now()}] {msg}" if msg else ""
        sys.stdout.write("\r" + " " * 96 + "\r")   # 清掉实时状态行
        print(line, flush=True)
        if self.fh:
            self.fh.write(line + "\n")
            self.fh.flush()

    def close(self) -> None:
        if self.fh:
            self.fh.close()
            self.fh = None


def trim_dir(path: str, keep: int, suffix: str = ".png") -> None:
    """只留最新的 keep 个文件。挂机跑久了 fail 截图能把盘塞满。"""
    try:
        if not os.path.isdir(path):
            return
        files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(suffix)]
        files.sort(key=os.path.getmtime)
        for p in files[:-keep] if len(files) > keep else []:
            try:
                os.remove(p)
            except Exception:
                pass
    except Exception:
        pass


def imread_u(path: str, gray: bool = True):
    """cv2.imread 不支持中文路径，走 fromfile。"""
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    flag = cv2.IMREAD_GRAYSCALE if gray else cv2.IMREAD_COLOR
    return cv2.imdecode(data, flag)


def imwrite_u(path: str, img) -> bool:
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    buf.tofile(path)
    return True


def load_cfg() -> dict:
    if not os.path.isfile(CFG_PATH):
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CFG, f, ensure_ascii=False, indent=2)
        print(f"已生成默认配置：{CFG_PATH}")
    with open(CFG_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    cfg = json.loads(json.dumps(DEFAULT_CFG))
    for k, v in raw.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    return cfg


# 窗口

def proc_exe(hwnd: int) -> str:
    try:
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return ""
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(
            h, 0, buf, ctypes.byref(size)
        )
        ctypes.windll.kernel32.CloseHandle(h)
        return os.path.basename(buf.value)
    except Exception:
        return ""


def enum_windows():
    """返回 [(hwnd, title, exe, client_w, client_h)]，含最小化窗口（尺寸为 0）"""
    out = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title.strip():
            return True
        if win32gui.GetParent(hwnd) != 0:
            return True
        try:
            l, t, r, b = win32gui.GetClientRect(hwnd)
        except Exception:
            return True
        out.append((hwnd, title, proc_exe(hwnd), r - l, b - t))
        return True

    win32gui.EnumWindows(cb, None)
    return out


def find_window(cfg: dict, hwnd_hint: int = 0) -> int:
    if hwnd_hint and win32gui.IsWindow(hwnd_hint):
        return hwnd_hint
    w = cfg.get("window", {})
    tk = (w.get("title_keyword") or "").strip().lower()
    ek = (w.get("exe_keyword") or "").strip().lower()
    if not tk and not ek:
        raise SystemExit("配置 window.title_keyword / exe_keyword 都为空，先跑 win 命令挑窗口。")

    hits = []
    for hwnd, title, exe, cw, ch in enum_windows():
        if tk and tk in title.lower():
            hits.append((hwnd, title, exe, cw, ch))
        elif ek and ek in exe.lower():
            hits.append((hwnd, title, exe, cw, ch))
    if not hits:
        cond = []
        if tk:
            cond.append(f"标题含『{tk}』")
        if ek:
            cond.append(f"进程含『{ek}』")
        raise SystemExit(
            f"没找到窗口（{' 或 '.join(cond)}）。\n"
            "游戏没开就先进游戏；开了还找不到，回菜单选 4 列出可见窗口。"
        )
    hits.sort(key=lambda x: x[3] * x[4], reverse=True)
    hwnd, title, exe, cw, ch = hits[0]
    if cw < 200 or ch < 200:
        raise SystemExit(
            f"窗口『{title[:40]}』被最小化了（客户区 {cw}x{ch}），先把游戏还原再来。"
        )
    return hwnd


def client_box(hwnd: int):
    l, t, r, b = win32gui.GetClientRect(hwnd)
    sl, st = win32gui.ClientToScreen(hwnd, (l, t))
    sr, sb = win32gui.ClientToScreen(hwnd, (r, b))
    return sl, st, sr, sb


def grab(hwnd: int | None = None, box=None):
    if box is None:
        if hwnd:
            box = client_box(hwnd)
        else:
            u = ctypes.windll.user32
            vx, vy = u.GetSystemMetrics(76), u.GetSystemMetrics(77)
            vw, vh = u.GetSystemMetrics(78), u.GetSystemMetrics(79)
            box = (vx, vy, vx + vw, vy + vh)
    img = ImageGrab.grab(bbox=box, all_screens=True)
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def activate(hwnd: int) -> bool:
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.6)
        fg = win32gui.GetForegroundWindow()
        if win32gui.GetAncestor(fg, win32con.GA_ROOT) == win32gui.GetAncestor(
            hwnd, win32con.GA_ROOT
        ):
            return True
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.2)
        fg = win32gui.GetForegroundWindow()
        return win32gui.GetAncestor(fg, win32con.GA_ROOT) == win32gui.GetAncestor(
            hwnd, win32con.GA_ROOT
        )
    except Exception:
        return False


def is_foreground(hwnd: int) -> bool:
    try:
        fg = win32gui.GetForegroundWindow()
        return win32gui.GetAncestor(fg, win32con.GA_ROOT) == win32gui.GetAncestor(
            hwnd, win32con.GA_ROOT
        )
    except Exception:
        return False


# 输入模拟

user32 = ctypes.WinDLL("user32", use_last_error=True)

PUL = ctypes.POINTER(ctypes.c_ulong)


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    pass


INPUT._anonymous_ = ("u",)
INPUT._fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

MOUSE_MOVE = 0x0001
MOUSE_LEFTDOWN = 0x0002
MOUSE_LEFTUP = 0x0004
MOUSE_RIGHTDOWN = 0x0008
MOUSE_RIGHTUP = 0x0010
MOUSE_ABSOLUTE = 0x8000
MOUSE_VIRTUALDESK = 0x4000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

VK_MAP = {
    "w": 0x57, "a": 0x41, "s": 0x53, "d": 0x44, "e": 0x45, "q": 0x51,
    "space": 0x20, "enter": 0x0D, "esc": 0x1B, "tab": 0x09,
    "shift": 0x10, "ctrl": 0x11, "alt": 0x12, "f1": 0x70, "f2": 0x71,
}


def _send(*items) -> int:
    """返回实际注入的事件数。返回 0 = 系统直接拒了（UIPI / 输入被拦）。"""
    n = len(items)
    arr = (INPUT * n)(*items)
    return int(user32.SendInput(n, arr, ctypes.sizeof(INPUT)))


def _mouse(x: int, y: int, flags: int) -> INPUT:
    vx = user32.GetSystemMetrics(76)
    vy = user32.GetSystemMetrics(77)
    vw = user32.GetSystemMetrics(78)
    vh = user32.GetSystemMetrics(79)
    nx = int(round((x - vx) * 65535 / max(vw - 1, 1)))
    ny = int(round((y - vy) * 65535 / max(vh - 1, 1)))
    mi = MOUSEINPUT(nx, ny, 0, flags | MOUSE_ABSOLUTE | MOUSE_VIRTUALDESK, 0, None)
    return INPUT(type=0, u=_INPUTUNION(mi=mi))


def _btn(flags: int) -> INPUT:
    """按下/抬起事件：不带坐标、不带 MOVE 标志。"""
    return INPUT(type=0, u=_INPUTUNION(mi=MOUSEINPUT(0, 0, 0, flags, 0, None)))


def cursor_pos():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def move_to(x: int, y: int) -> bool:
    """把光标弄到目标上。SetCursorPos 优先（不走输入队列，反作弊一般不拦），
    不行再补一次 SendInput 绝对移动。两种都不行说明光标被游戏锁了（ClipCursor）。"""
    try:
        user32.SetCursorPos(int(x), int(y))
    except Exception:
        pass
    time.sleep(0.03)
    cx, cy = cursor_pos()
    if abs(cx - x) <= 3 and abs(cy - y) <= 3:
        return True
    if _send(_mouse(x, y, MOUSE_MOVE)) == 0:
        return False
    time.sleep(0.04)
    cx, cy = cursor_pos()
    return abs(cx - x) <= 3 and abs(cy - y) <= 3


def click_at(x: int, y: int, button: str = "left", hold_ms: int = 90) -> bool:
    """标准序列：MOVE(带绝对坐标) -> DOWN(裸事件) -> UP(裸事件)。"""
    down = MOUSE_LEFTDOWN if button == "left" else MOUSE_RIGHTDOWN
    up = MOUSE_LEFTUP if button == "left" else MOUSE_RIGHTUP
    moved = move_to(x, y)
    time.sleep(0.06)
    _send(_btn(down))
    time.sleep(hold_ms / 1000.0)
    _send(_btn(up))
    return moved


def post_click(hwnd: int, cx: int, cy: int, hold_ms: int = 80) -> bool:
    """备用方案：把鼠标消息直接 PostMessage 给窗口，不带 SendInput 的 injected 标记。
    坐标是【客户区】坐标。返回 False 多半是 UIPI 拒绝（权限不够）。"""
    lp = ((cy & 0xFFFF) << 16) | (cx & 0xFFFF)
    try:
        win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lp)
        time.sleep(0.03)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
        time.sleep(hold_ms / 1000.0)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp)
        return True
    except Exception as e:
        print(f"   ⚠ PostMessage 被拒：{e}")
        return False


def post_click_screen(sx: int, sy: int, hold_ms: int = 80):
    """按屏幕坐标找光标真正命中的那个窗口再投消息。返回 (窗口, 是否成功)。"""
    try:
        h = win32gui.WindowFromPoint((sx, sy))
    except Exception:
        return 0, False
    if not h:
        return 0, False
    cx, cy = win32gui.ScreenToClient(h, (sx, sy))
    return h, post_click(h, cx, cy, hold_ms)


def local_diff(g1, g2, cx: int, cy: int, r: int = 220) -> float:
    """只比目标点周围一块。全屏比会被背景动画（光影/角色待机）污染。"""
    h, w = g1.shape[:2]
    x0, x1 = max(0, cx - r), min(w, cx + r)
    y0, y1 = max(0, cy - r), min(h, cy + r)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return float(cv2.absdiff(g1[y0:y1, x0:x1], g2[y0:y1, x0:x1]).mean())


def key_down(name: str) -> None:
    vk = VK_MAP.get(name.lower())
    if vk is None:
        return
    scan = user32.MapVirtualKeyW(vk, 0)
    _send(INPUT(type=1, u=_INPUTUNION(ki=KEYBDINPUT(vk, scan, KEYEVENTF_SCANCODE, 0, None))))


def key_up(name: str) -> None:
    vk = VK_MAP.get(name.lower())
    if vk is None:
        return
    scan = user32.MapVirtualKeyW(vk, 0)
    _send(
        INPUT(
            type=1,
            u=_INPUTUNION(ki=KEYBDINPUT(vk, scan, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, None)),
        )
    )


def key_tap(name: str) -> None:
    key_down(name)
    time.sleep(0.05)
    key_up(name)


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _ensure_admin() -> None:
    """★ 游戏几乎都是管理员权限启动的。普通权限的进程受 UIPI 限制：
    SendInput 到高权限窗口会被静默丢弃（表现为"光标不动"），
    PostMessage 直接抛 (5, '拒绝访问')。所以必须提权。"""
    if _is_admin():
        return
    print()
    print("⚠ 需要管理员权限")
    print("  游戏是以管理员身份运行的，普通权限下 Windows 的 UIPI 会拦住")
    print("  所有点击注入（光标不动 / PostMessage 拒绝访问都是这个原因）。")
    print("  正在申请提权，弹窗点『是』即可…")
    try:
        if getattr(sys, "frozen", False):
            exe, params = sys.executable, " ".join(f'"{a}"' for a in sys.argv[1:])
        else:
            exe = sys.executable
            params = " ".join([f'"{os.path.abspath(sys.argv[0])}"']
                              + [f'"{a}"' for a in sys.argv[1:]])
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, BASE, 1)
        if int(rc) <= 32:
            print("提权被拒绝（UAC 点了否）。请右键 → 以管理员身份运行。")
            input("回车退出…")
    except Exception as e:
        print(f"提权失败：{e}\n请右键 → 以管理员身份运行。")
        input("回车退出…")
    sys.exit(0)


def hot_pressed() -> bool:
    """Ctrl+Alt+Q 或 F9"""
    st = user32.GetAsyncKeyState
    if bool(st(0x78) & 0x8000):          # F9 备用
        return True
    return bool(st(0x11) & 0x8000) and bool(st(0x12) & 0x8000) and bool(st(0x51) & 0x8000)


def failsafe_triggered() -> bool:
    """鼠标甩到屏幕左上角 4px 内 = 急停"""
    pt = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        return False
    return pt.x <= 4 and pt.y <= 4


_STOP = threading.Event()


def start_watchdog() -> threading.Thread:
    """独立线程盯热键，30ms 一轮 —— 主循环在匹配也不会漏按。"""

    def loop():
        while not _STOP.is_set():
            try:
                if hot_pressed() or failsafe_triggered():
                    _STOP.set()
                    return
            except Exception:
                pass
            time.sleep(0.03)

    t = threading.Thread(target=loop, daemon=True, name="afk-watchdog")
    t.start()
    return t


def _combo(*vks) -> bool:
    st = user32.GetAsyncKeyState
    return all(bool(st(v) & 0x8000) for v in vks)


def _wait_release(*vks) -> None:
    while _combo(*vks):
        time.sleep(0.03)


def wait_capture_hot() -> str:
    """Ctrl+Alt+S 抓图 / Ctrl+Alt+X 跳过 / Ctrl+Alt+E 结束"""
    while True:
        if _combo(0x11, 0x12, 0x53):
            _wait_release(0x11, 0x12, 0x53)
            return "ok"
        if _combo(0x11, 0x12, 0x58):
            _wait_release(0x11, 0x12, 0x58)
            return "skip"
        if _combo(0x11, 0x12, 0x45):
            _wait_release(0x11, 0x12, 0x45)
            return "end"
        if user32.GetAsyncKeyState(0x1B) & 0x8000:
            return "end"
        time.sleep(0.04)


def roi_select(frame):
    """框选，返回原图坐标 (x, y, w, h)；图太大先缩放显示。"""
    h, w = frame.shape[:2]
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    lim_w, lim_h = int(sw * 0.86), int(sh * 0.82)
    sc = min(1.0, lim_w / max(w, 1), lim_h / max(h, 1))
    view = frame if sc >= 0.999 else cv2.resize(
        frame, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA
    )
    win = "afk_capture"
    cv2.namedWindow(win, cv2.WINDOW_AUTOSIZE)
    cv2.moveWindow(win, 0, 0)
    roi = cv2.selectROI(win, view, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow(win)
    cv2.waitKey(1)
    x, y, rw, rh = [int(v) for v in roi]
    if sc < 0.999 and rw > 0 and rh > 0:
        x, y, rw, rh = [int(round(v / sc)) for v in (x, y, rw, rh)]
    return x, y, rw, rh


# 模板与匹配

MATCH_SCALE = 0.5      # 半分辨率匹配：全图 450ms -> 105ms，分数几乎不变
ROI_MARGIN = 260       # 在采集时记录的位置周围 ±260px 内找，快了再快一截


class Tpl:
    """一张模板 + 半分辨率副本 + ROI 搜索范围。"""

    __slots__ = ("st", "full", "small", "roi", "scale")

    def __init__(self, st, full, roi=None):
        self.st = st
        self.full = full
        self.small = cv2.resize(full, None, fx=MATCH_SCALE, fy=MATCH_SCALE,
                                interpolation=cv2.INTER_AREA)
        self.scale = self.small.shape[1] / max(full.shape[1], 1)
        self.roi = roi

    @property
    def name(self):
        return self.st["name"]


def load_states(cfg: dict, cw: int = 0, ch: int = 0):
    """返回 ([Tpl...], [缺失文件名])"""
    states = cfg.get("states", [])
    meta = {}
    mp = os.path.join(TPL_DIR, "meta.json")
    if os.path.isfile(mp):
        try:
            with open(mp, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    loaded, missing = [], []
    for st in states:
        name = st.get("template", "")
        path = os.path.join(TPL_DIR, name)
        tpl = imread_u(path, gray=True) if os.path.isfile(path) else None
        if tpl is None:
            missing.append(name)
            continue
        if float(tpl.std()) < 1.0:
            print(f"⚠ 模板几乎纯色，匹配会不稳：{name}")
        area_ratio = (tpl.shape[0] * tpl.shape[1]) / max(cw * ch, 1) if cw and ch else 0
        if area_ratio > 0.18:
            print(f"⚠ 模板占了屏幕 {area_ratio*100:.0f}%，太大：{name}"
                  f"（重采，只框固定不动的一小块）")

        roi = None
        m = meta.get(name)
        if m and cw and ch and abs(m.get("client_w", 0) - cw) <= 2 \
                and abs(m.get("client_h", 0) - ch) <= 2:
            try:
                x, y, w, h = m["pos"]
                s = MATCH_SCALE
                roi = (
                    max(0, int((x - ROI_MARGIN) * s)),
                    max(0, int((y - ROI_MARGIN) * s)),
                    min(int((x + w + ROI_MARGIN) * s), int(cw * s)),
                    min(int((y + h + ROI_MARGIN) * s), int(ch * s)),
                )
            except Exception:
                roi = None
        loaded.append(Tpl(st, tpl, roi))
    return loaded, missing


def match_score(frame_gray, tpl_gray):
    fh, fw = frame_gray.shape[:2]
    th, tw = tpl_gray.shape[:2]
    if th > fh or tw > fw:
        return -1.0, (0, 0)
    res = cv2.matchTemplate(frame_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
    _, maxv, _, maxl = cv2.minMaxLoc(res)
    if not np.isfinite(maxv):
        return -1.0, (0, 0)
    return float(maxv), maxl


def match_tpl(frame_small, t: Tpl):
    """在（已降采样的）帧里找模板，返回 (score, (x, y))，坐标是降采样坐标系。"""
    th, tw = t.small.shape[:2]
    if t.roi:
        x0, y0, x1, y1 = t.roi
        if x1 - x0 >= tw and y1 - y0 >= th:
            s, loc = match_score(frame_small[y0:y1, x0:x1], t.small)
            if s >= 0:
                return s, (loc[0] + x0, loc[1] + y0)
            return s, (0, 0)
    return match_score(frame_small, t.small)


# 命令：win

def cmd_win(cfg: dict) -> None:
    wins = enum_windows()
    print()
    print("可见窗口（挑一个填进 afk_config.json 的 window 里）")
    print("-" * 78)
    for hwnd, title, exe, cw, ch in wins:
        print(f"hwnd={hwnd:<10} {cw}x{ch:<6} {exe:<24} {title[:40]}")
    print("-" * 78)
    print("游戏没开的话先启动游戏再跑这条。")


# 命令：capture

def cmd_capture(cfg: dict, hwnd_hint: int = 0) -> None:
    os.makedirs(TPL_DIR, exist_ok=True)
    hwnd, box = 0, None
    try:
        hwnd = find_window(cfg, hwnd_hint)
        box = client_box(hwnd)
        print(f"\n目标窗口：{win32gui.GetWindowText(hwnd)[:50]}"
              f"  客户区 {box[2]-box[0]}x{box[3]-box[1]}")
    except SystemExit as e:
        if "最小化" in str(e):
            raise
        print(f"\n{e}")
        print("→ 没锁定窗口，改抓整个屏幕采模板（游戏要在前台）。")

    states = cfg.get("states", [])
    print("\n采集说明：")
    print("  1. 游戏切到对应界面（不用切回本窗口）")
    print("  2. 按 Ctrl+Alt+S 抓图 → 弹出截图上拖框选【按钮本体】→ 回车确认")
    print("  3. Ctrl+Alt+X 跳过当前，Ctrl+Alt+E 结束采集")
    print("  按钮要贴边、带文字/图标；别选会动的区域（计时、速度）")
    print()

    meta_path = os.path.join(TPL_DIR, "meta.json")
    meta = {}
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    for idx, st in enumerate(states, 1):
        name = st.get("template")
        if not name:
            continue
        path = os.path.join(TPL_DIR, name)
        flag = "已有" if os.path.isfile(path) else "缺失"
        print(f"[{idx}/{len(states)}] {name}  ({flag})")
        print(f"    要截的是：{st.get('note','')}")
        print("    等待热键…", end="", flush=True)
        act = wait_capture_hot()
        print()
        if act == "end":
            print("    结束采集")
            break
        if act == "skip":
            print("    跳过")
            continue
        time.sleep(0.3)
        frame = grab(hwnd, box)
        if frame is None or frame.size == 0:
            print("    ⚠ 截图失败（独占全屏抓不到，游戏设置里改成无边框窗口）")
            continue
        x, y, w, h = roi_select(frame)
        if w < 8 or h < 8:
            print("    ⚠ 没框到有效区域，跳过")
            continue
        crop = frame[y:y + h, x:x + w]
        if imwrite_u(path, crop):
            print(f"    ✔ 已保存 {w}x{h} -> {name}")
            meta[name] = {"client_w": frame.shape[1], "client_h": frame.shape[0],
                          "pos": [x, y, w, h]}
        else:
            print("    ⚠ 写文件失败")

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("\n采集结束。跑 probe 看分数，跑 run 开始挂机。")


# 命令：probe

def cmd_probe(cfg: dict, hwnd_hint: int = 0) -> None:
    hwnd = find_window(cfg, hwnd_hint)
    box = client_box(hwnd)
    cw, ch = box[2] - box[0], box[3] - box[1]
    fresh, missing = load_states(cfg, cw, ch)
    if missing:
        print(f"⚠ 缺模板：{', '.join(missing)}")
    th = float(cfg["match"]["threshold"])
    print()
    print(f"实时匹配   客户区 {cw}x{ch}  阈值 {th}  x{MATCH_SCALE}")
    print(f"退出       F9 / 鼠标左上角 / Ctrl+C")
    print("分数 >=0.90 稳，0.82~0.90 勉强，<0.82 模板该重采")
    print()
    _STOP.clear()
    start_watchdog()
    last = None
    try:
        while not _STOP.is_set():
            t0 = time.perf_counter()
            frame = grab(hwnd)
            last = frame
            if frame is None or frame.size == 0:
                print("⚠ 截图失败" + " " * 40, end="\r", flush=True)
                time.sleep(0.5)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, None, fx=MATCH_SCALE, fy=MATCH_SCALE,
                               interpolation=cv2.INTER_AREA)
            parts = []
            best = None
            for t in fresh:
                s, _ = match_tpl(small, t)
                if best is None or s > best[1]:
                    best = (t.name, s)
                parts.append(f"{'★' if s >= th else ' '}{t.name}={s:.3f}")
            ms = (time.perf_counter() - t0) * 1000
            head = f"最高 {best[0]} {best[1]:.3f} | " if best else ""
            print(head + " | ".join(parts) + f"  [{ms:.0f}ms]     ",
                  end="\r", flush=True)
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\n")
        if last is not None and last.size:
            d = os.path.join(OUT_DIR, "probe")
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, datetime.now().strftime("%H%M%S") + ".png")
            imwrite_u(p, last)
            trim_dir(d, 20)
            print(f"退出前的画面已存：{p}")


# 命令：run

def cmd_run(cfg: dict, hwnd_hint: int = 0) -> None:
    hwnd = find_window(cfg, hwnd_hint)
    title = win32gui.GetWindowText(hwnd)[:58]
    box = client_box(hwnd)
    cw, ch = box[2] - box[0], box[3] - box[1]

    fresh, missing = load_states(cfg, cw, ch)
    if not fresh:
        raise SystemExit(
            "一个模板都没有。\n"
            "回菜单选 1 采集界面模板 —— 第一次用必须先采这 5 张。"
        )
    if missing:
        print(f"⚠ 这些模板没有，对应界面会被忽略：{', '.join(missing)}")

    th = float(cfg["match"]["threshold"])
    poll = max(int(cfg["loop"]["poll_ms"]), 60) / 1000.0
    stuck_warn = float(cfg["loop"]["stuck_warn_sec"])
    max_rounds = int(cfg["loop"]["max_rounds"])
    auto_focus = bool(cfg["loop"].get("auto_focus", False))
    dump_after = float(cfg["loop"].get("dump_after", 45.0))

    log_path = os.path.join(OUT_DIR, f"afk_{datetime.now():%Y%m%d_%H%M%S}.log")
    log = Log(log_path)
    trim_dir(OUT_DIR, 30, ".log")          # 日志只留最近 30 次
    trim_dir(os.path.join(OUT_DIR, "fail"), 20)

    print()
    print(f"窗口  {title}   {cw}x{ch}   模板 {len(fresh)}  阈值 {th}")
    print(f"日志  {log_path}")
    print(f"停止  {HOTKEY} / F9 / 鼠标甩左上角 / 本窗口 Ctrl+C     切走游戏 = 自动暂停")
    print()

    _STOP.clear()
    start_watchdog()

    held: set[str] = set()
    last_fire: dict[str, float] = {}
    last_state = None
    last_hit = time.time()
    warned_at = 0.0
    last_dump = 0.0
    rounds = 0
    frames = 0
    t0 = time.time()
    round_t0 = t0
    hold_grace = float(cfg["loop"].get("hold_grace", 1.5))
    last_hold_at = 0.0
    last_hold_keys: set[str] = set()
    scores: dict[str, float] = {}

    def status(text: str) -> None:
        sys.stdout.write("\r" + text[:94].ljust(94))
        sys.stdout.flush()

    def release_all():
        for k in list(held):
            key_up(k)
            held.discard(k)

    def client_point(cx: int, cy: int):
        return win32gui.ClientToScreen(hwnd, (cx, cy))

    click_mode = str(cfg["loop"].get("click_mode", "sendinput")).lower()

    def do_click(cx: int, cy: int, sx: int, sy: int, button: str = "left") -> bool:
        """按配置选投递方式：sendinput / postmessage / both"""
        moved = True
        if click_mode in ("sendinput", "both"):
            moved = click_at(sx, sy, button)
        if click_mode in ("postmessage", "both"):
            post_click(hwnd, cx, cy)
        return moved

    def check_effect(gray_before, cx: int = -1, cy: int = -1) -> bool:
        """点完 0.35 秒再抓一帧，只看目标点周围一块，判断这一下到底有没有落到游戏里。"""
        time.sleep(0.35)
        after = grab(hwnd)
        if after is None or after.size == 0:
            return True
        if after.shape[:2] != gray_before.shape[:2]:
            return True
        g_after = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
        if cx < 0:
            d = float(cv2.absdiff(gray_before, g_after).mean())
        else:
            d = local_diff(gray_before, g_after, cx, cy)
        return d >= 3.0

    def fire(cx: int, cy: int, sx: int, sy: int, button: str = "left") -> str:
        """点一下并确认生效。SendInput 偶尔被吞（刚切窗口时）→ 自动补一发窗口消息。

        返回一行日志后缀，空串表示这次点击没进游戏。
        """
        moved = do_click(cx, cy, sx, sy, button)
        ok = check_effect(gray, cx, cy)
        if not ok and click_mode == "sendinput":
            post_click(hwnd, cx, cy)          # 兜底：直接投窗口消息
            ok = check_effect(gray, cx, cy)
        if not moved:
            return ""
        return "" if ok else "   ⚠没反应"

    try:
        while True:
            if _STOP.is_set():
                log("收到终止信号，停止。")
                break
            if max_rounds > 0 and rounds >= max_rounds:
                log(f"已达到轮数上限 {max_rounds}，停止。")
                break

            if not is_foreground(hwnd):
                if auto_focus and activate(hwnd):
                    pass
                else:
                    status("⏸ 游戏不在前台，已暂停（切回游戏自动继续）")
                    _STOP.wait(0.5)
                    continue

            frame = grab(hwnd)
            if frame is None or frame.size == 0:
                status("⚠ 截图失败（游戏最小化 / 独占全屏）")
                _STOP.wait(1.0)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, None, fx=MATCH_SCALE, fy=MATCH_SCALE,
                               interpolation=cv2.INTER_AREA)
            frames += 1

            hit = None
            for t in fresh:
                s, loc = match_tpl(small, t)
                scores[t.name] = s
                if s >= th:
                    hit = (t, loc, s)
                    break

            now = time.time()
            want_hold: set[str] = set()
            if last_hold_keys and now - last_hold_at < hold_grace:
                want_hold |= last_hold_keys

            if hit:
                t, loc, s = hit
                last_hit = now
                st = t.st
                name = t.name
                new_state = name != last_state
                last_state = name
                did = ""          # 这一帧干了什么，空串 = 只是认出界面
                round_msg = ""

                act = st.get("action", "none")
                if act == "click":
                    cd = float(st.get("cooldown", 3.0))
                    if now - last_fire.get(name, 0.0) >= cd:
                        sc = t.scale
                        th_, tw_ = t.small.shape[:2]
                        cx = int(round((loc[0] + tw_ / 2) / sc)) + int(st.get("offset", [0, 0])[0])
                        cy = int(round((loc[1] + th_ / 2) / sc)) + int(st.get("offset", [0, 0])[1])
                        sx, sy = client_point(cx, cy)
                        did = f"点击({sx},{sy})" + fire(cx, cy, sx, sy, st.get("button", "left"))
                        last_fire[name] = now
                        if st.get("count_round"):
                            rounds += 1
                            round_msg = f"   ✔ 第 {rounds} 轮  {(now - round_t0) / 60:.1f} 分钟"
                            round_t0 = now
                elif act == "click_anywhere":
                    cd = float(st.get("cooldown", 10.0))
                    if now - last_fire.get(name, 0.0) >= cd:
                        px, py = st.get("point", [0.5, 0.55])
                        cx = int(cw * float(px))
                        cy = int(ch * float(py))
                        sx, sy = client_point(cx, cy)
                        did = f"点屏幕({sx},{sy})" + fire(cx, cy, sx, sy, st.get("button", "left"))
                        last_fire[name] = now
                        if st.get("count_round"):
                            rounds += 1
                            round_msg = f"   ✔ 第 {rounds} 轮  {(now - round_t0) / 60:.1f} 分钟"
                            round_t0 = now
                elif act == "key_hold":
                    k = str(st.get("key", "w"))
                    want_hold.add(k)
                    last_hold_at = now
                    last_hold_keys = set(want_hold)
                    if new_state:
                        did = f"按住 {k}"
                elif act == "key":
                    cd = float(st.get("cooldown", 3.0))
                    if now - last_fire.get(name, 0.0) >= cd:
                        key_tap(str(st.get("key", "enter")))
                        last_fire[name] = now
                        did = f"按 {st.get('key', 'enter')}"

                # 一个界面只打一行；重复动作（上一次没生效）单独打短行
                if new_state:
                    log(f"{name} {s:.2f}" + (f"  → {did}" if did else ""))
                elif did:
                    log(f"   ↻ {did}")
                if round_msg:
                    log(round_msg)
            else:
                last_state = "?"      # 加载 / 过场本来就认不出，静默
                if now - last_hit > dump_after and now - last_dump > 60:
                    last_dump = now
                    d = os.path.join(OUT_DIR, "fail")
                    os.makedirs(d, exist_ok=True)
                    p = os.path.join(d, datetime.now().strftime("%H%M%S") + ".png")
                    imwrite_u(p, frame)
                    trim_dir(d, 20)
                    top = "  ".join(f"{k}={v:.2f}"
                                    for k, v in sorted(scores.items(), key=lambda kv: -kv[1])[:3])
                    log(f"⚠ {int(now - last_hit)} 秒认不出界面  {top}  现场图 {p}")
                if now - last_hit > stuck_warn and now - warned_at > 300:
                    warned_at = now
                    log(f"⚠ 已经 {int(now - last_hit) // 60} 分钟没进展，游戏大概是卡住了")

            for k in held - want_hold:
                key_up(k)
                held.discard(k)
            for k in want_hold - held:
                key_down(k)
                held.add(k)

            head = f"[{last_state or '识别中'}]" if hit else "[未识别]"
            status(f"{head} 帧{frames} 轮{rounds} {int(now-t0)}s  "
                   f"| {HOTKEY} 停")

            _STOP.wait(poll)
    except KeyboardInterrupt:
        log("Ctrl+C，停止。")
    finally:
        release_all()
        sys.stdout.write("\r" + " " * 96 + "\r")
        dur = time.time() - t0
        log(f"结束  {dur/60:.1f} 分钟  {rounds} 轮  {frames} 帧")
        log.close()


# 命令：clicktest

def _wait_vk(vk: int, timeout: float = 120.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if user32.GetAsyncKeyState(vk) & 0x8000:
            while user32.GetAsyncKeyState(vk) & 0x8000:
                time.sleep(0.02)
            return True
        time.sleep(0.03)
    return False


def wait_combo(vk: int, timeout: float = 180.0) -> bool:
    """等 Ctrl+Alt+<vk>，Esc 取消。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if _combo(0x11, 0x12, vk):
            _wait_release(0x11, 0x12, vk)
            return True
        if user32.GetAsyncKeyState(0x1B) & 0x8000:
            return False
        time.sleep(0.03)
    return False


def cmd_clicktest(cfg: dict, hwnd_hint: int = 0) -> None:
    """一次跑完三种投递方式，直接告出到底哪条路能把点击送进游戏。结果同时写日志。"""
    hwnd = find_window(cfg, hwnd_hint)
    os.makedirs(OUT_DIR, exist_ok=True)
    log = Log(os.path.join(OUT_DIR, "clicktest.log"))
    try:
        log("")
        log("=" * 54)
        log(f"点击测试    管理员权限 = {'是' if _is_admin() else '否 ← 大概率就是它'}")
        log("=" * 54)
        log("  1. 切到游戏，鼠标停在要点的按钮正中心（先别点）")
        log("  2. 按 Ctrl+Alt+T 记下位置")
        log("  3. 后面全自动")
        log("")
        log("等待 Ctrl+Alt+T …")
        if not wait_combo(0x54):
            log("已取消")
            return

        sx, sy = cursor_pos()
        cx, cy = win32gui.ScreenToClient(hwnd, (sx, sy))
        log(f"目标位置：屏幕 ({sx}, {sy})   游戏客户区 ({cx}, {cy})")
        try:
            ha = win32gui.WindowFromPoint((sx, sy))
            log(f"该点命中的窗口：{ha}  进程 {proc_exe(ha)}")
        except Exception:
            pass

        before = grab(hwnd)
        if before is None or before.size == 0:
            log("⚠ 截图失败（游戏最小化 / 独占全屏）")
            return
        mark = before.copy()
        cv2.drawMarker(mark, (cx, cy), (0, 0, 255), cv2.MARKER_CROSS, 60, 4)
        p1 = os.path.join(OUT_DIR, "clicktest_before.png")
        imwrite_u(p1, mark)
        log(f"标了红叉的图：{p1}")

        #  A 光标能不能动
        moved = move_to(sx, sy)
        ax, ay = cursor_pos()
        sent = _send(_mouse(sx, sy, MOUSE_MOVE))
        log("")
        log(f"[A] 移动光标      目标 ({sx}, {sy})  实际 ({ax}, {ay})   "
            + ("到位 ✔" if moved else "没动 ✘"))
        log(f"    SendInput 返回 {sent}"
            + ("（0 = 系统拒绝注入）" if sent == 0 else ""))

        #  B SendInput 点击
        time.sleep(0.3)
        b1 = grab(hwnd)
        g0 = cv2.cvtColor(b1, cv2.COLOR_BGR2GRAY) if b1 is not None else None
        click_at(sx, sy)
        time.sleep(0.7)
        b2 = grab(hwnd)
        d_b = local_diff(g0, cv2.cvtColor(b2, cv2.COLOR_BGR2GRAY), cx, cy) \
            if g0 is not None and b2 is not None else -1.0
        log(f"[B] SendInput 点击   区域变化 {d_b:6.2f}   "
            + ("有效 ✔" if d_b >= 3 else "没反应 ✘"))

        #  C PostMessage 点击
        time.sleep(0.4)
        c1 = grab(hwnd)
        g0 = cv2.cvtColor(c1, cv2.COLOR_BGR2GRAY) if c1 is not None else None
        th, ok_c = post_click_screen(sx, sy)
        time.sleep(0.7)
        c2 = grab(hwnd)
        d_c = local_diff(g0, cv2.cvtColor(c2, cv2.COLOR_BGR2GRAY), cx, cy) \
            if g0 is not None and c2 is not None else -1.0
        log(f"[C] PostMessage 点击  投给窗口 {th}  "
            + ("发送成功" if ok_c else "被拒绝 ✘")
            + f"   区域变化 {d_c:6.2f}   "
            + ("有效 ✔" if d_c >= 3 else "没反应"))

        if c2 is not None and c2.size:
            imwrite_u(os.path.join(OUT_DIR, "clicktest_after.png"), c2)

        log("")
        if d_b >= 3 or d_c >= 3:
            log("✔ 有点击能被游戏接受")
            log("   B 有效 → 直接跑挂机；只有 C 有效 → 把 afk_config.json 里")
            log("   \"click_mode\": \"sendinput\" 改成 \"postmessage\"")
        elif not _is_admin():
            log("★ 现在不是管理员权限，上面的失败很可能全是 UIPI 拦的：")
            log("  关掉本窗口，右键『以管理员身份运行』再来一次这个测试。")
        else:
            log("✘ 管理员权限下三种都不行，按顺序排查：")
            log("   1. 游戏画面设置改【无边框窗口】/【全屏窗口化】再测")
            log("   2. 关掉 WeGame 浮窗 / 录屏 / 显卡叠加")
            log("   3. 看 clicktest_before.png 上的红十字是不是真在按钮上")
    finally:
        log.close()
        print(f"\n结果已写入：{os.path.join(OUT_DIR, 'clicktest.log')}")


#  菜单


def confirm_start() -> bool:
    """开跑前的警告。回车继续，Ctrl+C 放弃。"""
    print()
    print("=" * 56)
    print(" 【警告】")
    print(" 自己用就行了，请勿大肆宣传。")
    print(" 不然这就是官方随便加个检测的事，到时候大家都只能老老实实手刷。")
    print("=" * 56)
    print(" 确认无误后回车。")
    print()
    try:
        input(" 回车开始 > ")
    except (KeyboardInterrupt, EOFError):
        print("\n已取消。")
        return False
    return True


def menu(cfg: dict) -> None:
    while True:
        print()
        print("=" * 56)
        print(" afk-loop   屏幕模板匹配挂机")
        print("=" * 56)
        print("  1  采集界面模板   （第一次必做）")
        print("  2  开始挂机")
        print("  3  实时匹配分数   （调阈值 / 查模板有没有失效）")
        print("  4  列出可见窗口")
        print("  5  点击测试       （点了没反应时用这个）")
        print("  0  退出")
        print("=" * 56)
        print(f"  终止热键 {HOTKEY} / F9 / 鼠标甩左上角")
        print()
        c = input("选择：").strip().lower()
        try:
            if c == "1":
                cmd_capture(cfg)
            elif c == "2":
                if confirm_start():
                    cmd_run(cfg)
            elif c == "3":
                cmd_probe(cfg)
            elif c == "4":
                cmd_win(cfg)
            elif c == "5":
                cmd_clicktest(cfg)
            elif c in ("0", "q"):
                return
            else:
                print(f"⚠ 没有「{c}」这个编号 —— 这里只有 0/1/2/3/4/5")
        except SystemExit as e:
            print(f"\n{e}")
        except Exception:
            import traceback
            traceback.print_exc()


def main() -> None:
    if "--no-admin" not in sys.argv:
        _ensure_admin()
    cfg = load_cfg()
    args = [a for a in sys.argv[1:] if a != "--no-admin"]
    hwnd_hint = 0
    if "--hwnd" in args:
        i = args.index("--hwnd")
        hwnd_hint = int(args[i + 1])
        del args[i:i + 2]
    cmd = args[0].lower() if args else ""

    try:
        if cmd == "capture":
            cmd_capture(cfg, hwnd_hint)
        elif cmd == "run":
            cmd_run(cfg, hwnd_hint)
        elif cmd == "probe":
            cmd_probe(cfg, hwnd_hint)
        elif cmd == "win":
            cmd_win(cfg)
        elif cmd in ("", "menu"):
            menu(cfg)
        else:
            print(__doc__)
    except SystemExit as e:
        print(f"\n{e}")
    except KeyboardInterrupt:
        print("\n已中断")


if __name__ == "__main__":
    main()
