---
name: dingtalk-ai-table
description: 钉钉 AI 表格（多维表）操作技能。使用 mcporter CLI 连接钉钉官方新版 AI 表格 MCP server，基于 baseId / tableId / fieldId / recordId 体系执行 Base、Table、Field、Record 的查询与增删改。适用于创建 AI 表格、搜索表格、读取表结构、批量增删改记录、批量建字段、更新字段配置、按模板建表等场景。需要配置 DINGTALK_MCP_URL 或直接使用 Streamable HTTP URL。
version: 0.6.0
metadata:
  author: Marila@Dingtalk
  category: productivity
  tags:
    - dingtalk
    - spreadsheet
    - mcp
    - automation
    - data-management
  documentation: https://github.com/aliramw/dingtalk-ai-table
  support: https://github.com/aliramw/dingtalk-ai-table/issues
  openclaw:
    requires:
      env:
        - DINGTALK_MCP_URL
        - OPENCLAW_WORKSPACE
      bins:
        - mcporter
        - python3
    primaryEnv: DINGTALK_MCP_URL
    homepage: https://github.com/aliramw/dingtalk-ai-table
---

# 钉钉 AI 表格操作（新版 MCP）

## 🚀 5 分钟快速开始

### 1️⃣ 列出我的表格
```bash
mcporter call '<DINGTALK_MCP_URL>' .list_bases limit=5
```

### 2️⃣ 创建新表格
```bash
mcporter call '<DINGTALK_MCP_URL>' .create_base baseName='我的项目'
```

### 3️⃣ 添加记录
```bash
mcporter call '<DINGTALK_MCP_URL>' .create_records \
  --args '{"baseId":"base_xxx","tableId":"tbl_xxx","records":[{"cells":{"fld_name":"张三"}}]}'
```

### 4️⃣ 查询记录
```bash
mcporter call '<DINGTALK_MCP_URL>' .query_records \
  --args '{"baseId":"base_xxx","tableId":"tbl_xxx","limit":10}'
```

### 5️⃣ 批量导入
```bash
python3 scripts/import_records.py base_xxx tbl_xxx data.csv
```

---

## 核心概念

按 **新版 MCP schema** 工作：
- Base：`baseId`
- Table：`tableId`
- Field：`fieldId`
- Record：`recordId`

不要再用旧版 `dentryUuid / sheetIdOrName / fieldIdOrName`。

推荐使用 `mcporter 0.8.1` 及以上版本。

输出模式兼容说明：
- `mcporter 0.8.1+` 可直接调用
- 更低版本需要显式加 `--output text`
- AI 表格 MCP 无论使用哪种模式，返回体本身都是标准 JSON；差异主要在 `mcporter` 的输出处理方式

## 版本守门规则（每个 MCP Server 地址只强制检查一次）

在真正开始任何 AI 表格操作前，必须先检查当前 `mcporter` 注册的 `dingtalk-ai-table` MCP server 实际返回的 tools schema。**但这个检查不该每次都重复做；同一个 MCP Server 地址只需要强制检查一次。**

### 一次性检查策略

1. 先读取当前 `mcporter` 里 `dingtalk-ai-table` 对应的 MCP Server 地址。
2. 用这个地址生成一个本地检查标记（例如基于完整 URL 或其 hash）。
3. 在工作区保存检查结果，例如放到：

```text
~/.openclaw/workspace/.cache/dingtalk-ai-table/
```

建议文件名模式：

```text
schema-check-<url-hash>.json
```

4. 如果当前地址对应的检查标记已经存在，并且结果是“已确认新版 schema”，则**跳过重复检查**，直接继续后续 AI 表格操作。
5. 只有在以下情况才重新强制检查：
   - 第一次运行，没有检查标记
   - `mcporter` 里的 MCP Server 地址变了
   - 之前检查结果是旧版 schema / 检查失败
   - 用户明确要求重新验证

### 强制检查时执行

```bash
mcporter list dingtalk-ai-table --schema
```

### 判断标准

如果返回的 tools 仍然是旧版这一套，例如出现：
- `get_root_node_of_my_document`
- `create_base_app`
- `list_base_tables`
- `add_base_record`
- `search_base_record`
- `list_base_field`

