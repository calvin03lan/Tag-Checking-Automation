# 目录说明
本目录是项目入口与集成层，负责启动程序并连接 UI、自动化、报告输出。输入：Excel 配置与用户操作；输出：运行日志、截图证据、Excel 报告。  
关键文件：`main.py`、`requirements.txt`。

## 目录总览索引表
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

## Demo：新模板映射为旧格式
- 脚本：`demo_new_excel_to_legacy.py`
- 目标：将客户新 Excel 模板转换为旧读取逻辑所需的双 Sheet 格式：`URLs`、`Keywords`
- 转换规则基于 `读入描述.md`，并包含：
	- `K/L/P` 复合主键去重校验（重复时报错）
	- `B-G` 的 `Required` 开关控制关键词导入
	- 关键词主值列映射：`B->R, C->S, D->U, E->W, F->Y, G->AB`
	- 第 3 行表头采用模糊匹配定位列（支持换行与备注文本，不依赖精确表头）

### 运行示例
```bash
# 生成一份演示新模板并转换为旧格式
python demo_new_excel_to_legacy.py --make-demo-input --output demo_legacy_config.xlsx

# 使用真实新模板文件进行转换
python demo_new_excel_to_legacy.py --input /path/to/new_template.xlsx --output /path/to/legacy_config.xlsx
```

## 打包（macOS）
- 脚本：`build.sh`
- 功能：使用 `.venv` 中的 PyInstaller 执行 `onedir + windowed` 打包，并固定 Bundle ID（用于更稳定的系统权限识别）。

```bash
# 在项目根目录执行
./build.sh
```

产物位置：
- `dist/Tag_Checking_Automation.app`（可直接双击）
- `dist/Tag_Checking_Automation/`（onedir 目录）
