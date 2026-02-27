# Item 样式系统设计（v0.2）

> 目标：统一 `toflow/tui/item_formatters.py` 的视觉语义与排版规则，降低样式分歧，确保各视图在信息密度与可读性之间稳定一致。

## 1. 本版决策

基于当前确认：

- NOW 不再做"纯内容居中"，改为 **固定宽度表格块**：块内按"左对齐 + 右对齐"排版，再将整块居中。
- NOW Suggestion 推荐理由标签 **最多显示 1 个**。
- Track 在 sleeping 状态 **不显示 icon**。
- formatter **不参与终端宽度计算**，只输出完整语义内容。

未明确项先采用默认策略（后续可在此文档增量修订）。

## 2. 设计范围

本文覆盖以下 formatter 的规范：

- `format_track_item`
- `format_track_group`
- `format_project_row`
- `format_todo_item`
- `format_archive_item`
- `format_timeline_item`
- `format_now_today_item`
- `format_now_suggestion_item`

## 3. 样式目标

1. **一致性**：同语义在所有视图使用同一图标/色彩语义。
2. **可扫描**：主信息优先（标题），次信息收敛到右侧或 dim 区域。
3. **低噪音**：默认低饱和；高亮仅用于 selected / error / confirm。
4. **统一体验**：统一使用 Unicode 图标方案，不做 ASCII 回退。

## 4. 视觉语义层（Style Class）

建议统一引入以下语义类（在 `APP_STYLE` 中实现）：

| 类名 | 用途 |
| --- | --- |
| `class:item.icon` | 通用图标段 |
| `class:item.title` | 主标题 |
| `class:item.meta` | 次信息（project/context/time） |
| `class:item.tag` | 标签（PIN/DDL/STAGE） |
| `class:item.dim` | 弱化文本 |
| `class:item.done` | 完成态文本 |
| `class:item.cancelled` | 取消态文本 |
| `class:item.pinned` | 置顶强调 |

保留现有状态类兼容：

- `class:track.active/sleeping`
- `class:project.active/sleeping/finished/cancelled`
- `class:todo.active/sleeping/done/cancelled`

## 5. 图标与状态映射

### 5.1 图标方案（Unicode）

#### Track（仅 active / sleeping）

| 语义 | 图标 |
| --- | --- |
| active | （无） |
| sleeping | （无） |

#### Project / Todo / Archive

| 语义 | 图标 |
| --- | --- |
| active | `○` |
| sleeping | `z` |
| finished/done | `◉` |
| cancelled | `×` |
| pinned | `✜` |

## 6. 排版基元

### 6.1 单行原则

- formatter 只产出 **单行** `FormattedText`，不换行。
- 超长截断交由 `display.truncate_lines()`。

### 6.2 左右锚点行（LR 行）

定义：

- 左块 `L`：主信息（icon + title）
- 右块 `R`：次信息（stage / dots / duration / tag / context）
- 宽度 `W`：固定行宽
- 规则：`L` 左对齐，`R` 右对齐，中间填充空格

伪公式：

`line = L + " " * max(1, W - width(L) - width(R)) + R`

## 7. NOW 固定宽度表格块（核心）

### 7.1 约束

- 新增常量：`NOW_TABLE_WIDTH = 64`
- NOW 子视图目标布局宽度为 `W=64`，再由 `apply_zen_layout` 居中整个块。
- `formatter` 不读取终端宽度，不负责 `W` 的降级策略。
- 终端宽度适配（例如窄屏降宽）由 Pane / Display 层处理。

### 7.2 含义

这保证 NOW 既有"Zen 居中"的整体感，又有"表格锚点"的信息秩序，不会出现散乱漂浮文本。

## 8. 各 formatter 规范

### 8.1 `format_track_item`

- active：`[title]`
- sleeping：`[title]`（无 icon，dim）
- 无右侧 meta

示例：

- `Work`
- `Work`（sleeping, dim）

### 8.2 `format_track_group`

- 结构同 Track Item，但作为 Group header
- 使用 header 强调样式（bold）

### 8.3 `format_project_row`

- 左块：`[icon] [title] [flags]`
- 右块（可选）：`[hints] [DDL]`
- pinned 时 icon 优先 `✜`，并使用 pinned 样式

示例：`✜ Q1 Plan [≡][⧗6h0m]                  ♥⚡ DDL 03-05`

### 8.4 `format_todo_item`

- 左块：`[icon] [title] [flags]`
- 右块：`[stage] [DDL?]`（无值则省略）
- stage 仅当 `total_stages > 1` 显示，如 `[2/5]`

示例：`○ Draft intro [↗][⧗45m]                [2/5]`

### 8.5 `format_archive_item`

- 保留 depth 缩进。
- 未归档父上下文继续 dim，并追加 `(has archived children)`。
- todo 仍显示 stage（若 `total_stages > 1`）。

### 8.6 `format_timeline_item`

- 日期头：`-- YYYY-MM-DD --`（dim）。
- session 行改为 LR 行：
  - 左块：`HH:MM  25m  parent_info`
  - 右块：`description(截断)`
- description 为空则省略右块。

### 8.7 `format_now_today_item`

- 使用 NOW 固定宽度 LR 行（W=64）：
  - 左块：`[✓?] title`
  - 右块：`dots + project`
- `+ Add...` 作为特殊 dim 行。

示例：

- `Write chapter                         ● ○ ○  Academic`
- `✓ Tax form                               ●  Life`

### 8.8 `format_now_suggestion_item`

- 使用 NOW 固定宽度 LR 行（W=64）：
  - 左块：`title`
  - 右块：`context + [tag](最多1个)`
- 已在 Today（若未来恢复显示）则整行 dim + `✓` 前缀。

### 8.9 Flags & Hints 规则

#### Flags（Project / Todo）

- has description: `[≡]`
- has url: `[↗]`（仅 Todo）
- session:
  - `<60m`：`[⧗Xm]`
  - `>=60m`：`[⧗HhMm]`
  - 总历史累计，向下取整
  - Todo：统计该 todo 的总历史 session 时长
  - Project：统计该 project 的总历史 session 时长，需包含 children 累计

#### Hints（仅 Project）

- willingness（2-3 显示）：`♥`
- importance（2-3 显示）：`⭑`
- urgency（2-3 显示）：`⚡`

## 9. Suggestion Tag 规则（最多 1 个）

### 9.1 候选标签

- `PIN`
- `DDL mm-dd (+/-Nd)` 或 `DDL mm-dd today`
- `STAGE cur/total`
- `MOMENTUM`

### 9.2 选择优先级

`PIN > DDL > STAGE > MOMENTUM`

仅取第一项显示，避免标签噪音。

## 10. 状态优先级

同一 item 多语义冲突时，按以下优先级渲染：

1. `selected`（Pane 覆盖）
2. `pinned`
3. `cancelled/done/sleeping`
4. `active`
5. `meta/tag/dim`

## 11. 实施顺序（建议）

1. 在 `item_formatters.py` 抽取统一 helper：图标映射、stage/ddl、LR 拼接。
2. 先改 NOW 两个 formatter（Today/Suggestion），验证固定宽度视觉。
3. 再改 timeline / todo / project / archive。
4. 最后补 `APP_STYLE` 新 class，并做一次全视图回归截图检查。

## 12. 验收标准

- 同一终端宽度下，各视图行布局稳定，无随机漂移。
- NOW 视图呈现"表格锚点 + 整体居中"。
- Suggestion 每行最多 1 个 reason tag。
- 所有 formatter 输出仍是单行 `FormattedText`，不侵入 Pane 选中逻辑。
