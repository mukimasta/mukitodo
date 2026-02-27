# ToFlow v0.2 开发者指南

本文档描述 ToFlow v0.2 的系统架构与实现，面向开发者。

## 项目结构

```
toflow/
├── __init__.py          # 包入口，导出 db_session、registry
├── __main__.py          # python -m toflow 入口，启动 TUI
├── database.py          # SQLite 连接、session、init_db
├── models.py            # ORM 模型（Track, Project, TodoItem, Session, NowTodayItem）
├── registry.py          # EntityType、MODELS、协议检查
├── utils.py             # 时间解析、UTC 转换
├── migrate.py           # v1→v2 schema 迁移
├── cli/
│   ├── __init__.py
│   ├── main.py          # Typer app 入口，无子命令时启动 TUI
│   ├── _common.py       # run_result、format_*、parse_deadline
│   ├── formatters.py    # format_track、format_project、format_todo、format_session_timeline
│   ├── track.py
│   ├── project.py
│   ├── todo.py
│   ├── box.py
│   ├── session.py
│   ├── archive.py
│   └── timeline.py
├── ops/
│   ├── __init__.py      # 导出 Result、各模块函数
│   ├── result.py
│   ├── crud.py
│   ├── query.py
│   ├── now_query.py
│   ├── status.py
│   ├── archive.py
│   ├── pin.py
│   ├── move.py
│   ├── session.py
│   └── today.py
└── tui/
    ├── __init__.py
    ├── app.py           # prompt-toolkit Application、键绑定、布局
    ├── state.py         # AppState、UIMode、PrimaryView
    ├── display.py       # 视口裁剪、truncate、zen 布局、render_*
    ├── types.py
    ├── text_width.py
    ├── item_formatters.py
    ├── view/
    │   ├── base.py      # View、EntityView
    │   ├── twp.py       # TWPTrackView、TWPProjectView
    │   ├── todos.py
    │   ├── box.py       # BoxTodosView、BoxProjectsView
    │   ├── picker.py    # PickerView（移动目标选择）
    │   ├── archive.py
    │   └── timeline.py
    ├── pane/
    │   ├── base.py      # Pane ABC
    │   ├── flat_list.py
    │   ├── group_box.py
    │   ├── today.py
    │   └── session.py
    ├── input/
    │   ├── intent.py
    │   ├── widgets.py
    │   ├── form.py
    │   ├── session.py
    │   └── service.py
    └── now/
        ├── state.py
        ├── config.py
        ├── types.py
        ├── timer.py
        ├── notifier.py
        ├── suggestion.py
        ├── runtime.py
        ├── view_today.py
        ├── view_suggestion.py
        └── view_promodoro.py
```

---

## 一、数据库设计

SQLite 数据库，路径：`~/.toflow/toflow.db`

**注意**：v0.2 将 Project 的 `track_id`、TodoItem 的 `project_id` 统一为 `parent_id`。旧版 `toflow.db` 可通过 `toflow migrate` 迁移。

### 实体定义

**Track**:

- `id` PRIMARY KEY
- `title` NOT NULL
- `description`
- `status` NOT NULL, DEFAULT 'active' (active / sleeping)
- `created_at_utc` NOT NULL
- `archived_at_utc` (NULL = 未归档)
- `order_index`

**Project** (Structure Project / Box Project):

- `id` PRIMARY KEY
- `parent_id` FOREIGN KEY (nullable, NULL = Box Project, FK → tracks.id)
- `title` NOT NULL
- `description`
- `deadline_utc`
- `willingness_hint` (0-3)
- `importance_hint` (0-3)
- `urgency_hint` (0-3)
- `status` NOT NULL, DEFAULT 'active' (active / sleeping / cancelled / finished)
- `pinned`: boolean, DEFAULT FALSE
- `created_at_utc` NOT NULL
- `started_at_utc`
- `finished_at_utc`
- `archived_at_utc` (NULL = 未归档)
- `order_index`
- Constraint: pinned => status='active'
- Promote (Box→Structure): 设置 parent_id 即从 Box 移至 Structure

