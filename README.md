# Game Sprite Extractor

> 从游戏截图中自动提取所有物件，去背景、方格排布，输出透明背景精灵表（Sprite Sheet）

## 🎯 功能

上传一张游戏画面截图，自动完成：
1. **背景检测** — 智能识别背景区域（支持纯色/渐变背景）
2. **物件分割** — 找出画面中所有独立物件（角色、道具、UI元素等）
3. **去背景** — 生成带透明通道的 RGBA PNG
4. **方格排布** — 按面积排序，自动计算最优网格布局

输出可直接用于 Godot、Unity、Phaser、Cocos 等游戏引擎。

## 🖼️ 效果

```
输入: game_screenshot.png (400x300, 蓝色背景 + 4个物件)

输出: game_screenshot_sheet.png (627x218, 透明背景, 4个物件方格排布)

┌──────────┬──────────┬──────────┐
│ 白色长条  │ 绿色方块  │ 黄色三角  │
├──────────┼──────────┼──────────┤
│ 红色圆形  │          │          │
└──────────┴──────────┴──────────┘
```

## 🚀 快速开始

### 安装

```bash
# 依赖: Python 3 + Pillow
pip install Pillow
```

### 基本用法

```bash
# 最简调用
python3 scripts/extract_sprites.py screenshot.png

# 指定输出路径
python3 scripts/extract_sprites.py screenshot.png output_sheet.png

# 同时导出每个物件为单独文件
python3 scripts/extract_sprites.py screenshot.png --extract-dir ./sprites/
```

### 参数调优

```bash
# 像素风游戏（低容差 + 小物件）
python3 scripts/extract_sprites.py game.png --tolerance 10 --min-size 50 --padding 2

# 高清手游（高容差 + 合并碎片）
python3 scripts/extract_sprites.py game.png --tolerance 40 --merge-gap 12 --min-size 200

# 动画帧提取（单列竖排）
python3 scripts/extract_sprites.py frames.png --max-cols 1 --padding 0

# 纯色背景（dominant 方法更快）
python3 scripts/extract_sprites.py screenshot.png --method dominant
```

## ⚙️ 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--tolerance` | 30 | 背景色容差 (0-255)。太大可能吃掉物件边缘，太小可能漏掉背景 |
| `--min-size` | 100 | 最小物件面积(像素)，过滤噪点 |
| `--padding` | 4 | 物件间透明间距(像素) |
| `--max-cols` | 0 | 最大列数 (0=自动，1=单列竖排) |
| `--merge-gap` | 8 | 合并近邻物件间距(像素)，解决物件被切碎问题 |
| `--method` | floodfill | 背景检测方法: `floodfill` / `dominant` |
| `--extract-dir` | — | 同时输出单独物件到此目录 |
| `--sort-by` | area | 排序方式: `area`(面积) / `height`(高度) |

## 🎮 引擎适配

| 引擎 | 导入方式 |
|------|---------|
| **Godot** | Texture2D → AtlasTexture / SpriteFrames 切片 |
| **Unity** | Sprite (Multiple) → Sprite Editor 自动切图 |
| **Phaser** | `this.load.spritesheet()` 加载 |
| **Cocos** | SpriteFrame，设置 Grid 切图参数 |
| **Unreal** | Paper2D → Flipbook / TileSet |

输出格式直接兼容：Texture、Sprite、UI Texture、UI Sprite、Icon、Button、Background、Tileset、Layer、Character Sprite、Animation Frame、Flipbook、Particle Texture、Effect Sprite。

## 📖 技术原理

### 背景检测

采用 **Flood Fill 泛洪填充算法**，从图片四边开始，将颜色相近的连通区域标记为背景。对渐变背景和轻微光照变化有良好容错。

### 物件分割

对非背景区域进行 4-邻域连通分量分析，过滤过小的噪点，智能合并被背景色切碎的近邻物件。

### 打包排布

按物件面积从大到小排序，自动计算接近正方形的网格布局。每个物件在其格子内居中放置，格子间留透明间距。

## 📁 文件结构

```
game-sprite-extractor/
├── scripts/
│   └── extract_sprites.py      # 核心提取脚本
└── references/
    └── params_guide.md         # 参数调优详细指南
```

## 📄 License

MIT
