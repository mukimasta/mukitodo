# Changelog

本文件记录 ToFlow 项目的所有重要变更。

## [v0.2.0] - 2026-02 架构重构

**重大变更**：v0.2 为一次全面架构重构，采用分层设计、协议化实体、View/Pane 抽象。

### CLI 层

- Typer 子命令：`track` | `project` | `todo` | `box` | `session` | `archive` | `timeline`
- 模块化：`cli/main.py` 入口，各子命令独立模块
- 无子命令时启动 TUI，`--no-view` 可跳过
- `toflow migrate`：v1 → v2 schema 迁移

### Ops 层

- 新建 `ops/` 目录，中粒度业务操作
- `Result(success, data, message)` 统一返回
- 模块：crud、query、status、archive、pin、move、session、today、now_query
- 所有 ops 接收 `session` 参数，由调用方提供事务边界

### Registry 与协议

- `EntityType` Enum：TRACK、PROJECT、TODO、SESSION
- `supports_protocol(entity_type, name)`：基于 hasattr 的 duck typing
- 协议：Archivable、Orderable、Statusable、Parentable、Pinnable

### 数据层

- `parent_id` 统一：Project、TodoItem 均用 parent_id（替代 track_id/project_id）
- 数据库路径：`~/.toflow/toflow.db`
- NowTodayItem：planned_sessions 约束 1–9（迁移后）

### TUI 层

- **View/Pane 抽象**：View 持 Pane，EntityView 提供默认 CRUD
- **AppState**：structure_stack、primary（STRUCTURE/NOW）、secondary、modal、UIMode
- **Input 子系统**：FormService、InputForm、InputSession，与 View 解耦
- **NOW 子域**：NowState 聚合 today/suggestion/promodoro，独立模块
- **PickerView**：`m` 键移动，选择目标 Track/Project
- 取消 INFO 视图；Box 改为 `[`/`]` 切换 Todos/Projects

### 项目结构

```
toflow/
├── cli/          # 子命令模块
├── ops/          # 业务操作
├── tui/
│   ├── view/     # View 实现
│   ├── pane/     # Pane 实现
│   ├── input/    # 表单子系统
│   └── now/      # NOW 子域
├── models.py, database.py, registry.py
└── migrate.py
```

---

## [v0.1.1] - 2026-01-29 Structure Move

**新功能**：Structure 视图内移动 Project/Todo（按 `m`）
- Project 可移至其他 Track
- Todo 可移至其他 Project
- 交互与 Box move 一致：m → 导航 → Enter 确认

---

## [v0.1.0] - 2026-01-15

修复 bug，优化体验，发布 GitHub，更名为 ToFlow。

---

## [v0.0.9] - 2026-01-04

1. **时间显示**：Timeline 按本地日期分组；Session 显示本地时间；数据存 UTC
2. **排序**：Alt+Up/Down 调整 order_index（structure + box）
3. **取消 Takeaway**：Session 结束时记录 description
4. **调整**：新增 pinned 字段，移除 project focusing 状态

---

## [v0.0.8] - 2026-01-02 NOW 完成提醒与休息

- 剩余 5 分钟响铃
- 计时结束：响铃、激活 iTerm2、进入 Finish Session 流程
- 保存后进入 5 分钟 Rest 模式（Space 开始）
- 休息结束响铃

---

## [v0.0.7] - 2026-01-02 TODO 阶段

- 新增 `total_stages`、`current_stage`
- Space：active 时 stage+1，达 total 自动 done；done 时 reopen
- Input：T/S chip 调整阶段

---

## [v0.0.6] - 2026-01-01

优化快捷键、视图切换、Input 显示；修复添加后焦点丢失。

---

## [v0.0.5 (a)] - 2026-01-01 TUI Renderer 重构

- 隐式滚动替代滚动条
- `tui/renderer/` 目录，Renderer 与 LayoutManager 分离

---

## [v0.0.4 (e)] - 2025-12-31 Box Inbox

- 新增 BOX 视图（`b` 进入），Box Todos / Box Ideas（`[`/`]`）
- Box Todo Move、Box Idea Promote
- Archive 支持 Box Todos

---

## [v0.0.4 (d)] - 2025-12-31 TUI Refactor

- LayoutManager、Renderer 回调、单向数据流

---

## [v0.0.4 (c)] - 2025-12-30 Input Mode 重构

- InputState、Tab 切换字段、多类型多字段编辑

---

## [v0.0.4 (b)] - 2025-12-30 Timeline View

- Session 历史、倒序、按日期分组

---

## [v0.0.4 (a)] - 2025-12-29 状态切换、排序、Archive

- Sleep/Cancel/Archive、按状态排序、Archive 视图

---

## [v0.0.3] - 2025-12 架构完善

- State 缓存、Renderer 纯渲染、actions 解耦、Info View

---

## [v0.0.2] - 2025-12-10 NOW Actioner

- 函数重设计、NOW Actioner、TUI 重构（AppState、Renderer）

---

## [v0.0.1] - 2025-12-06 MVP

首个可用版本。Track → Project → Item 层级，TUI → Actions → Services → Models → DB。

---

## 计划中

1. URL 解析与跳转
2. Record Done List
3. NOW 推荐优化
4. NOW 置顶
5. 模型时间字段统一 UTC
6. 中文输入法优化