或者整体仍然基于：
- `dentryUuid`
- `sheetIdOrName`
- `fieldIdOrName`

那么说明：**虽然 skill 文件已经是新版，但 mcporter 里注册的 MCP server 地址还是旧的，不能继续操作。**

### 遇到旧版 schema 时的强制提示

此时必须明确提示用户：

1. 打开这个页面：
   `https://mcp.dingtalk.com/#/detail?mcpId=9555&detailType=marketMcpDetail`
2. 点击右侧 **「获取 MCP Server 配置」** 按钮
3. 复制新的 MCP Server 地址
4. 用新的地址替换 `mcporter` 里已经注册的 `dingtalk-ai-table` 地址
5. 替换完成后，再重新执行：

```bash
mcporter list dingtalk-ai-table --schema
```

只有当返回的 tools 已经变成新版 schema，例如出现：
- `list_bases`
- `get_base`
- `get_tables`
- `get_fields`
- `query_records`
- `create_records`
- `update_records`
- `delete_records`
- `prepare_attachment_upload`

才允许继续真正的 AI 表格操作。

### 通过检查后的处理

一旦确认当前 MCP Server 地址返回的是新版 schema，就把结果写入本地检查标记。后续只要 `mcporter` 里的 `dingtalk-ai-table` 地址没变，就不要再重复做这一步守门检查。

### 用户提示文案（可直接复用）

```text
当前 mcporter 里注册的 dingtalk-ai-table 还是旧版 MCP schema，暂时不能按新版技能操作。
请打开 https://mcp.dingtalk.com/#/detail?mcpId=9555&detailType=marketMcpDetail ，点击右侧“获取 MCP Server 配置”按钮，复制新的 MCP Server 地址，并替换 mcporter 里已注册的 dingtalk-ai-table 地址。替换后重新检查 schema，确认出现 list_bases / get_base / create_records 等新版 tools 后，再继续操作 AI 表格。
```

## 前置要求

### 安装 mcporter CLI

```bash
npm install -g mcporter
# 或
bun install -g mcporter
```

验证：

```bash
mcporter --version
```

### 配置 MCP Server

在钉钉 MCP 广场 https://mcp.dingtalk.com/#/detail?mcpId=9555&detailType=marketMcpDetail 获取新版钉钉 AI 表格 MCP 的 `Streamable HTTP URL`。

方式一：直接配置到 mcporter

```bash
mcporter config add dingtalk-ai-table --url "<Streamable_HTTP_URL>"
```

方式二：使用环境变量

```bash
export DINGTALK_MCP_URL="<Streamable_HTTP_URL>"
```

> 这个 URL 带访问令牌，等同密码，不要泄露。

### 工作区沙箱

脚本读取本地文件时，会优先使用 `OPENCLAW_WORKSPACE` 作为允许根目录：

```bash
export OPENCLAW_WORKSPACE="$HOME/.openclaw/workspace"
```

未设置时默认使用当前工作目录。

## 核心工具集

### Base 层
- `list_bases`
- `search_bases`
- `get_base`
- `create_base`
- `update_base`
- `delete_base`
- `search_templates`

### Table 层
- `get_tables`
- `create_table`
- `update_table`
- `delete_table`

### Field 层
- `get_fields`
- `create_fields`
- `update_field`
- `delete_field`

### Record 层
- `query_records`
- `create_records`
- `update_records`
- `delete_records`

### 附件层
- `prepare_attachment_upload`

## 推荐工作流

### 1. 先找 Base

```bash
mcporter call dingtalk-ai-table list_bases limit=10
mcporter call dingtalk-ai-table search_bases query="销售"
```

### 2. 再拿 Table 目录

```bash
mcporter call dingtalk-ai-table get_base baseId="base_xxx"
```

### 3. 再展开表结构

```bash
mcporter call dingtalk-ai-table get_tables \
  --args '{"baseId":"base_xxx","tableIds":["tbl_xxx"]}'
```

### 4. 字段复杂时读完整配置

```bash
mcporter call dingtalk-ai-table get_fields \
  --args '{"baseId":"base_xxx","tableId":"tbl_xxx","fieldIds":["fld_xxx"]}'
```

