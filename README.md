<h1 align="center">afk-loop</h1>

<p align="center">
  <b>盯着屏幕找按钮，认出来就点，一直循环。</b><br>
  纯截图 + OpenCV 模板匹配 · 不读内存 · 不发包 · 不改游戏文件
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square" alt="Python 3.10+"></a>
  <a href="#-前提"><img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?style=flat-square" alt="Windows 10/11"></a>
  <a href="https://opencv.org/"><img src="https://img.shields.io/badge/OpenCV-4.8%2B-5C3EE8?style=flat-square" alt="OpenCV 4.8+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-3DA639?style=flat-square" alt="License MIT"></a>
</p>

---

## 🔍 这是什么

一个自动点鼠标的循环工具。它干的事就一句：**截屏 → 在指定位置找一张小图 → 找到就点它**。

不读游戏内存、不发网络包、不注入 DLL、不改任何游戏文件。它看到的和你眼睛看到的一样。

适合这种流程固定的循环：

```
房间 → 点开始 → 匹配 → 比赛 → 排名结算(确认) → 奖励结算(点屏幕) → 回房间 → 再来一次
```

每一步都是「一个固定画面 + 一个固定按钮」，所以能被模板匹配认出来。
你需要做的只有一件事：**采 5 张图，告诉它每一步长什么样**。换分辨率、换 UI 版本只需重采模板，代码不用动。

> 仓库不含任何游戏资源，模板由使用者自己采。

## 📋 前提

| 项 | 要求 |
|---|---|
| 系统 | Windows 10 / 11 64 位 |
| Python | 3.10+ |
| 权限 | **必须管理员运行**，原因见 [出问题了](#-出问题了) |
| 游戏画面 | **无边框窗口 / 全屏窗口化**。独占全屏抓不到画面 |

## 🚀 快速开始

```bash
pip install -r requirements.txt
python nfsm_afk.py
```

也可以直接双击 `启动挂机.bat` —— 它会选 Python、检查依赖、自动提权。

菜单：

```
  1  采集界面模板  第一次必做
  2  开始挂机
  3  实时分数      查模板有没有失效
  4  可见窗口      找标题 / 进程名
  5  点击测试      点了没反应时用
  0  退出
```

**第一次必须先采 5 张模板**，没模板什么都干不了。
菜单 1 进去：按 <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>S</kbd> 抓图 → 拖框 → 回车确认；
<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>X</kbd> 跳过，<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>E</kbd> 结束。
采完用菜单 3 查分数，**≥ 0.90 才算能用**。

### 🛑 怎么停

| 方式 | 说明 |
|---|---|
| <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>P</kbd> | **暂停 / 继续**，暂停期间不动鼠标键盘 —— 想切出去看控制台先按这个 |
| <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>Q</kbd> / <kbd>F9</kbd> / 鼠标甩左上角 / <kbd>Ctrl</kbd>+<kbd>C</kbd> | 终止，四个都行 |

切到别的窗口会自动暂停 —— 脚本不抢焦点，随时切得出来。

## 🚪 两种开局

同一个玩法有两种进法，本工具都支持 —— 它认的是**画面**，不是入口类型。

| | 怎么进 | 注意 |
|---|---|---|
| **A. 房间** | 大厅创建 / 进入玩法房间 → 房间内点开始 | 该模式的房间**没有私密功能**。别人中途进来又不准备，会把你卡在房间里，得手动踢人或重开 |
| **B. 大世界** | 在大世界直接选这个玩法模式，不建房间，直接开始 | 不会被路人插进来打断；**挂长时间用这条** |

只有**第一步**不同（A 是房间里的开始按钮，B 是大世界里的玩法入口），往下 4 步完全一致。
`samples/` 里的 5 张示例采的是 **A**。走 B 只要把第 1 张换成大世界入口，第 2–5 张照旧。

## 🖼 采模板：只框「永远不变的东西」

**这是 90% 的失败原因。** 框进去会变的内容，就永远匹配不上：

| ❌ 别框 | 为什么 |
|---|---|
| `确认(26秒)` | 倒计时每秒都在变 |
| `4/6`、`91/200` | 任务进度每局不同 |
| `晋级名额 0 / 24` | 名额数字会变 |
| 奖励物品图标 | 每局刷新 |

✅ 只框文字本身 —— `确认` 两个字、`晋级名额` 四个字、底部那行固定提示。

`samples/` 有 5 张示例图，说明该框哪一块，**但不能直接拿来用**（见 [samples/README.md](samples/README.md)）。

## ⚙ 配置

`afk_config.json` 首次运行自动生成，**默认值就能用**，一般不用动。完整字段见 `afk_config.example.json`。

真要调的只有这几个：

| 键 | 说明 |
|---|---|
| `match.threshold` | 匹配阈值，默认 0.82；调高更严，认不出就调回来 |
| `loop.max_rounds` | 跑几轮自动停，0 = 不限 |
| `loop.click_mode` | `sendinput`（默认）/ `postmessage` / `both` |
| `states[]` | 状态表：一张 png + 一个动作，**按顺序匹配，第一个过阈值的胜出** |

动作就三种常用：`click`（点模板中心，默认）、`click_anywhere`（点屏幕固定位置，可配 `points` 轮换试点）、`none`（只等待）。
其余的 `key_hold` / `key`（按键）见示例文件。

## 🔧 出问题了

**点了没反应** —— 十有八九是权限。用管理员身份重开。
还不行就跑菜单 5 点击测试，日志 `out/clicktest.log` 会告诉你哪种点击方式有效。

**分数只有 0.4 左右** —— 模板框到了会变的东西，或者游戏换了分辨率 / UI。重采这一张。

**点了界面不动** —— 日志出现 `⚠ 连点 3 次都没推进` 就是那个位置点不到。
换个位置框模板，或者给这条加 `offset` 偏一点。

## 📦 打包成 exe

仓库不带二进制，自己打：

```
build.bat
```

产物在 `dist\afk-loop\`。*PyInstaller 产物在 360 / Defender 上误报率很高，需要加白名单。*

## 📁 文件

```
nfsm_afk.py              主程序，单文件
afk_config.example.json  配置示例
requirements.txt         依赖
启动挂机.bat              启动器：查 Python / 查依赖 / 自动提权
build.bat                打包成 exe
用法.txt                  速查卡
templates\               你自己的模板（仓库里是空的）
samples\                 取景示例，不能直接当模板用
out\                     运行日志、失败现场图
```

## 📄 License

MIT，见 [LICENSE](LICENSE)。