**TodoItem** (Structure Todo / Box Todo):

- `id` PRIMARY KEY
- `parent_id` FOREIGN KEY (nullable, NULL = Box Todo, FK → projects.id)
- `title` NOT NULL
- `description`
- `url`
- `deadline_utc`
- `status` NOT NULL, DEFAULT 'active' (active / done / sleeping / cancelled)
- `total_stages`: int, DEFAULT 1
- `current_stage`: int, DEFAULT 0
- `pinned`: boolean, DEFAULT FALSE
- `created_at_utc` NOT NULL
- `started_at_utc`
- `finished_at_utc` (status=done 时非空)
- `archived_at_utc` (NULL = 未归档)
- `order_index`
- Constraint: status='done' ⟺ finished_at_utc IS NOT NULL
- Constraint: total_stages >= 1
- Constraint: 0 <= current_stage <= total_stages
- Constraint: pinned => status='active'

**Session** (Now Action Session):

- `id` PRIMARY KEY
- `title`
- `description`
- `todo_item_id` NOT NULL, FOREIGN KEY
- `duration_minutes` NOT NULL
- `started_at_utc` NOT NULL
- `ended_at_utc` (NULL means saving on-going session)
- Constraint: todo_item_id 必须关联 Todo

**Today** (NOW 今日队列):

- `todo_id` PRIMARY KEY（无独立 id）
- `planned_sessions` NOT NULL, 1–9（迁移后 < 10）
- `completed_sessions` NOT NULL, 0 起，≤ planned_sessions
- `order_index` NOT NULL
- Constraint: todo_id UNIQUE
- `get_items()` 时过滤掉已删除的 todo（不建 FK）

### 字段分布

| 字段               | Track | Project | TodoItem | Session |
| ---------------- | ----- | ------- | -------- | ------- |
| id               | ✓     | ✓       | ✓        | ✓       |
| title            | ✓     | ✓       | ✓        | ✓       |
| status           | ✓     | ✓       | ✓        | -       |
| description      | ✓     | ✓       | ✓        | ✓       |
| created_at_utc   | ✓     | ✓       | ✓        | -       |
| archived_at_utc  | ✓     | ✓       | ✓        | -       |
| order_index      | ✓     | ✓       | ✓        | -       |
| deadline_utc     | -     | ✓       | ✓        | -       |
| pinned           | -     | ✓       | ✓        | -       |
| parent_id        | -     | ✓       | ✓        | -       |
| todo_item_id     | -     | -       | -        | ✓       |
| willingness_hint | -     | ✓       | -        | -       |
| importance_hint  | -     | ✓       | -        | -       |
| urgency_hint     | -     | ✓       | -        | -       |
| url              | -     | -       | ✓        | -       |
| total_stages     | -     | -       | ✓        | -       |
| current_stage    | -     | -       | ✓        | -       |
| started_at_utc   | -     | ✓       | ✓        | ✓       |
| finished_at_utc  | -     | ✓       | ✓        | -       |
| duration_minutes | -     | -       | -        | ✓       |
| ended_at_utc     | -     | -       | -        | ✓       |

### 协议设计

只对**语义统一、实现相似**的能力抽象协议；控制协议数量（约 6–8 个），避免过度拆分。

| 协议               | 关键内容                                            | 实现者                               |
| ---------------- | ----------------------------------------------- | --------------------------------- |
| **Identifiable** | `id: int`                                       | Track, Project, TodoItem, Session |
| **Titleable**    | `title: str`                                    | Track, Project, TodoItem, Session |
| **Describable**  | `description: str | None`                       | Track, Project, TodoItem, Session |
| **Archivable**   | `archived_at_utc: datetime | None`（NULL = 未归档）  | Track, Project, TodoItem          |
| **Orderable**    | `order_index: int | None`                       | Track, Project, TodoItem          |
| **Statusable**   | `status: str`；`allowed_statuses() -> list[str]` | Track, Project, TodoItem          |
| **Parentable**   | `parent_id` 列（FK，nullable）                      | Project, TodoItem                 |
| **Editable**     | `editable_fields() -> list[FieldSpec]`          | Track, Project, TodoItem          |


