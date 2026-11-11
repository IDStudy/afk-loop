<h1 align="center">afk-loop</h1>

<p align="center">
  <b>盯着屏幕找按钮，认出来就点，一直循环。</b><br>
  纯截图 + OpenCV 模板匹配 · 不读内存 · 不发包 · 不改游戏文件
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="#-前提"><img src="https://img.shields.io/badge/Windows-10%20%7C%2011%20x64-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 10/11 x64"></a>
  <a href="https://opencv.org/"><img src="https://img.shields.io/badge/OpenCV-4.8%2B-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV 4.8+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-3DA639?style=for-the-badge&logo=opensourceinitiative&logoColor=white" alt="License MIT"></a>
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
| 权限 | **必须管理员运行**，原因见 [点了没反应](#点了没反应) |
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

切到别的窗口会自动暂停 —— 脚本不抢焦点，随时切得出来。每次点击前还会再确认一遍游戏在前台，不在就不点。

## 🚪 两种开局

同一个玩法有两种进法，本工具都支持 —— 它认的是**画面**，不是入口类型。

| | 怎么进 | 注意 |
|---|---|---|
| **A. 房间** | 大厅创建 / 进入玩法房间 → 房间内点开始 | 该模式的房间**没有私密功能**。别人中途进来又不准备，会把你卡在房间里，得手动踢人或重开 |
| **B. 大世界** | 在大世界直接选这个玩法模式，不建房间，直接开始 | 不会被路人插进来打断；**挂长时间用这条** |

只有**第一步**不同（A 是房间里的开始按钮，B 是大世界里的玩法入口），往下 4 步完全一致。

`samples/` 里的 5 张示例采的是 **A（房间）**。走 B 只要把第 1 张换成大世界入口，第 2–5 张照旧。
如果打完一局回到大世界、入口不在同一屏（要先进一个菜单），按 [加一个界面](#加一个界面) 补一条状态即可。

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

`afk_config.json` 首次运行自动生成，参考 `afk_config.example.json`。

| 键 | 说明 |
|---|---|
| `window.title_keyword` / `exe_keyword` | 怎么认游戏窗口 |
| `match.threshold` | 匹配阈值，默认 0.82 |
| `loop.poll_ms` | 轮询间隔，默认 100ms |
| `loop.dump_after` | 多久认不出界面就存现场图，默认 120 秒（匹配本身可能要等一分钟） |
| `loop.stuck_warn_sec` | 连续多久没推进就打一条警示，默认 300 秒 |
| `loop.hold_grace` | `key_hold` 松手后多久内不重复按，默认 1.5 秒 |
| `loop.click_mode` | `sendinput` / `postmessage` / `both` |
| `loop.max_rounds` | 跑几轮自动停，0 = 不限 |
| `loop.auto_focus` | 是否主动把游戏拉回前台，**默认 false，别开**（会抢焦点，切不出去） |
| `states[]` | 状态表：一张 png + 一个动作，**按顺序匹配，第一个过阈值的胜出** |
| `states[].count_round` | 打勾的这条算完成一轮（挂在奖励结算那条上） |

动作类型：

| 动作 | 作用 |
|---|---|
| `click`（默认） | **点模板中心**（可加 `offset` 微调）—— 框哪点哪 |
| `click_template` | 同 `click`，老写法，留着兼容 |
| `click_anywhere` | 点客户区固定比例位置：配 `points` 依次轮换，配 `point` 只用那一个，都不配就点模板中心 |
| `key_hold` | 按住某键（比赛里按住油门） |
| `key` | 点一下某键 |
| `none` | 只等待 |

### `points`：任意位置未必真「任意」

奖励结算界面中央是奖励卡片，点上去只是把卡片选中，界面不推进 —— 所以那一步默认用
`[[0.5,0.94],[0.5,0.55],[0.5,0.06]]`（底部 → 中间 → 顶部）轮换试，哪个能推进就记住哪个。
日志会写 `点屏幕[第1/3点](x,y)`，一眼看出试到第几个。

三个点都不行，就把 `points` 改成你想点的地方（0~1 比例），或者用 `click` 点模板中心。

### 加一个界面

流程比默认多一步时（比如从大世界开局），不用改代码：

1. 菜单 1 采一张新模板，比如 `6_entry.png`
2. 在 `afk_config.json` 的 `states` 里插一条，**顺序放在它需要压住的那条之前**：

```json
{ "name": "大世界-入口", "template": "6_entry.png", "action": "click", "cooldown": 6.0 }
```

3. 菜单 3 停在那个界面看分数，≥ 0.90 才算能用

## 🔧 出问题了

### 点了没反应

**十有八九是权限。** 游戏以管理员身份运行、脚本不是，Windows 的 UIPI 会拦掉所有输入注入：

- `SendInput` 静默丢弃 —— 表现为光标纹丝不动
- `PostMessage` 直接抛 `(5, '拒绝访问')`

用管理员权限重开即可。验证：菜单 5 跑点击测试，日志写在 `out/clicktest.log`，会明确告诉你哪种投递方式有效。

### 分数只有 0.4 左右

模板框到了动态内容，或者游戏换了分辨率 / UI 版本。重采。

### 点完界面不动

脚本不在点击那一刻下结论（按钮点完可能还留在画面上淡出），而是**点完 3 秒仍停在同一个界面**才算没推进。
连续 3 次都没推进才写一条警示：

```
⚠ 「房间里-开始」连点 3 次都没推进 —— 这个位置点不动
```

按顺序排查：

1. 点到的东西不能点（奖励卡、图片、空白）→ 换个位置框模板，或给这条加 `offset`
2. 光标被游戏锁住（全屏独占锁鼠标）→ 日志出现 `⚠没送进去（光标被锁 / 权限不够）`
3. 权限不够 → 见「点了没反应」

## 📦 打包成 exe

仓库不带二进制，想要自己打：

```
build.bat
```

产物在 `dist\afk-loop\`。*PyInstaller 产物在 360 / Defender 上误报率很高，需要加白名单。*

## 📁 文件

```
nfsm_afk.py              主程序，单文件
afk_config.example.json  配置示例（窗口、阈值、状态表）
requirements.txt         依赖
build.bat                一键打包成 exe，产物 dist\afk-loop\
启动挂机.bat              启动器：有 nfsm_afk.py 就跑源码，只有 exe 就跑 exe
用法.txt                  速查卡：流程 / 热键 / 采集步骤 / 日志说明
samples\                 取景示例图，不能直接当模板用
templates\               你自己的模板放这（仓库里是空的）
out\                     运行日志、失败现场图
```

## 📄 License

MIT，见 [LICENSE](LICENSE)。
