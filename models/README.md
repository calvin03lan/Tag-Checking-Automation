# models 目录说明
作用：定义系统数据结构与基础常量，作为模块间统一协议。输入：外部配置与运行中状态；输出：类型安全的数据对象（URL/Keyword/ReportEntry/Session）。  
关键文件：`session.py`、`config.py`。  
说明：`config.py` 包含全局语言兼容映射常量（`LANG_COMPAT_MAP`），用于统一将多种语言缩写归一化为 `tc/sc/en`。输出目录根路径（`OUTPUT_BASE_ROOT`）已改为通过 `utils.platform_runtime` 按系统动态决策（macOS/Windows/Linux），避免将固定路径规则写死在模型层。`KeywordItem` 包含 `tag_type`（`dc/gtag/meta/ttd/taboola/applier/other`）用于前端展示，并包含 `secondary_text/tertiary_text` 支持多条件匹配（如 `dc: type+cat`、`gtag: conversion_id+snippet`、`meta: pixel_id+ev`、`ttd: account_id+ct`、`taboola: account_id+en`、`applier: action_id+track_id`）。`UrlItem` 包含 `url_path/url_kind` 元信息（`pws/cms/legacy`）用于 URL 管理组件按样式实时重建完整 URL。`KeywordItem/ReportEntry` 均带有 `tag_vendor/source_row` 元信息用于按新模板原始行序导出报告。
