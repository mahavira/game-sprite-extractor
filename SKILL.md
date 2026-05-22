---
name: game-sprite-extractor
description: |
  游戏精灵提取器。当用户上传游戏画面截图，要求提取图片中的所有物件/素材，去除背景，
  以方格排布输出透明背景精灵表（Sprite Sheet）时触发。输出的精灵表可直接用于游戏引擎
  的 Texture、Sprite、UI Texture、UI Sprite、Icon、Button、Background、Tileset、
  Layer、Character Sprite、Animation Frame、Flipbook、Particle Texture、Effect Sprite。
  触发词：提取素材、提取精灵、精灵表、sprite sheet、提取物件、去背景排布、游戏素材提取、
  纹理提取、tileset 生成、spritesheet。
agent_created: true
---

# Game Sprite Extractor — 游戏精灵提取器

## 概述

从游戏画面截图中自动检测所有物件（角色、道具、UI 元素等），去除背景生成透明 PNG，
并以方格方式排布为单张精灵表（Sprite Sheet），可直接导入 Godot、Unity、Phaser、
Cocos 等游戏引擎使用。

## 触发条件

当用户上传图片并表达以下意图之一时触发:
- "提取这张图中的所有素材/物件"
- "生成精灵表/sprite sheet"
- "帮我去背景、排布成方格"
- "把游戏截图里的素材都抠出来"
- "做成 tileset/纹理贴图"

## 工作流程

### 步骤 1: 确认输入与参数

先确认:
- 图片文件路径（用户上传的截图）
- 是否需要调整参数（如果图片效果不佳再调整）

默认参数适用于大多数情况。如果用户未指定，直接使用默认值执行。

### 步骤 2: 运行提取脚本

使用 `scripts/extract_sprites.py`:

```bash
python3 scripts/extract_sprites.py <输入图片路径> [输出路径] [选项]
```

**默认调用 (推荐):**
```bash
python3 scripts/extract_sprites.py screenshot.png
```
输出文件自动命名为 `screenshot_sheet.png`，保存在同目录。

**如果用户需要单独查看每个物件:**
```bash
python3 scripts/extract_sprites.py screenshot.png --extract-dir ./extracted/
```

### 步骤 3: 根据效果调整参数

如果用户反馈效果不理想（物件未检测到 / 背景残留 / 物件被切碎），按优先级调整:

| 问题 | 调整方式 |
|------|---------|
| 物件没检测到 | 降低 `--tolerance` (默认30, 试试 10-20) |
| 背景被当作物件 | 提高 `--tolerance` (试试 40-60) |
| 大物件被切成碎片 | 提高 `--merge-gap` (默认8, 试试 15-25) |
| 太多噪点 | 提高 `--min-size` (默认100, 试试 300-500) |
| 物件太挤 | 提高 `--padding` (默认4, 试试 8-16) |
| 纯色背景但 floodfill 不好使 | 用 `--method dominant` |
| 需要竖排 | 用 `--max-cols 1` |

详细参数说明见 `references/params_guide.md`。

### 步骤 4: 呈现结果

提取完成后:
1. 用 Read 工具查看输出图片确认效果
2. 向用户报告：物件数量、精灵表尺寸
3. 如果效果不理想，根据步骤 3 调整参数重新运行
4. 将精灵表交付给用户

## 输出特性

- **格式**: RGBA PNG，透明背景
- **排布**: 方格网格，物件在各自格子内居中
- **排序**: 按面积从大到小，大物件优先放置
- **无网格线**: 物件之间只有透明间距 (padding)，不绘制任何线条

## 适配的游戏引擎用途

| 引擎 | 用法 |
|------|------|
| Godot | 导入为 Texture2D → 配合 AtlasTexture / SpriteFrames 使用 |
| Unity | 导入为 Sprite (Multiple) → Sprite Editor 切片 |
| Phaser | `this.load.spritesheet()` 加载 |
| Cocos | 导入为 SpriteFrame，设置切图参数 |

## 依赖

需要 Python 3 + Pillow:
```bash
pip install Pillow
```
