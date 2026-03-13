# core 目录说明
作用：核心执行与业务逻辑（自动化流程、匹配分析、过滤、报告生成）。输入：`models` 数据对象与配置；输出：网络事件、状态结果、`ReportEntry` 与 Excel 文件。  
关键文件：`automation.py`、`tag_analyzer.py`、`network_filter.py`、`reporter.py`、`report_alignment.py`。

补充：`automation.py` 的网络回调中，`Name` 字段输出去掉协议和域名后的请求主串（保留 path 参数与 query），可正确展示 DoubleClick 的 `activityi;...;cat=...` 形式。
补充：关键词命中统计已前移到 `request` 阶段（请求发出即计入），并保留 `response` 阶段日志补充状态码与耗时，降低某些 beacon/异步请求在响应阶段缺失导致的漏检风险。
补充：浏览器上下文支持注入 `http_credentials`，当网页触发 Chrome 原生身份验证框时可自动使用前端保存的登录 `ID/Password` 完成认证。
补充：按钮点击前会在同一 `id` 的全部候选节点中优先选择“可见且可点击”的元素，避免多语言页面中因隐藏同 ID 节点导致误判“按钮不可见”而跳过。
补充：若严格按 `id` 查找不到元素，会自动启用模糊回退：在 `class/name/aria-label/title/文本` 等字段中按关键词匹配可点击节点，兼容“非标准按钮定义”页面。
补充：点击阶段若发生同标签页跳转（例如站点拦截 `Cmd/Ctrl+Click`），自动检测 URL 漂移并回跳到当前测试 URL，随后继续未完成按钮的点击流程。
补充：点击阶段会检测并尝试关闭阻塞型站内弹层（如 modal/drawer/overlay）：包含 `Esc`、关闭控件的类名/ID/文案模糊匹配（如 `close-btn`）与 backdrop 点击；关闭后继续执行未完成按钮，减少“页面被遮挡导致测试中断”。
补充：按钮点击改为启发式轮询：不会只跑固定顺序单轮，而是对未完成按钮做多轮扫描，某按钮一旦变为可见可点就立即执行；适配“先弹层后露出按钮”的动态页面行为。
补充：网络请求回调会附带当前页面上下文（`num/lang/url`）；前端关键词过滤可据此限制“仅同页面序号日志”，降低跨页同关键词造成的混淆。
补充：关键词匹配采用参数感知规则并支持多条件：`dc` 需同时匹配 `type + cat`（支持 query 与 DoubleClick 常见分号路径参数）、`gtag` 需同时匹配 `conversion_id + snippet(label)`、`meta` 需同时匹配 `Master Pixel ID(id) + EV value(ev)`、`ttd` 需同时匹配 `Account ID + CT value`、`taboola` 需同时匹配 `Account ID + EN value`、`applier` 需同时匹配 `action_id + track_id`；其余类型保持 URL 包含匹配。日志高亮与关键词结果判定使用同一套规则。
补充：`applier` 匹配规则已调整为仅校验 `action_id + track_id` 两项，不再要求 `type` 参与匹配。
补充：`excel_exporter.py` 中保留 `Tag QA Report` / `New Template Report` 的通用导出能力，但当前主流程默认不调用该路径。
补充：当前主流程默认使用“复制输入文件并回填”的导出方式：原始 sheet 保持不变，新增 `Test Result`（首页副本）并在其 B-G 回填 `PASS/FAILED`（`Not Required` 不改），证据区写入该页 `AC` 起始列；不再创建独立 `Evidence` sheet。
补充：在 `Test Result` 前新增总览页 `Summary`：A1=`Summary`、A2=`Latest Update`、A3=`Status`，B2 写当天日期（`yyyy/mm/dd`），当结果全部为 `PASS` 时，B3 写 `All PASS`（`PASS` 绿色加粗）。
补充：`Test Result` 的证据表头固定第 3 行，仅做加粗，左右居中、上下靠下；证据区图片列宽固定 `51`、证据行高固定 `90`，证据图片按单元格尺寸铺满（图片宽=证据列宽、图片高=行高对应像素）。
补充：`PASS/FAILED` 结果单元格在 B-G 与证据结果列保持一致样式（红/绿底、加粗、上下左右居中）；当语言列为 `all/(all)` 时，会在该行下方自动插入 2 行用于三语言证据展开。
补充：报告结果按关键词行对齐规则已抽离到 `report_alignment.py`，UI 层通过核心函数调用，不再在 `app` 中维护该业务算法。