### 实体 → 协议映射

| 实体           | 协议                                                                                            |
| ------------ | --------------------------------------------------------------------------------------------- |
| **Track**    | Identifiable, Titleable, Describable, Archivable, Orderable, Statusable, Editable             |
| **Project**  | Identifiable, Titleable, Describable, Archivable, Orderable, Statusable, Parentable, Editable |
| **TodoItem** | Identifiable, Titleable, Describable, Archivable, Orderable, Statusable, Parentable, Editable |
| **Session**  | Identifiable, Titleable, Describable                                                          |


### 不纳入协议的能力

- **Timeable**（deadline / started / finished）：仅 Project、TodoItem 有，实现差异大，在各自 ops 中处理
- **Stageable**（total_stages / current_stage）：仅 TodoItem，单独逻辑
- **Pinnable**：仅 Project、TodoItem，有 `set_pinned` ops；archive 时顺带 unpin
- **Hintable** / **URLLinkable** / **SessionDurable**：实体特有字段，不抽象为协议

### 通用类型

```
FieldSpec = (field: str, label: str, widget: "text"|"chip"|"date"|"select", options?: list[str])
Result    = (success: bool | None, data: Any, message: str)
```

### Registry 注册表

用 `EntityType` Enum + 简单映射，类型安全。

**EntityType**:

```
EntityType(str, Enum):
    TRACK = "track"
    PROJECT = "project"
    TODO = "todo"
    SESSION = "session"
```

**MODELS**: `EntityType -> ORM 类`（Track, Project, TodoItem, Session）

**PARENT_OF**: `EntityType -> EntityType | None`（仅 Project→TRACK, Todo→PROJECT）

**辅助函数**:

- `get_model_class(entity_type) -> type`
- `resolve(session, entity_type, entity_id) -> model | None`
- `get_parent_type(entity_type) -> EntityType | None`
- `get_parent_field(entity_type) -> str | None`
- `get_child_type(entity_type) -> EntityType | None` — 用于 cascade delete
- `get_referrers(entity_type) -> list[(model_cls, fk_column)]` — 被引用关系，用于 cascade delete
- `supports_protocol(entity_type, protocol_name) -> bool` — 基于 model 的 hasattr 推导

---

## 二、ops 层设计

仅**中粒度**：一个函数 = 一次持久化单元。toggle、archive 等业务编排由 TUI/CLI 上层完成（get → 算 → set）。

### 目录结构

```
ops/
├── __init__.py       # 导出 Result, EmptyResult, 各模块函数
├── result.py         # Result dataclass
├── crud.py           # create, update, delete
├── query.py          # list, get
├── now_query.py      # NOW 推荐候选查询
├── status.py         # set_status
├── archive.py        # set_archived
├── pin.py            # set_pinned
├── move.py           # reorder, reparent
├── session.py        # save_session, delete_session, update_session_description
└── today.py          # TodayStore：NOW 今日队列持久化（含排序/完成进度/清理）
```

### 各模块函数

**result.py**

```
Result(success: bool | None, data: Any, message: str)
EmptyResult = Result(None, None, "")
```

**crud.py**

- `create_entity(session, entity_type, **fields) -> Result`
- `update_entity(session, entity_type, entity_id, **updates) -> Result`
- `delete_entity(session, entity_type, entity_id) -> Result` — 含级联

**query.py**

