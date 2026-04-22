# utils 目录说明
作用：通用工具与 I/O 适配层，不含业务策略。输入：文件路径/图像路径/原始配置文件；输出：解析后的模型数据、工作目录、拼接后的图片。  
关键文件：`excel_config_adapter.py`、`config_io.py`、`file_system.py`、`image_processor.py`。  
说明：Excel 读取与模型转换由 `excel_config_adapter.py` 统一负责，语言兼容映射使用 `models/config.py` 的全局常量 `LANG_COMPAT_MAP`（含 `tc/chi/zh-hk/zh-tw`、`sc/schi/zh-cn/zh-hans`、`en/eng/en-hk/en-us/en-gb` 等）。

## URL 样式全局选项
- `url_style_options.py` 负责 URL title / language segment / cms suffix 的全局选项持久化（跨任务复用）。
- 选项支持 `pws/cms` 分别配置，并可针对 `tc/sc/en` 独立设置语言片段；`cms` 额外支持可配置后缀（默认 `/index.html`）。
- `cms` 后缀支持两种形态：以 `/` 开头的路径后缀（如 `/index.html`）与以 `.` 开头的扩展后缀（如 `.html`，将拼成 `.../chi.html`，不会额外插入 `/`）。
- 提供 URL 重建函数与批量应用函数，供 URL 管理组件实时刷新预览和保存结果。

## 平台运行时适配
- `platform_runtime.py` 统一封装系统差异（macOS / Windows / Linux）：
  - 默认输出根目录（`Tag_QA_Files`）的系统级路径决策；
  - 系统 Chrome 路径候选与自动探测；
  - 浏览器新标签点击修饰键（`Meta/Control`）；
  - macOS 录屏权限重置提示命令（`tccutil reset ScreenCapture`）。
- 业务层不再直接写 `sys.platform` 分支，改为调用该模块以减少平台耦合。

## 登录凭证全局选项
- `login_credentials.py` 负责网页登录凭证（`username/password`）的全局持久化（跨任务复用）。
- 默认凭证：`depaemuser` / `Pr0t8ctd8pa8mus8r`；支持通过弹窗修改并保存。

## macOS 录屏权限辅助
- `screen_capture_permission.py` 封装 macOS `CGPreflightScreenCaptureAccess/CGRequestScreenCaptureAccess`。
- 用于截图前预检与触发系统授权，避免打包应用在证据截图阶段因权限未生效而直接失败。

## 新旧模板自动识别
- 当工作簿**恰好**由两个 sheet（`URLs`、`Keywords`）组成时，按旧模板解析。
- 其他情况自动走新模板解析（`new_template_adapter.py`），基于第 3 行表头模糊匹配列名。
- 新模板解析为端到端内存转换：直接产出 `UrlItem` / `KeywordItem`，不生成中间旧 Excel 文件。
- 新模板已取消 `K/L/P`（Language + URL path + Button ID）重复拦截：同键重复行不会报错，读取阶段按规则继续合并 URL 并累积关键词。
- 新模板 URL 读取遵循新规：L 列视为 `URL path name` 片段而非完整 URL；`/cms` 走 cms 规则，其余走 pws 规则。
- URL 拼接默认规则：`pws = https://www.hangseng.com + lang + path`；`cms = https://cms.hangseng.com + path + lang + suffix`（默认后缀 `/index.html`，可在 URL Manager 中切换）。
- 语言列支持 `(All)`：单行会扩展为 `tc/sc/en` 三条 URL 与三条关键词记录。
- 新模板 URL 构建会复用 `url_style_options.py` 的当前选中样式值，便于和 URL 管理的全局配置保持一致。
- 新模板中 `Gtag Event snippet` 会按 `/` 拆分为 `conversion_id` 与 `snippet(label)`，分别写入 `KeywordItem.secondary_text` 与 `KeywordItem.text`。
- 新模板中 `DoubleClick` 会同时读取 `type(Group Tag String)` 与 `cat(Activity Tag String)`；`Meta` 会同时读取 `Master Pixel ID` 与 `EV value`。
- 新模板中 `The Trade Desk` 会同时读取 `Account ID(V)` 与 `CT value(W)`；`Taboola` 会同时读取 `Account ID(X)` 与 `EN value(Y)`。
- 新模板中 `Applier` 读取 `action_id(AA)` 与 `track_id(AB)` 两项，`type(Z)` 不再参与读入与匹配。
- 新模板解析时会标记关键词类型：`doubleclick->dc`、`gtag->gtag`、`meta->meta`、`ttd->ttd`、`taboola->taboola`、`applier->applier`。
- 新模板解析时会保留关键词来源 `tag_vendor` 与 `source_row`，用于新增报告 sheet 按输入原始行序输出。
