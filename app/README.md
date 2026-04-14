# app 目录说明
作用：UI 展示与用户交互编排（窗口、表格、事件绑定）。输入：用户操作与 `core` 回调数据；输出：界面状态更新与启动/管理指令。  
关键文件：`main_window.py`、`styles.py`、`components/`。

补充：`Keywords` 面板现新增 `Tag` 列，用于展示每个关键词的类型（`dc/gtag/meta/ttd/taboola/applier`）。
补充：`Keywords` 表格列顺序已调整为 `# | Lang | Tag | Text1 | Text2 | ID | Status`：`Text1` 展示辅助关键词（如 `dc.type`、`gtag.conversion_id`、`meta.id`、`ttd/taboola.account_id`、`applier.action_id`），`Text2` 展示主关键词（如 `dc.cat`、`gtag.snippet`、`meta.ev`、`ttd.ct`、`taboola.en`、`applier.track_id`）。Applier 的匹配仅使用 `action_id + track_id`。状态更新逻辑已对应 `Status` 列。
补充：配置栏已移除 `Config Excel` 计数文案，顶部空间优先留给 `Task Name` 输入框以显示更长任务名称。
补充：配置栏新增 `Login Management` 按钮，可弹窗维护网页登录 `ID/Password` 并保存为全局凭证。
补充：`Keywords` 已不再提供手动管理弹窗，关键词来源统一为 Excel 读入结果。
补充：`URL Manager` 已改为 URL 样式管理：可选择/增删 `pws/cms` title 与 `tc/sc/en` 语言片段，全局持久化；支持一键恢复默认样式；预览窗格会实时刷新全部 URL，保存后回写当前任务 URL 列表。
补充：`Keywords` 面板会按各列当前最长字符串自动扩展列宽，并将左右分栏默认向右移动，优先保证左侧列内容完整可见。
补充：证据截图生成阶段会同步切换顶部 URL 选择框到当前关键词所属 URL，确保截图上下文一致。
补充：证据截图在 macOS 下会先做录屏权限预检；若权限未生效会提示用户重开应用，并自动回退为仅保留网页截图，避免流程中断。
补充：导出时会复制输入 Excel 作为结果文件，保留原始 sheet 不变；新增 `Test Result`（首页副本）回填 B-G 测试结果并在 `AC` 起始列写证据，且在其前新增总览页 `Summary`。
补充：关键词结果对齐与报告写入已下沉到 `core`（`core.report_alignment`、`core.reporter`），`MainWindow` 仅做 UI 编排与调用，减少前端持有业务实现细节。
补充：证据截图中的关键词选择已改为“按关键词行索引逐项选择”，避免同名关键词场景下的重复选中与漏选。
补充：`Network Requests` 的 `Name` 列显示日志全名，超出可视长度时以省略号显示。
补充：点击已选中的关键词行会取消选择并恢复显示全部日志。
补充：`Network Requests` 新增文本过滤输入框，可按输入文本筛选日志。
补充：点击某条日志可弹出详情框查看该日志全文。
补充：自动流程（证据截图阶段）选中关键词时会优先将该行滚动到窗格中间显示；手动点击关键词时保持原生行为，不做额外滚动干预。
补充：关键词过滤后的日志仅保留同一序号语言上下文（同 `num + lang`）的请求，不再额外做去重展示。
补充：为适配更密集的数据展示，主窗口尺寸、字体、表格行高与主要列宽已整体缩小，界面更紧凑。
补充：主界面左右分栏默认宽度已调整为 `Keywords` 约占窗口 `55%`，初始打开时优先保障关键词窗格可视区域。
补充：配置栏新增 `Mobile Emulation` 开关；开启后自动化会以移动端设备参数（触控 + 移动视口 + 移动端 UA）打开页面，便于复测移动版埋点行为。