- `get_entity(session, entity_type, entity_id) -> model | None`
- `list_entities(session, entity_type, *, parent_id=None, include_archived=False) -> Result`
  - **parent_id 语义**：Project 时 `parent_id=track_id` 过滤该 track 下的 projects，`parent_id=None` 为 Box projects；Todo 时 `parent_id=project_id` 过滤该 project 下的 todos，`parent_id=None` 为 Box todos。参数名与列名均为 `parent_id`。Track 无 parent，忽略 parent_id。
- `list_tracks_with_projects(session) -> Result`
- `list_archived_structure(session) -> Result`
- `list_timeline_records(session, limit: int | None = None) -> Result`

**now_query.py**

- `list_suggestion_candidates(session) -> Result` — NOW 推荐候选（active todo，校验 parent/project/track 状态）

**status.py**

- `set_status(session, entity_type, entity_id, new_status) -> Result` — 更新 status，顺带处理 unpin、finished_at_utc、stage
- `apply_stage_delta(session, entity_type, entity_id, stages_completed) -> Result` — 仅 TodoItem 支持 stage
- `set_stage(session, entity_type, entity_id, *, current_stage, total_stages) -> Result`

**archive.py**

- `set_archived(session, entity_type, entity_id, archived: bool) -> Result` — archived 时 unpin

**pin.py**

- `set_pinned(session, entity_type, entity_id, pinned: bool) -> Result` — 仅 Project、TodoItem；pinned 时要求 status='active'

**move.py**

- `reorder(session, entity_type, entity_id, direction: int) -> Result`
- `reparent(session, entity_type, entity_id, new_parent_id: int) -> Result`

**session.py**

- `save_session(session, todo_item_id, duration_minutes, started_at_utc, ended_at_utc=None, title=None, description=None) -> Result`
- `delete_session(session, session_id) -> Result`
- `update_session_description(session, session_id, description) -> Result`

**today.py** (TodayStore)

- `get_items() -> list[dict]` — 队列归一化 + 过滤已删除 todo
- `in_today_ids() -> set[int]`
- `add_item(todo_id, planned_sessions=1) -> Result`
- `remove_item(todo_id) -> Result`
- `reorder(todo_id, direction) -> Result`
- `adjust_planned(todo_id, delta) -> Result` — planned ≥ completed
- `mark_session_completed(todo_id) -> Result`
- `first_unfinished_todo_id() -> int | None`
- `next_unfinished_todo_id(current_todo_id) -> int | None`
- `clear_all() -> Result` — r 清空
- `is_full() -> bool`

### 调用方编排

toggle、archive 等由 TUI state 或 CLI 编排：`get_entity` → 根据 allowed_statuses 计算 next_status → `set_status`。**所有 ops 调用需由调用方通过 `with db_session() as s:` 传入 session。**

### 调用约定

- **session 全传入**：所有 ops 函数第一个参数为 `session`，由调用方通过 `db_session()` 提供；事务边界由调用方控制
- 返回 `Result`，调用方根据 `result.success` 处理
- 多步原子操作：同一 `with db_session() as s:` 内连续调用多个 ops，任一步失败即整体 rollback

---

## 三、CLI 设计

命令分类：`track` | `project` | `todo` | `box` | `session` | `archive` | `timeline`。

- **box** 为独立分类：包含 Box Todos (`parent_id=NULL`) 与 Box Projects (`parent_id=NULL` 的 Project)
- `box todo add`、`box project add` 等价于 `todo add`（省略 --parent-id）、`project add`（省略 --parent-id）
- `box todo reparent`、`box project reparent` 对应 `reparent` ops

**CLI 反馈**

- 成功：输出 `result.message` 到 stdout
- 失败：输出错误信息到 stderr，退出码非 0

命令详见 [MANUAL.md](MANUAL.md)。

**CLI formatters**：`cli/formatters.py` 将 entity dict 格式化为纯文本，供 `print()` 输出。

