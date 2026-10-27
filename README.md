<h1 align="center">afk-loop</h1>

<p align="center">
  <b>屏幕截图 + OpenCV 模板匹配的自动点击循环</b><br>
  认出当前在哪个界面 → 点该点的按钮 → 如此循环
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="#-前提"><img src="https://img.shields.io/badge/Windows-10%20%7C%2011%20x64-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 10/11 x64"></a>
  <a href="https://opencv.org/"><img src="https://img.shields.io/badge/OpenCV-4.8%2B-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV 4.8+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-3DA639?style=for-the-badge&logo=opensourceinitiative&logoColor=white" alt="License MIT"></a>
</p>

<p align="center">
  <a href="#-特性"><img src="https://img.shields.io/badge/No-Memory%20Read-FF6B35?style=flat-square" alt="No Memory Read"></a>
  <a href="#-特性"><img src="https://img.shields.io/badge/No-DLL%20Injection-E63946?style=flat-square" alt="No DLL Injection"></a>
  <a href="#-特性"><img src="https://img.shields.io/badge/Single-File-8E44AD?style=flat-square" alt="Single File"></a>
  <a href="#-配置"><img src="https://img.shields.io/badge/Template-Driven-16A085?style=flat-square" alt="Template Driven"></a>
</p>

---

## 🔍 它是什么

一个基于**屏幕截图 + OpenCV 模板匹配**的自动点击循环工具。
没有内存读写、没有发包、不修改游戏文件 —— 它看到的和你眼睛看到的完全一样，只是替你点鼠标。

很多对局类玩法的循环是固定的：

```
房间 → 点开始 → 匹配 → 比赛 → 排名结算(点确认) → 奖励结算(点屏幕) → 回房间 → 再来一次
```

每一步都是一个固定画面 + 一个固定按钮，这种循环适合用模板匹配自动化。
程序做的事很朴素：**截图 → 在截图里找模板 → 找到就点它**。

> 本项目只包含流程逻辑，不含任何游戏资源。模板由使用者自己采集。

## ✨ 特性

| | |
|---|---|
| 👁 **纯视觉** | 只读屏幕像素，不碰内存、不读进程、不发包 |
| 🧩 **单文件** | 全部逻辑在 `nfsm_afk.py` 里，没有隐藏依赖 |
| 📝 **状态表驱动** | 加一个界面 = 加一张图 + 一条配置，不改代码 |
| 🖱 **点击双通道** | `SendInput` 为主，无响应自动补发 `PostMessage` |
| 🛑 **随时能停** | 三个热键 + 鼠标急停 + 切窗口自动暂停 |
| 🐞 **失败留证** | 认不出界面时自动存现场图 + 分数排行 |
| 📦 **零配置启动** | 首次运行自动生成配置，采完模板就能跑 |

## 📋 前提

| 项 | 要求 |
|---|---|
| 系统 | Windows 10 / 11 64 位 |
| Python | 3.10+ |
| 权限 | **必须管理员运行**，原因见 [点了没反应](#点了没反应) |
| 游戏画面 | **无边框窗口 / 全屏窗口化**。独占全屏抓不到画面 |

## 🚀 快速开始

```bash
pip install -r requirements.txt
python nfsm_afk.py
```

菜单：

```
  1  采集界面模板   （第一次必做）
  2  开始挂机
  3  实时匹配分数   （调阈值 / 查模板有没有失效）
  4  列出可见窗口
  5  点击测试       （点了没反应时用这个）
  0  退出
```

**第一次必须采 5 张模板**，没有模板什么都干不了。
采集时按 <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>S</kbd> 抓图、拖框、回车。

## 🖼 采模板：只框「永远不变的东西」

这是 90% 的失败原因。框进去会变的内容，就永远匹配不上：

| ❌ 别框 | 为什么 |
|---|---|
| `确认(26秒)` | 倒计时每秒都在变 |
| `4/6`、`91/200` | 任务进度每局不同 |
| `晋级名额 0 / 24` | 名额数字会变 |
| 奖励物品图标 | 每局刷新 |

✅ 正确做法：只框文字本身 —— `确认` 两个字、`晋级名额` 四个字、底部那行固定提示。

采完跑菜单 3，每个界面分数要 **≥ 0.90**。低于 0.82 就是框错了，重采。

`samples/` 里有 5 张示例图，说明该框哪一块 —— **但不能直接拿来用**，见 [samples/README.md](samples/README.md)。

## 🛑 怎么停

| 方式 | 说明 |
|---|---|
| <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>Q</kbd> | 主热键，游戏里也有效 |
| <kbd>F9</kbd> | 备用 |
| 鼠标甩到屏幕左上角 | 急停 |
| 控制台 <kbd>Ctrl</kbd> + <kbd>C</kbd> | |

切到别的窗口会自动暂停 —— 脚本不会抢焦点，随时切得出来。

## 🔧 两个常见故障

### 点了没反应

**十有八九是权限。** 游戏以管理员身份运行，脚本如果是普通权限，Windows 的 UIPI 会拦掉所有输入注入：

- `SendInput` 静默丢弃 —— 表现为光标不动
- `PostMessage` 直接抛 `(5, '拒绝访问')`

用管理员权限重开即可。验证方法：菜单 5 跑一次点击测试，日志写在 `out/clicktest.log`，会明确告诉你哪一种投递方式有效。

### 分数一直 0.4 左右

模板框到了动态内容，或者游戏换了分辨率 / UI 版本。重新采。

## ⚙️ 配置

`afk_config.json`（首次运行自动生成，参考 `afk_config.example.json`）：

| 键 | 说明 |
|---|---|
| `window.title_keyword` / `exe_keyword` | 怎么认游戏窗口 |
| `match.threshold` | 匹配阈值，默认 0.82 |
| `loop.poll_ms` | 轮询间隔，默认 100ms |
| `loop.dump_after` | 多久认不出界面就存现场图，默认 45 秒 |
| `loop.click_mode` | `sendinput` / `postmessage` / `both` |
| `loop.max_rounds` | 跑几轮自动停，0 = 不限 |
| `states[]` | 状态表：一张 png + 一个动作 |

状态表按顺序匹配，第一个过阈值的胜出。

| 动作 | 作用 |
|---|---|
| `click` | 点模板中心（可加 `offset` 微调） |
| `click_anywhere` | 只借模板判定状态，点客户区固定比例位置（`point`） |
| `key_hold` | 按住某键（比赛里按住油门） |
| `key` | 点一下某键 |
| `none` | 只等待 |

## 📦 打包成 exe

仓库里不带二进制。想要 exe 自己打：

```
build.bat
```

产物在 `dist\afk-loop\`。
*PyInstaller 产物在 360 / Defender 上误报率很高，需要加白名单。*

## 📁 文件

```
nfsm_afk.py              主程序，单文件
afk_config.example.json  配置示例（窗口、阈值、状态表）
requirements.txt         依赖
build.bat                一键打包成 exe，产物 dist\afk-loop\
启动挂机.bat              源码版启动器，自动申请管理员
用法.txt                  速查卡：流程 / 热键 / 采集步骤 / 日志说明
samples\                 取景示例图，不能直接当模板用
templates\               你自己的模板放这（仓库里是空的）
out\                     运行日志、失败现场图
```

## 📄 License

MIT，见 [LICENSE](LICENSE)。
