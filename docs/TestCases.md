# 测试用例说明文档（当前版本）

## 概述

当前自动化测试位于 `tests/`，总计 **71** 条单元测试，命令如下：

```bash
cd Tag_Checking_Automation
source .venv/bin/activate
pytest tests/ -q
```

测试边界：
- 覆盖 `core/`、`utils/`、`models/` 的纯逻辑与文件处理；
- UI（`app/`）与真实浏览器执行（`core/automation.py`）主要靠人工集成测试。

---

## 1. `core/tag_analyzer.py`

**测试文件**：`tests/test_tag_analyzer.py`（14条）

覆盖点：
- `matches()`：关键词命中、未命中、空关键词、大小写场景；
- `analyze_requests()`：单命中/多命中/全不命中/空输入；
- `keyword_statuses()`：按关键词输出布尔命中映射。

---

## 2. `models/session.py`

**测试文件**：`tests/test_session.py`（11条）

覆盖点：
- `UrlItem` 默认状态、字段赋值；
- `UrlStatus` 枚举值与字符串兼容性；
- `ReportEntry`（每关键词一行）字段完整性与默认值；
- `Session` 默认集合独立性（防 mutable default 共享）。

---

## 3. `utils/file_system.py`

**测试文件**：`tests/test_file_system.py`（10条）

覆盖点：
- `create_workspace()`：目录创建、幂等、空名异常；
- `cleanup_dir()`：删除目录与不存在目录容错；
- `save_json()/load_json()`：读写往返与父目录自动创建。

---

## 4. `utils/config_io.py`

**测试文件**：`tests/test_config_io.py`（13条）

覆盖点：
- `load_excel_config()`：`URLs/Keywords` 双 sheet 解析、字段映射、空行跳过、缺sheet异常；
- `num` 保持原值（不重编号）；
- `convert_excel_to_json_data()` 兼容旧格式读取。

---

## 5. `utils/image_processor.py`

**测试文件**：`tests/test_image_processor.py`（7条）

覆盖点：
- 纵向拼接 `stitch_images()` 输出尺寸、路径、异常；
- 横向拼接 `stitch_side_by_side()` 由业务流程使用（集成验证为主）；
- 输出目录自动创建。

---

## 6. `core/reporter.py`

**测试文件**：`tests/test_reporter.py`（11条）

覆盖点：
- 报告文件创建与绝对路径返回；
- 新表头字段（URL/KW 双维度）顺序与内容；
- 语言标签映射（URL Lang / KW Lang）；
- 缺图写 `N/A`、有图嵌入不抛错；
- 每条关键词单独成行写入。

---

## 7. `core/network_filter.py`

**测试文件**：`tests/test_network_filter.py`（3条）

覆盖点：
- 三元组 `(num,lang,name)` 精确过滤；
- 无匹配返回空；
- `trigger_keyword_filter()` 能回调输出过滤结果。

---

## 8. 未纳入自动化测试（需人工）

| 模块 | 原因 | 建议验证 |
|---|---|---|
| `app/main_window.py` | 依赖 tkinter 事件循环与桌面窗口 | 启动后检查关键词筛选、日志滚动、置顶截图 |
| `core/automation.py` | 依赖 Playwright + 真实网络请求 | 真实 URL 跑通：打开、点击、稳定等待、切页、报告输出 |

人工冒烟流程建议：
1. 导入含多 URL / 多关键词 Excel；
2. 点击 Start，观察 Network “即到即显即滚动”；
3. 验证关键词 filter、PASS/FAILED、截图数量与报告行数一致。