| 函数                              | 输入           | 输出格式                                              |
| ------------------------------- | ------------ | ------------------------------------------------- |
| `format_track(item)`            | track dict   | `[archived] id title [status]`                    |
| `format_project(item)`          | project dict | `[archived] id title [status]`                    |
| `format_todo(item)`             | todo dict    | `[archived] id title [status] cur/total`          |
| `format_session_timeline(item)` | session dict | `id | parent_info | duration | time_range | desc` |

- 依赖 `utils.format_utc_to_local` 转换时间显示

---

## 四、TUI 架构

核心原则：**不搞 if-else，用通用抽象，一个解决所有。**

### 分层架构

```
App ─── 键绑定 + prompt-toolkit 接线，纯胶水
 └─ AppState ─── structure_stack + primary + secondary + modal + UI mode
     └─ View ─── 领域操作（load / toggle / delete / add），每个 View 对应一种实体
         └─ Pane ─── 光标 + 选中样式 + 渲染为 Lines
             └─ item_formatter ─── 纯函数，(item) -> FormattedText，只管内容
```

**自底向上**：每一层只做自己的事，不越界。

| 层              | 输入           | 输出                  | 职责边界                                        |
| -------------- | ------------ | ------------------- | ------------------------------------------- |
| item_formatter | `dict`       | `FormattedText`（一行） | 只关心 item 内容和状态样式                            |
| Pane           | formatter 输出 | `Lines`             | 光标位置、选中样式覆盖、前缀（▸）、布局结构（盒子/列表）               |
| View           | 用户操作         | `Result`            | 数据库 CRUD、导航（push/pop）、持有一个 Pane             |
| AppState       | View 操作结果    | UI 状态               | structure_stack、primary、secondary、modal、UI 模式 |
| App            | 按键事件         | —                   | 将按键分发到 AppState/View，组装 prompt-toolkit 布局   |


### 基础类型

```python
FormattedText = list[tuple[str, str]]   # 一行的样式段：[(style, text), ...]
Lines         = list[FormattedText]     # 多行：每个元素是一行
```

### Input 子系统

Input 已从 View 中完全解耦：**View 不再构建表单、不再提交表单**，只提供上下文（entity_type / selected_id / add_parent_id）。

```
tui/input/
├── intent.py    # InputIntent：按键动作抽象
├── widgets.py   # Text/Date/Stage/Hint/Select 字段行为与渲染
├── form.py      # InputForm：字段状态、光标、diff、日期归一化
├── session.py   # InputSession + InputMode：一次输入会话
└── service.py   # FormService：构建会话 + 提交编排
```

#### 职责边界

- App：key -> `InputIntent` 分发；触发 add/edit；调用 submit；刷新当前 view
- AppState：只管理 `input_session` 生命周期（start/take/cancel），不依赖 FormService
- InputForm：字段级状态与编辑规则（text/date/stage/hint/select）
- FormService：构建 `InputSession`，并将提交拆分为 ops 调用序列
- View：只做导航与实体动作（delete/toggle/pin/reorder）；仅暴露 `selected_id()`、`add_parent_id()`

#### 输入数据流（Input 模式）

`key event -> InputIntent -> InputForm.handle_intent() -> Widget.handle()`  
`Widget.render_*() -> display.render_input_form_lines()`  
`Enter -> AppState.take_input_session() -> FormService.submit(session) -> ops`

#### 提交编排（FormService）

- Add：`build_add_session()` -> `submit()`
  - 校验 title
  - 组装 payload（含 parent_id）
  - date 字段统一用 `InputForm.normalize_date_value()`
  - `create_entity`
  - Todo 且有 stage 时追加 `set_stage`
- Edit：`build_edit_session()` -> `submit()`
  - `form.to_updates()`
  - 拆分普通字段 / status / stage
  - 分别调用 `update_entity` / `set_status` / `set_stage`

#### 事务语义

