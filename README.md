# Desktop Organizer - AI桌面智能整理器

一个基于AI的Windows桌面文件智能整理工具，帮助用户自动分类、整理和管理桌面文件。

## 功能特性

- 🔍 **智能扫描** - 递归扫描桌面文件，0.4秒完成800+文件分析
- 📂 **自动分类** - 8种文件类型自动识别（CAD/Office/图片/代码等）
- 🎯 **项目识别** - 自动识别项目编号（P019/TAC28等），匹配现有文件夹体系
- 🔄 **重复检测** - 智能发现重复文件和相似文件
- 🗑️ **临时清理** - 自动识别临时文件（.bak/.err/Hash命名文件）
- ✨ **AI分析** - 调用GPT-5.4-mini进行智能分类（可选）
- 📊 **组织预览** - 一键预览整理方案，支持撤销
- 🎨 **高级UI** - Linear.app风格暗色主题

## 技术栈

- Python 3.11+
- PyQt6 (GUI框架)
- PyInstaller (打包exe)
- OpenAI API (AI分类，可选)

## 快速开始

### 方式1: 直接运行exe
下载 `DesktopOrganizer.exe` 双击运行，无需安装Python。

### 方式2: 源码运行
```bash
pip install PyQt6
python main.py
```

### 方式3: 打包exe
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name DesktopOrganizer --add-data "config.json;." main.py
```

## 项目结构

```
desktop-organizer/
├── main.py              # 入口文件
├── config.json          # 配置文件
├── requirements.txt     # 依赖
├── src/
│   ├── scanner.py       # 桌面扫描器
│   ├── analyzer.py      # 文件分析器
│   ├── folder_suggester.py  # 智能文件夹建议
│   ├── ai_classifier.py # AI分类引擎
│   ├── organizer.py     # 整理执行器
│   ├── models.py        # 数据模型
│   ├── utils.py         # 工具函数
│   └── gui/
│       ├── main_window.py   # 主窗口
│       └── widgets.py       # 自定义组件
└── dist/
    └── DesktopOrganizer.exe  # 打包后的exe
```

## 配置说明

编辑 `config.json` 自定义：

```json
{
  "desktop_path": "C:\\Users\\ww\\Desktop",
  "max_depth": 3,
  "category_rules": {
    "CAD": [".dwg", ".stp", ".sldprt"],
    "Office": [".xlsx", ".docx", ".pdf"],
    "Images": [".png", ".jpg"],
    "Code": [".py", ".js", ".ts"]
  },
  "folder_mappings": {
    "CAD": "04_图纸_3D_研发",
    "Office": "01_东宝龙制造工作",
    "Images": "07_图片视频素材",
    "Code": "06_AI_Codex_自用应用"
  }
}
```

## 性能指标

| 指标 | 数值 |
|------|------|
| 扫描812文件 | 0.4秒 |
| 分析812文件 | 0.012秒 |
| 内存占用 | 44KB |
| 中文文件名 | 86个全部正确处理 |

## License

MIT
