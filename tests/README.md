# tests 目录说明
作用：单元测试集合，用于验证核心逻辑、I/O 解析与报告输出的正确性。输入：pytest 执行与临时测试数据；输出：通过/失败结果与回归保护。  
关键文件：`test_*.py`（当前 113 条测试）。

## 配置读取覆盖点
- `test_config_io.py` 已覆盖旧模板（`URLs` + `Keywords`）读取。
- 已覆盖新模板自动回退解析（非旧模板双 sheet 时自动启用）。
- 已覆盖新模板重复键策略：`K/L/P` 复合键重复不报错，解析阶段允许同键多行输入并继续产出关键词。
- 已覆盖新模板 URL 新规：`pws/cms` 两种拼接格式与默认域名规则。
- 已覆盖语言 `(All)` 行自动拆分为 `tc/sc/en` 三条 URL 与关键词记录。
- 已覆盖全局 URL 样式选项的存储与应用（title/语言片段/cms后缀选择、URL重建、legacy URL 保持不变）。
- 已覆盖 CMS 后缀两种拼接形态：`/index.html` 路径后缀与 `.html` 扩展后缀（扩展后缀不追加多余 `/`）。
- 已覆盖新模板 `Gtag` 关键词拆分规则（`conversion_id/snippet`），并校验 `secondary_text` 读入。
- 已覆盖新模板 `DoubleClick(type+cat)`、`Meta(master pixel id+ev)`、`The Trade Desk(account+ct)`、`Taboola(account+en)` 的多关键词读入。
- 已覆盖新模板 `Applier(action_id+track_id)` 两关键词读入（`type` 不参与）。
- 已覆盖关键词类型标记（`dc/gtag/meta/ttd/taboola/applier`）。
- `test_tag_analyzer.py` 已覆盖参数匹配规则：`dc->type+cat`、`gtag->conversion_id+label`、`meta->id+ev`、`ttd->account+ct`、`taboola->account+en`、`applier->action_id+track_id`，以及其他类型的 URL 包含匹配。
- `test_reporter.py` 已覆盖新增 `New Template Report` sheet 的 12 列结构与按 `source_row` 排序行为。
- `test_reporter.py` 已覆盖“复制输入文件后保留原 sheet 不变、新增 `Test Result` 回填 B-G + 在 `AC` 起始列写入证据区，并在其前新增总览页 `Summary`”的导出模式。
- 已覆盖总览页 `Summary` 的固定文案（A1/A2/A3）、日期格式（`yyyy/mm/dd`）与全通过状态文案（`All PASS`）。
- 已覆盖 `Test Result` 页第 3 行证据表头（左右居中+上下靠下）、证据图片列宽（51）与证据行高（90）。
- 已覆盖 B-G 与证据区结果列（AC 起）`PASS/FAILED` 的一致样式（红/绿底、加粗、上下左右居中）。
- 已覆盖 `Summary` 证据图片尺寸与单元格尺寸一致（宽=证据列宽换算像素，高=行高换算像素）。
- 已覆盖语言为 `all/(all)` 时在该行下方自动插入 2 行，并按三语言展开证据写入。
- 已覆盖 `ReportWriter.write_into_input_copy()` 门面行为，避免 UI 直接依赖底层 `ExcelReportExporter` 实现。
- 已覆盖 `core.report_alignment.align_entries_to_keywords()` 的对齐规则（重复 key 顺序消费、缺失项回填 `None`）。