- `FormService.submit()` 在同一 `db_session()` 内执行多步 ops
- 任一步返回失败，抛内部异常中断，触发整体 rollback
- 成功后由 App 刷新当前 View（`current_view.load_data()`）

#### Widget 映射

- `text` -> `TextWidget`
- `date` -> `DateWidget`
- `stage` -> `StageWidget`
- `chip/select` 且 `*_hint` -> `HintWidget`
- 其他 `chip/select` -> `SelectWidget`

### 渲染管线

数据从 Pane 到屏幕，经过四步变换，类型始终是 `Lines`，直到最后一步才展平：

```
Pane.render()          -> Lines    # 完整内容（可能超出终端）
  -> truncate_lines()  -> Lines    # 横向截断：超宽行加 …
  -> clip_to_viewport() -> Lines   # 纵向裁剪：只留视口范围内的行
  -> flatten()         -> FormattedText  # 行间插 \n，交给 prompt-toolkit
```

设计细节：`\n` 只在 `flatten` 最后一步出现。Pane 产出结构化的行列表，中间处理函数直接操作行，不需要拆分/重组。

### Pane — 渲染核心

Pane = Layout + Cursor + Render 三合一。每种 Pane 自己管光标、自己渲染。

| Pane 类型 | 布局 | 光标 | 用途 |
| --- | --- | --- | --- |
| FlatListPane | 平铺列表 | 单层索引 | todos / box / timeline / suggestion |
| GroupBoxPane | 分组盒子 | 双层 group ↔ row | Structure: Track→Project |
| TodayPane | 平铺列表（Zen） | 单层索引 | NOW Today（session dots + `+ Add...`） |
| SessionPane | 静态内容（Zen） | 无光标 | NOW Focus / Reflect / Rest |


Pane ABC 接口：

```python
move(delta: int)                  # 移动光标
selected_id() -> int | None       # 当前选中 ID
selected_item() -> dict | None    # 当前选中 item
render() -> Lines                 # 渲染完整内容（不含视口裁剪）
selected_line_index() -> int | None  # 选中行在 Lines 中的索引，供视口定位
viewport_start: int               # 滚动位置，跟随 Pane 实例
```

### View — 视图操作

每个 View 持有一个 Pane，声明 `entity_type` 和 `toggle_target`。基类提供默认的 `delete_selected` / `toggle_selected`（通过 `_with_selected` 模板方法），子类只需实现真正不同的逻辑。

```python
class View(ABC):
    title: str                     # 面包屑标题
    entity_type: EntityType        # 操作的实体类型
    toggle_target: str             # Space 切换的目标状态（如 "sleeping"）

    pane -> Pane                   # 关联的 Pane（抽象属性）
    load_data()                    # 从数据库加载数据到 Pane
    go_deeper(state) / go_back(state)  # 导航：右键深入、左键返回
    delete_selected() -> Result    # 默认：按 entity_type 删除
    toggle_selected() -> Result    # 默认：在 active ↔ toggle_target 间切换
    selected_id() -> int | None    # 当前选中实体 ID（供 edit 使用）
    add_parent_id() -> int | None  # 当前父上下文 ID（供 add 使用）
```

已实现：

| View | Pane | 实体 | 说明 |
| --- | --- | --- | --- |
| TWPTrackView | GroupBoxPane (group 层) | Track | Structure 根视图 |
| TWPProjectView | GroupBoxPane (row 层) | Project | 与 TWPTrackView 共享同一个 Pane 实例 |
| TodosView | FlatListPane | Todo | Project 下的 Todos |
| BoxTodosView | FlatListPane | Todo | Box 待办 |
| BoxProjectsView | FlatListPane | Project | Box 项目 |
| ArchiveView | FlatListPane | — | 归档结构 |
| TimelineView | FlatListPane | — | Session 历史 |
| PickerView | GroupBoxPane | — | 移动目标选择（reparent） |
| TodayView | TodayPane | Todo | NOW 今日队列 |
| SuggestionView | FlatListPane（Zen） | Todo | NOW 推荐列表 |
| PromodoroView | SessionPane（Zen） | Todo | NOW 执行流程（Focus/Reflect/Rest） |


