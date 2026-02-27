# ToFlow v0.2 CLI 手册

## 功能概览

ToFlow 是终端里的结构化 Todo 应用。通过 **Track → Project → Todo** 三层结构，让每个任务都有归属，服务于长期目标。

**核心概念**

- **Structure（结构）** — 按 Track（轨道）→ Project（项目）→ Todo（待办）组织任务，支持状态流转、置顶、归档。
- **Box（收集箱）** — 临时存放未整理的 Todo 与 Project。快速收集灵感，稍后移入 Structure。
- **Session（会话）** — 番茄钟式专注记录，关联 Todo，用于回顾与复盘。
- **Archive（归档）** — 已结束项可归档，保持列表简洁又不丢失历史。
- **Timeline（时间线）** — 查看已完成的 Session，追踪时间投入。

**使用方式**

- 运行 `toflow` 或 `toflow view` 打开 TUI 界面。
- 在终端中执行 `toflow track add "Work"` 等命令，通过 CLI 管理任务（适合脚本与自动化）。

数据保存在 `~/.toflow/toflow.db`。

## TUI 界面导航

ToFlow TUI 有五个视图，通过快捷键随时切换：

| 快捷键 | 视图 | 说明 |
|--------|------|------|
| `Tab` | NOW ↔ STRUCTURE | 两个主视图之间切换 |
| `[` | BOX Todos | 收集箱：待办 |
| `]` | BOX Projects | 收集箱：项目 |
| `` ` `` | ARCHIVE | 已归档项 |
| `'` | TIMELINE | Session 历史 |
| `q` | 退出 | 需确认 |

### 界面模式

- **Normal** — 默认模式，所有导航和操作均在此模式下进行。
- **Confirm** — 删除、归档等破坏性操作触发。**再按一次相同键确认，按其他键取消。**
- **Input** — 添加或重命名时触发。输入内容后 `Enter` 提交，`Escape` 取消。

### Structure 视图

Structure 是核心视图，以 **Track → Project → Todo** 三层结构管理任务。

**布局**：Track 显示为带边框的盒子，盒子内是其下属的 Project 列表。进入 Project 后，以平铺列表显示该 Project 下的 Todo。

**导航**

| 按键 | 操作 |
|------|------|
| `↑` `↓` | 移动光标 |
| `→` | 深入下一层（Track → Project → Todo） |
| `←` | 返回上一层 |

**操作**

| 按键 | 操作 | Track | Project | Todo |
|------|------|:-----:|:-------:|:----:|
| `=` / `+` | 添加 | ✓ | ✓ | ✓ |
| `r` | 重命名 | ✓ | ✓ | ✓ |
| `Backspace` | 删除（确认） | ✓ | ✓ | ✓ |
| `a` | 归档（确认） | ✓ | ✓ | ✓ |
| `Space` | 主动作 | sleeping ↔ active | finished ↔ active | stage +1 / done 时 reopen |
| `s` / `z` | 休眠 | sleeping ↔ active | sleeping ↔ active | sleeping ↔ active |
| `c` | 取消 | — | cancelled ↔ active | cancelled ↔ active |
| `p` | 置顶 | — | ✓ | ✓ |
| `Alt+↑` `Alt+↓` | 排序 | ✓ | ✓ | ✓ |
| `m` | 移动（Picker） | — | ✓ | ✓ |
| `Enter` | 进入 NOW | — | — | ✓ |

**Todo 阶段**：带有多阶段的 Todo，`Space` 会推进阶段（current_stage +1）；当 `current == total` 时自动变为 done。done 状态下再按 `Space` 会 reopen（回到 `total-1/total`）。

**Input 模式说明（用户侧）**：在添加/编辑时，`Tab`/`Shift+Tab` 切换字段，`Enter` 提交，`Esc` 取消；日期、阶段、提示字段会按各自规则响应 `Space`、`=`、`-` 与数字输入。

**移动项目**：按 `m` 打开 Picker，选择目标 Track（Project）或 Project（Todo）后 Enter 确认。

### NOW 视图

NOW 是行动视图，由 **Suggestion → Today → Promodoro** 组成。  
NOW 子视图使用 Zen 布局：不显示顶部标题栏，内容居中。

从 Structure / Box 的 Todo 按 `Enter`（确认）可加入 Today；Today 中按 `Enter` 开始一次专注。

**Suggestion（推荐）**