### 5. 再查 / 写记录

**基础查询：**

```bash
mcporter call dingtalk-ai-table query_records \
  --args '{"baseId":"base_xxx","tableId":"tbl_xxx","limit":100}'
```

**查询执行规则（必须遵守）：**

AI 表格不适合作为数据库做复杂组合分页查询。Agent 执行查询时必须按以下规则处理：

1. 不要使用“排序 + 过滤 + 翻页”连续遍历。
2. 不要使用“排序 + 翻页”连续遍历。
3. 不要使用“过滤 + 翻页”连续遍历。
4. 如果需要过滤，先过滤获取第一页，处理后回写辅助标记字段，下次继续查询未标记数据。
5. 如果需要排序，也只读取当前排序结果第一页，处理后回写辅助标记字段，不要依赖排序 + 翻页完成全量遍历。
6. 如果表里没有可用的回写字段，Agent 可以自动新增一个辅助字段，例如 `处理标记`、`查询标记`、`同步标记` 或 `AI处理标记`。
7. 辅助字段只用于避免重复读取和模拟稳定分页，不应承载业务含义。

**过滤字段规则：**

filter 中提供的是字段 ID，不是字段名称。Agent 不能直接把 `商品ID`、`日期`、`店铺` 这类字段名放进过滤条件。

正确流程：

1. 先读取字段列表。
2. 根据字段名称找到对应字段，例如 `商品ID`。
3. 取得该字段的 `fieldId`。
4. 使用 `fieldId` 构造过滤条件。

示例：

```text
用户要求：查询商品ID = 123456 的记录

正确做法：
1. get_fields / get_tables 读取字段列表
2. 找到 fieldName = 商品ID 的字段
3. 取得 fieldId，例如 fld_product_id
4. 使用 fld_product_id 构造 filter

错误做法：
直接把 商品ID 当成过滤字段传入
```

**按日期过滤查询：**

当前更适合按日期过滤。

支持：

```text
2026-05-01 ✅
```

不支持或不可依赖：

```text
2026-05-01 01:00 ~ 2026-05-01 02:00 ❌
```

如果用户要求小时、分钟、秒级时间范围，先按日期查询，再在本地代码里继续筛选。

示例：

```json
{
  "baseId": "base_xxx",
  "tableId": "tbl_xxx",
  "limit": 100,
  "filter": {
    "operator": "and",
    "operands": [{
      "operator": "eq",
      "operands": ["日期字段fieldId", "2026-05-01"]
    }]
  }
}
```

> 注意：filter 中字段必须使用 **fieldId**，不是 fieldName。`singleSelect` 过滤必须传 option id（通过 `get_fields` 获取）。
> 其他操作符以当前 MCP schema 为准。不要为了实现精确时间段查询，强行构造小时级 `between` 条件。

**排序查询：**

排序只允许用于确定当前第一页的处理优先级，不要依赖排序 + 翻页完成全量遍历。

```json
{
  "sort": {"operator": "desc", "fieldName": "采集时间"},
  "limit": 100
}
```

处理完当前第一页后，应回写辅助标记字段，下次查询时排除已标记数据。

**图片 / 附件字段查询规则：**

图片 / 附件字段通常会显著拖慢查询速度。Agent 查询前应先读取字段信息。

默认规则：

1. 如果用户没有明确要求图片、截图、附件、凭证等字段，默认只返回非图片 / 非附件字段。
2. 查询前先通过字段列表识别 `attachment`、图片、截图、凭证等字段。
3. 如果当前 MCP schema 支持指定返回字段，则只传入非图片 / 非附件字段的 fieldId。
4. 如果当前 MCP schema 不支持指定返回字段，则查询后只使用非图片字段，并在必要时提示图片字段可能导致查询变慢。
5. 用户明确要求图片字段时，再单独查询图片字段或按记录补查。

示例：

```text
用户需求：查询今天的销售记录

推荐返回字段：
店铺、日期、销售额、花费、ROI、备注

默认排除字段：
截图、图片、附件、凭证
```

---

### 6. 写入附件字段