**共享 Pane 模式**：TWPTrackView 和 TWPProjectView 共享同一个 GroupBoxPane，视觉相同（盒子布局），通过 `drill_in()` / `drill_out()` 在 push/pop 时切换光标层级。

导航栈：`TWPTrackView → TWPProjectView → TodosView`

### AppState — 极薄状态

```python
structure_stack: list[View]  # Structure 导航栈
now: NowState                # NOW 聚合状态
primary: PrimaryView         # STRUCTURE / NOW
secondary: View | None       # Box/Archive/Timeline
modal: View | None           # Picker 等临时层
ui_mode: UIMode              # NORMAL / CONFIRM / INPUT
last_result: Result          # 上次操作结果
```

- `current_view` 优先级：`modal > secondary > primary`
- `is_now_active()` 统一判断 NOW 主视图是否处于可交互态（无 secondary/modal）
- **Confirm 模式**：存一个 `Callable` + trigger_key。同键确认，异键取消
- **Input 模式**：存一个 `InputSession`。Enter 由 App 取出 session 并调用 `FormService.submit()`

### NOW 视图（已实现）

NOW 已落地为一个独立子域，App 仅做接线。

**核心模块**

| 模块 | 职责 |
| --- | --- |
| `tui/now/state.py` (`NowState`) | 聚合 `today/suggestion/promodoro`，统一 NOW 行为入口（`adjust_current`、`handle_note_key`、`open_note`、`reset_confirm_request`） |
| `tui/now/view_today.py` | Today 列表：队列管理、开始 focus、清空/删除/排序/session 调整 |
| `tui/now/view_suggestion.py` | 推荐列表：`Enter` 加入后立即回 Today |
| `tui/now/view_promodoro.py` | Focus/Reflect/Rest phase 状态机，session 持久化与 stage 变更 |
| `tui/now/runtime.py` | 计时 runtime 循环：tick、响铃、time-up 事件分发、UI invalidate |
| `tui/now/timer.py` | 纯计时器（arm/start/pause/resume/update） |
| `ops/today.py` (`TodayStore`) | Today 队列持久化与归一化（含 orphan 清理） |
| `ops/now_query.py` + `tui/now/suggestion.py` | 推荐候选 + 打分引擎 |

**关键行为（当前实现）**

- Today 最大 5 项，满额隐藏 `+ Add...`；`planned_sessions` 范围 1–9 且不低于 `completed_sessions`
- Suggestion `Enter`：加入 Today 成功后立即返回 Today，并重新计算推荐（过滤已在 Today 的 todo）
- Suggestion 行尾显示推荐理由标签：`PIN/PROJ PIN`、`DDL mm-dd`、`STAGE`、`MOMENTUM`
- Focus `q` 可触发全局退出确认
- Reflect note 为单行自由输入，`q/s/a/p` 等按键按普通文本处理
- Reflect 保存后进入 Rest 准备态（不自动开始，需 `Space`）
- Rest 不显示 next 文案；休息结束/跳过后统一回到 Today，不自动跳转下一个 focus
- `t` 可在 NOW 子视图与 Today 面板间切换（计时继续）

### App — 接线层

纯胶水，不承载领域逻辑。

- 键绑定按 UIMode 过滤（`is_normal` / `is_confirm` / `is_input`）
- NOW 相关动作统一走 `NowState`（而非在 `app.py` 里分支判断具体 view/phase）
- 计时循环由 `run_timer_runtime()` 托管，App 只创建后台任务并接收结果回写 `last_result`
- 布局：`[title_bar] | main_content | separator | status_bar | [input_area]`
- Zen 模式下隐藏顶部标题栏，仅保留内容区居中渲染 + 底部状态栏
