# Tag Checking Automation

Tag Checking Automation is a desktop QA tool for validating tracking tags across multilingual web pages.  
It reads Excel-based test configurations, runs browser automation, captures network requests in real time, and generates evidence-backed Excel reports.

## Core Capabilities

- Load both legacy (`URLs` + `Keywords`) and new single-sheet Excel templates.
- Execute page/event validation with per-URL/per-language keyword scoping.
- Show live network logs and keyword-filtered matches in the UI.
- Export results to a copy of the input workbook with screenshots and summary.
- Support global URL style management (PWS/CMS title, language segment, and CMS suffix).
- Support mobile emulation mode (`Mobile Emulation`) with isolated incognito session.

## Project Index

| Directory | Description |
|---|---|
| `app/` | UI layer and interaction orchestration ([`app/README.md`](app/README.md)) |
| `app/components/` | Reusable dialogs (`URL Manager`, `Login Management`) ([`app/components/README.md`](app/components/README.md)) |
| `core/` | Automation, matching, filtering, reporting ([`core/README.md`](core/README.md)) |
| `models/` | Shared models and configuration constants ([`models/README.md`](models/README.md)) |
| `utils/` | I/O adapters and utility helpers ([`utils/README.md`](utils/README.md)) |
| `tests/` | Unit test suite and coverage notes ([`tests/README.md`](tests/README.md)) |
| `docs/` | Design and test documentation ([`docs/README.md`](docs/README.md)) |
| `examples/` | Example Excel files for manual validation ([`examples/README.md`](examples/README.md)) |

## Run Locally

```bash
python main.py
```

## Build (macOS)

- Script: `build.sh`
- Purpose: package the app with PyInstaller (`onedir + windowed`) and a stable bundle identifier.

```bash
./build.sh
```

Build outputs:

- `dist/Tag_Checking_Automation.app`
- `dist/Tag_Checking_Automation/`

## Notes for New Template Parsing

- New template parsing is now in-memory and no longer depends on a conversion script.
- `K/L/P` duplicate rows are allowed (no blocking validation error).
- CMS URL generation uses configurable suffixes (for example `/index.html` or `.html`).

---

# Tag Checking Automation（中文说明）

Tag Checking Automation 是一个用于多语言网页埋点验证的桌面 QA 工具。  
它可读取 Excel 配置、执行浏览器自动化、实时采集网络请求，并输出带截图证据的 Excel 报告。

## 主要能力

- 支持旧模板（`URLs` + `Keywords`）和新单表模板自动识别与读取。
- 按 URL 与语言维度执行 page/event 关键词检测。
- 主界面实时展示网络请求并支持关键词过滤查看命中。
- 输出输入文件副本并回填结果、证据截图和总览页。
- 支持全局 URL 样式管理（PWS/CMS 的 title、语言片段、CMS 后缀）。
- 支持移动端模拟（`Mobile Emulation`），以独立无痕会话运行。

## 目录索引

| 目录 | 说明文档 |
|---|---|
| `app/` | [`app/README.md`](app/README.md) |
| `app/components/` | [`app/components/README.md`](app/components/README.md) |
| `core/` | [`core/README.md`](core/README.md) |
| `models/` | [`models/README.md`](models/README.md) |
| `utils/` | [`utils/README.md`](utils/README.md) |
| `tests/` | [`tests/README.md`](tests/README.md) |
| `docs/` | [`docs/README.md`](docs/README.md) |
| `examples/` | [`examples/README.md`](examples/README.md) |

## 本地运行

```bash
python main.py
```

## macOS 打包

```bash
./build.sh
```

产物：

- `dist/Tag_Checking_Automation.app`
- `dist/Tag_Checking_Automation/`

## 新模板说明（当前实现）

- 新模板已改为内存解析，不再依赖额外转换脚本。
- `K/L/P` 重复行已允许，不再阻断读入。
- CMS URL 后缀可配置（如 `/index.html`、`.html`）。