| 按键 | 操作 |
|------|------|
| `↑` `↓` | 移动光标 |
| `Enter` | 加入 Today，并立刻返回 Today |
| `Esc` | 返回 Today（Today 有内容时） |

- 每次加入成功后会重新计算推荐，已在 Today 的 todo 不再出现在列表中。
- 每行会显示推荐理由标签，例如：`PIN`、`DDL 03-01 (+2d)`、`STAGE 2/4`、`MOMENTUM`。

**Today（今日队列）**

| 按键 | 操作 |
|------|------|
| `↑` `↓` | 移动光标 |
| `Alt+↑` `Alt+↓` | 队列排序 |
| `+` / `-` | 调整该项 planned sessions（1–5） |
| `Backspace` | 移除该项（确认） |
| `Enter` | 在 todo 项上开始 Focus（确认）；在 `+ Add...` 上进入 Suggestion |
| `r` | 清空 Today（确认） |

- Today 最多 5 项；满 5 项时隐藏 `+ Add...`。
- 已完成项会显示 `✓` 和实心 session dots，但仍保留在列表中，直到手动移除或清空。

**Promodoro（Focus / Reflect / Rest）**

| 按键 | 操作 |
|------|------|
| `Space` | Focus: 开始/暂停/恢复；Rest: 开始/暂停/恢复 |
| `+` / `-` | Focus 等待/暂停时调工作时长；Reflect 时调 stage delta；Rest 时调休息时长 |
| `Enter` | Focus 运行中提前完成（确认）；Reflect 保存；Rest 跳过 |
| `r` | Focus 重置（确认） |
| `n` | Reflect 打开 note 输入 |
| `Esc` | Reflect note 输入态下关闭 note |
| `t` | 显示/隐藏 Today 面板（不中断计时） |
| `q` | 退出（confirm，Focus 阶段同样生效） |

- Focus 进入后默认是等待态，不自动开始，需按 `Space`。
- Reflect note 是自由输入行，`q/s/a/p` 等按键可正常输入字符，不会触发全局动作。
- Reflect 保存后进入 Rest 准备态，默认不自动开始，需按 `Space`。
- Rest 不显示 next 文案；休息结束或跳过后统一回到 Today，不会自动跳到下一个 Focus。

### Box 视图

Box 是收集箱，存放尚未归入 Structure 的 Todo 和 Project。按 `[` 进入 Box Todos，`]` 进入 Box Projects。

**操作**

| 按键 | 操作 |
|------|------|
| `↑` `↓` | 移动光标 |
| `=` / `+` | 添加 |
| `r` | 重命名 |
| `Backspace` | 删除（确认） |
| `a` | 归档（确认） |
| `Space` | 切换状态 |
| `s` / `z` | 休眠 |
| `c` | 取消 |
| `p` | 置顶 |
| `m` | 移动（Picker） |
| `Alt+↑` `Alt+↓` | 排序 |
| `Escape` | 返回 |

**整理到 Structure**：按 `m` 打开 Picker，选择目标 Project（Todo）或 Track（Project）后 Enter 确认。

### Archive 视图

按 `` ` `` 进入 Archive，浏览所有已归档的 Track、Project、Todo。

| 按键 | 操作 |
|------|------|
| `↑` `↓` | 移动光标 |
| `a` | 取消归档（确认） |
| `Backspace` | 永久删除（确认） |
| `Escape` | 返回 |

归档项按原有层级结构展示，未归档的父级作为上下文显示但不可操作。

### Timeline 视图

按 `'` 进入 Timeline，查看已完成的 Session 历史记录，按日期倒序分组。

| 按键 | 操作 |
|------|------|
| `↑` `↓` | 移动光标（跳过日期标题） |
| `Backspace` | 删除 Session（确认） |
| `Escape` | 返回 |


## CLI 命令概览

```
toflow [command] [options]
toflow view              # open TUI (same as no args)
toflow --no-view         # skip TUI (script-friendly)

# by category
toflow track/project/todo ...     # Structure
toflow box todo/project ...       # Box Todos / Box Projects
toflow session ...       # sessions
toflow archive ...       # archive view
toflow timeline ...      # completed sessions
```

**Track → Project → Todo 层级**

parent_id 语义：project 的 parent 是 track；todo 的 parent 是 project。

