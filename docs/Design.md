# 设计文档：Tag Checking Automation Tool（当前实现版）

## 1. 目标与范围

该工具用于多语言页面标签验证，面向 QA/运营；核心目标是自动化浏览器验证、实时网络日志可视化、以及按关键词输出可追溯证据。

主要能力：
1. 从 Excel（`URLs`/`Keywords`）读取测试配置；
2. 串行访问 URL，按当前页面 `num+lang` 规则执行按钮点击；
3. 实时显示 Network（Name/Type/Status/Time），支持按关键词过滤；
4. 生成“每个关键词一行”的 Excel 报告，并附对应证据截图。

---

## 2. 关键设计原则

1. **解耦**：`app/` 只负责展示，`core/` 负责业务编排，`utils/` 负责 I/O 与图像处理。
2. **线程安全 UI 更新**：自动化线程通过回调 + `root.after` 更新界面。
3. **可追溯证据**：每个关键词输出独立截图，截图显示该关键词过滤后的日志。
4. **可扩展过滤能力**：过滤逻辑独立在 `core/network_filter.py`，可被其他模块复用。

---

## 3. 配置输入与数据模型

### 3.1 Excel 输入格式

- Sheet `URLs`：`num | lang | url`
- Sheet `Keywords`：`num | lang | text | button_name`
- `num` 保留 Excel 原值，不做自动重编号。

### 3.2 核心模型（`models/session.py`）

- `UrlItem`：`url, lang, num, status`
- `KeywordItem`：`num, lang, text, button_name`
- `ReportEntry`（每条 keyword 一行）：  
  `url_index, url, url_lang, kw_num, kw_text, kw_lang, kw_button, result, tested_at, screenshot_path`

---

## 4. 自动化执行流程（Start 到报告输出）

### 4.1 总体流程

1. 用户点击 `Start`；
2. 创建 workspace，清空 Network 面板，重置关键词状态；
3. 启动后台线程，运行 `BrowserAutomation.run(...)`；
4. 逐 URL 串行执行 `_process_url(...)`；
5. 汇总 `ReportEntry`，写入 Excel。

### 4.2 单 URL 流程（当前规则）

1. 打开 URL（`domcontentloaded`）；
2. 读取当前页面匹配关键词：`kw.num == url.num && kw.lang == url.lang`；
3. 提取去重 `button_id`；
4. 等日志“防抖倒计时”归零（500ms无新日志）；
5. 每隔 2 秒执行一次 Cmd/Ctrl+Click（新标签打开），并关闭额外标签；
6. 每次点击后继续等待防抖倒计时归零，再进行下一次点击；
7. 网络稳定后进行网页快照；
8. 依次切换每个页面关键词的 filter，逐条截图取证；
9. 按关键词写报告行（PASS/FAILED + 对应截图路径）。

### 4.3 PASS 判定

- 判定键为 `(num, lang, text)`；
- 当该键在当前页面网络请求中出现至少一次匹配请求，即 `PASS`；
- 否则 `FAILED`。

---

## 5. 日志与过滤设计

### 5.1 Network 实时展示

- 列：`Name | Type | Status | Time`
- 响应到达即追加、即滚动；
- 匹配请求高亮为绿色，错误状态码（>=400）红色显示。

### 5.2 Filter 机制（独立模块）

`core/network_filter.py` 提供：
- `KeywordIdentity(num, lang, name)`
- `NetworkEvent(...)`
- `filter_events_for_keyword(...)`
- `trigger_keyword_filter(..., on_filtered=...)`

UI 在关键词选中事件中调用 `trigger_keyword_filter`，右侧只渲染当前关键词匹配日志。

---

## 6. 截图证据流程

1. 先截图网页（浏览器前置）；
2. 对当前页面的每个关键词：
   - 触发关键词过滤；
   - 应用窗口置顶（逐张执行 `topmost=True -> update -> wait -> grab -> topmost=False`）；
   - 截应用窗体；
   - 与网页图做左右拼图（左应用、右网页）；
3. 每个关键词生成独立证据图并回写到对应 `ReportEntry`。

---

## 7. 报告输出

`core/reporter.py` 输出 `.xlsx`，每个关键词一行：

`URL # | URL | URL Lang | KW # | Keyword | KW Lang | ID | Result | Tested At | Screenshot`

- `Result` 列按 PASS/FAILED 上色；
- `Screenshot` 列嵌入该关键词对应证据图；
- 仅对当前 URL 的 `num+lang` 关键词写入行，避免跨页面混写。

---

## 8. 当前目录结构（摘要）

```text
Tag_Checking_Automation/
├── main.py
├── app/        # UI层
├── core/       # 自动化、分析、过滤、报告
├── models/     # 数据结构与常量
├── utils/      # 配置I/O、文件系统、图像处理
├── tests/      # 单元测试
└── docs/       # 设计与测试说明
```