attachment 字段支持三种写法：

**方式一：先上传，再写 fileToken（推荐，可靠）**

```bash
# Step 1：申请上传地址（返回 uploadUrl 和 fileToken）
mcporter call dingtalk-ai-table prepare_attachment_upload \
  --args '{"baseId":"base_xxx","fileName":"report.pdf","size":102400,"mimeType":"application/pdf"}'

# Step 2：把文件 PUT 到 uploadUrl（必须带 Content-Type，值必须与 mimeType 完全一致）
curl -X PUT "<uploadUrl>" \
  -H "Content-Type: application/pdf" \
  --data-binary @report.pdf

# Step 3：把 fileToken 写入记录
mcporter call dingtalk-ai-table create_records \
  --args '{"baseId":"base_xxx","tableId":"tbl_xxx","records":[{"cells":{"fld_attach":[{"fileToken":"ft_xxx"}]}}]}'
```

**方式二：直接传外链 URL（异步转存，best-effort）**

```bash
mcporter call dingtalk-ai-table create_records \
  --args '{"baseId":"base_xxx","tableId":"tbl_xxx","records":[{"cells":{"fld_attach":[{"url":"https://example.com/file.pdf"}]}}]}'
```

> URL 转存是 best-effort 异步链路，返回成功仅表示已受理，不保证立即可读。可靠写入请用 fileToken 方式。

**方式三：原样回传已有附件数据（保留 / 追加已有附件时使用）**

从 `query_records` 读出的 attachment 单元格数据是完整对象数组，字段形状如下：

```json
[
  {
    "filename": "a.xlsx",
    "size": 92250,
    "type": "xls",
    "resourceId": "<id>",
    "resourceUrl": "<resourceUrl>"
  }
]
```

其中 `type` 是文件类别枚举，常见值为 `"xls"`、`"image"` 等；`resourceUrl` 通常为有时效的下载链接。

如需保留已有附件，把读出的值原样塞回即可。如需追加新附件，把新的 `{"fileToken":"ft_xxx"}` 与已有对象合并成一个数组一起传入。

`update_records` 的 attachment 字段格式相同，传入后会整体覆盖该字段。

## 脚本

### 批量新增字段

```bash
python3 scripts/bulk_add_fields.py <baseId> <tableId> fields.json
```

`fields.json` 示例：

```json
[
  {"fieldName":"任务名","type":"text"},
  {"fieldName":"优先级","type":"singleSelect","config":{"options":[{"name":"高"},{"name":"中"},{"name":"低"}]}}
]
```

兼容项：
- `name` 会自动映射为 `fieldName`
- `phone` 会自动映射为 `telephone`

### 批量导入记录

```bash
python3 scripts/import_records.py <baseId> <tableId> data.csv
python3 scripts/import_records.py <baseId> <tableId> data.json 50
```

说明：
- CSV 表头默认按 `fieldId` 解释
- JSON 支持：
  - `[{"cells": {...}}]`
  - `[{"fld_xxx": "value"}]`

## 安全规则

- 文件路径受 `OPENCLAW_WORKSPACE` 沙箱限制
- 仅允许读取工作区内 `.json` / `.csv` 文件
- Base / Table / Field / Record ID 都做格式校验
- 批量上限按 MCP server 实际限制控制：
  - `create_fields`：最多 15
  - `get_tables / get_fields`：最多 10
  - `create_records / update_records / delete_records`：最多 100

## 调试原则

- 先 `get_base`，再 `get_tables`，必要时 `get_fields`
- 不要猜 `fieldId`
- 构造过滤条件前，必须先把字段名转换为 fieldId
- 不要依赖“排序 + 过滤 + 翻页”、“排序 + 翻页”、“过滤 + 翻页”做全量遍历
- 批量处理优先使用“查询第一页 + 回写辅助标记字段”的方式推进
- 用户未明确要求图片 / 附件字段时，默认排除图片 / 附件字段
- 复杂参数一律用 `--args` JSON
- `singleSelect / multipleSelect` 过滤时必须传 option ID，不是 option name

## 参考

- API 参考：`references/api-reference.md`
- 错误排查：`references/error-codes.md`