```bash
# overview
toflow list

# add
toflow track add <title>
toflow project add <title> [--parent-id ID]
toflow todo add <title> [--parent-id ID] [--total-stages N]

# list（自身） / show（子集）
toflow track list                         # 所有 Tracks
toflow track show <track_id>              # 该 Track 下的 Projects
toflow project list [--parent-id <id>]    # 省略=Box Projects；指定=该 Track 下的 Projects
toflow project show <project_id>          # 该 Project 下的 Todos
toflow todo list [--parent-id <id>]       # 省略=Box Todos；指定=该 Project 下的 Todos

# update
toflow track update <id> [--title TITLE] [--description DESC]
toflow project update <id> [--title TITLE] [--description DESC] [--deadline ISO] [--willingness-hint <0-3>] [--importance-hint <0-3>] [--urgency-hint <0-3>]
toflow todo update <id> [--title TITLE] [--description DESC] [--url URL] [--deadline ISO] [--total-stages N]

# status
toflow track status <id> active|sleeping
toflow project status <id> active|sleeping|cancelled|finished
toflow todo status <id> active|done|sleeping|cancelled

# archive / unarchive / delete
toflow track/project/todo archive <id>
toflow track/project/todo unarchive <id>
toflow track/project/todo delete <id>

# reparent (project: parent = track; todo: parent = project)
toflow project reparent <id> <parent_id>
toflow todo reparent <id> <parent_id>

# pin (project, todo only)
toflow project/todo pin <id>
toflow project/todo unpin <id>

# todo only: done / undo / stage
toflow todo done <id>
toflow todo undo <id>              # set status to active
toflow todo stage <id> set <n>     # set to stage n
toflow todo stage <id> add <x>     # add x
toflow todo stage <id> sub <x>     # subtract x (reduce)
```

**Box（收集箱）**（独立命令，不与 Structure 混用）

```bash
# add
toflow box project add <title>
toflow box todo add <title> [--total-stages N]

# list（自身，Box 无 show）
toflow box list              # Box 概览
toflow box todo list         # Box Todos
toflow box project list      # Box Projects

# update / status / archive / delete
toflow box todo update <id> [--title TITLE] [--description DESC] [--url URL] [--deadline ISO] [--total-stages N]
toflow box project update <id> [--title TITLE] [--description DESC] [--deadline ISO] [--willingness-hint <0-3>] [--importance-hint <0-3>] [--urgency-hint <0-3>]
toflow box todo status <id> active|done|sleeping|cancelled
toflow box project status <id> active|sleeping|cancelled|finished
toflow box todo/project archive <id>
toflow box todo/project unarchive <id>
toflow box todo/project delete <id>

# reparent (project: parent = track; todo: parent = project)
toflow box todo reparent <id> <parent_id>
toflow box project reparent <id> <parent_id>

# pin / stage
toflow box todo/project pin <id>
toflow box todo/project unpin <id>
toflow box todo stage <id> set <n>     # set to stage n
toflow box todo stage <id> add <x>     # add x
toflow box todo stage <id> sub <x>     # subtract x (reduce)
```

**Session（Pomodoro）**

```bash
toflow session add --todo <id> --duration <minutes> --started <ISO_time> [--ended <ISO_time>] [--title ...] [--description ...]
toflow session delete <id>
toflow session update <id> [--description ...]
```

**Archive 与 Timeline**

```bash
toflow archive list
toflow timeline
toflow timeline --limit <n>
```

### 常见用法示例

```bash
# 1. 搭建结构
toflow track add "Work"
toflow list
toflow project add "Q1 计划" --parent-id 1
toflow todo add "写文档" --parent-id 3 --total-stages 3

# 2. 查看结构
toflow list
toflow track list                          # 所有 Tracks
toflow track show 1                         # Track 1 下的 Projects
toflow project list --parent-id 1           # 同上
toflow project show 3                        # Project 3 下的 Todos
toflow todo list --parent-id 3              # 同上

# 3. 任务
toflow todo done 10
toflow todo undo 10              # 撤销完成

# 4. 推进阶段（番茄钟结束）
toflow session add --todo 10 --duration 25 --started "2025-02-14T10:00:00Z" --ended "2025-02-14T10:25:00Z"
toflow todo done 10

# 5. 快速收集
toflow box todo add "买牛奶"
toflow box todo add "写报告" --total-stages 4
toflow box project add "做一个 CLI 工具"

# 6. 整理：Box → Structure
toflow list
toflow box todo reparent 4 3      # todo 4 移到 project 3
toflow box project reparent 5 1   # project 5 移到 track 1

# 7. 置顶 / 归档
toflow project pin 5
toflow todo archive 8

# 8. 回顾
toflow timeline
toflow archive list
```
