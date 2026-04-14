# app/components 目录说明
作用：可复用弹窗组件（URL 管理、登录凭证管理），不包含核心业务判定。输入：主窗口传入当前列表或凭证；输出：用户编辑后的结果（回调 `on_save`）。  
关键文件：`url_manager.py`、`login_manager.py`。

补充：`URL Manager` 已重构为“URL 样式管理”组件：
- 支持分别选择 `pws/cms` 的 URL title；
- 支持分别选择 `tc/sc/en` 的语言片段样式；
- 支持为 `cms` 配置 URL 后缀样式（默认 `/index.html`，可新增/删除并下拉切换）；
- 支持对上述选项做新增/删除，且持久化为全局后端选项（跨任务复用）；
- 支持一键“恢复默认样式”，将 title/语言片段配置重置为系统默认值；
- 保留 URL 预览窗格，并在选项变化时实时重建并刷新全部 URL。
- 点击 `Save` 或直接关闭弹窗（右上角 `X`）都会将当前预览 URL 回写到主窗口并刷新 URL 下拉框。

补充：`Login Management` 弹窗支持编辑并保存登录 `ID/Password`（默认值：`depaemuser` / `Pr0t8ctd8pa8mus8r`），并提供 `Show Password` 开关便于核对输入；保存后供自动化浏览器身份验证复用。
