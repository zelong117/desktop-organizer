# Desktop Organizer - AI 桌面智能整理器

一个 Windows 桌面文件整理工具，用 PyQt6 提供图形界面，支持扫描桌面文件、按类型分类、识别临时文件和项目文件，并生成整理预览。

## 功能

- 扫描当前用户桌面，统计文件、文件夹、大小和临时文件数量。
- 按 CAD、Office、图片、压缩包、代码、视频、音频、文本等规则自动分类。
- 识别重复文件候选和项目编号模式。
- 在图形界面中查看文件表格、文件详情、扫描进度和整理建议。
- 支持可选 AI 分类配置，未配置 API 时仍可使用本地规则分析。

## 运行环境

- 推荐：Windows + 系统 Python 3.12。
- GUI 依赖：PyQt6。
- Hermes 内置 Python 没有 `pip`，不适合直接安装 PyQt6 运行 GUI。请使用系统安装的 Python 3.12 来运行桌面程序。
- `config.json` 默认使用 `%USERPROFILE%\Desktop`，会随当前登录用户自动展开；留空时也会自动使用当前用户桌面。

## 源码运行

在项目根目录执行：

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
```

如果系统没有注册 `py -3.12`，可以直接使用 Python 3.12 的完整路径：

```powershell
C:\Path\To\Python312\python.exe -m pip install -r requirements.txt
C:\Path\To\Python312\python.exe main.py
```

## 配置说明

默认配置文件是 `config.json`。

```json
{
  "desktop_path": "%USERPROFILE%\\Desktop",
  "max_depth": 3,
  "skip_system_files": true
}
```

- `desktop_path`：默认 `%USERPROFILE%\\Desktop`，会自动适配当前 Windows 用户；留空也表示自动使用当前用户桌面。
- `max_depth`：递归扫描深度。
- `skip_system_files`：是否跳过 `desktop.ini`、`thumbs.db` 等系统文件。
- `category_rules`：文件扩展名分类规则。
- `folder_mappings`：整理建议使用的目标文件夹映射。

不要把固定用户名写进配置；跨机器使用时保留 `%USERPROFILE%\\Desktop` 或留空即可自动适配当前用户。

## 打包 exe

```powershell
py -3.12 -m pip install pyinstaller
py -3.12 -m PyInstaller --onefile --windowed --name DesktopOrganizer --add-data "config.json;." main.py
```

打包结果通常位于 `dist\DesktopOrganizer.exe`。

## 项目结构

```text
desktop-organizer/
├── main.py                  # 程序入口、配置加载、全局字体设置
├── config.json              # 扫描与分类配置
├── requirements.txt         # Python 依赖
├── src/
│   ├── scanner.py           # 桌面扫描器
│   ├── analyzer.py          # 文件分析器
│   ├── folder_suggester.py  # 文件夹建议
│   ├── ai_classifier.py     # 可选 AI 分类
│   ├── organizer.py         # 整理执行与预览逻辑
│   ├── models.py            # 数据模型
│   ├── utils.py             # 工具函数
│   └── gui/
│       ├── main_window.py   # 主窗口
│       └── widgets.py       # 自定义 PyQt6 组件
├── test_comprehensive.py
└── test_phase2.py
```

## 常见问题

**运行时报 `No module named PyQt6`**

确认使用的是系统 Python 3.12，并执行过：

```powershell
py -3.12 -m pip install -r requirements.txt
```

**Hermes Python 不能安装依赖**

Hermes 内置 Python 没有 `pip`，这是预期限制。GUI 程序请改用系统 Python 3.12。

**想扫描其他目录**

把 `config.json` 的 `desktop_path` 改成目标目录的绝对路径。恢复自动扫描当前用户桌面时，再改回 `%USERPROFILE%\\Desktop` 或空字符串。
