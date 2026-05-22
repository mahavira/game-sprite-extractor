# 参数调优指南

## 核心参数

### --tolerance (默认 30)
背景色容差值。范围 0-255，值越大越宽松地把相近颜色当背景。

- **值太小 (5-15)**: 只有与边缘颜色几乎完全相同的才被识别为背景。适用于背景非常均匀的截图。
- **值适中 (20-40)**: 适用于大多数游戏截图，能处理轻微渐变或光照变化。
- **值太大 (50-80)**: 可能把物件边缘也当作背景吃掉。仅当背景与物件颜色跨度很大时使用。

诊断:
- 物件没被检测到 → 降低 tolerance
- 物件边缘被侵蚀 → 提高 tolerance
- 大块背景被当成物件 → 提高 tolerance

### --min-size (默认 100)
最小物件像素面积。小于此值的连通分量被当作噪点丢弃。

- **100-200**: 保留小 UI 元素（按钮、图标）
- **300-500**: 只保留角色、大型物件
- **50 以下**: 保留粒子效果、小图标等

### --padding (默认 4)
精灵表中物件之间的透明间距（像素）。

- 太小 (1-2): 物件视觉上太挤，引擎切片时容易切到邻居
- 适中 (4-8): 标准间距
- 较大 (16-32): 如果物件有特效光晕需要额外空间

### --max-cols (默认 0=自动)
控制网格列数。
- 0: 自动计算，尽量接近正方形
- 1: 单列竖排（适合动画帧序列）
- 自定义数值: 按指定列数排布

### --method (默认 floodfill)
背景检测方法。

- **floodfill**: 从四边泛洪填充。适合大多数情况，能处理渐变背景。
- **dominant**: 找最常见颜色作为背景色。适合纯色/接近纯色的背景。
- **edges**: floodfill 的别名。

### --border-crop (默认 0)
在 floodfill 前从边缘裁剪多少像素。适用于游戏截图边缘有 UI 边框的情况。

### --merge-gap (默认 8)
合并近邻物件的最大间距（像素）。解决物件因背景干扰被切成碎片的问题。

- 0: 不合并
- 4-8: 默认，合并非常靠近的碎片
- 15-25: 合并中等间距的分裂物件
- 30+: 激进合并

### --sort-by (默认 area)
排序方式。
- **area**: 按面积降序，大的先放
- **height**: 按高度降序

### --extract-dir
如果指定，除了生成精灵表，还会把每个物件单独保存为此目录下的 PNG 文件，
命名格式 `sprite_0000.png`, `sprite_0001.png` ...

## 典型场景参数推荐

### 像素风/复古游戏截图
```bash
python3 extract_sprites.py game.png --tolerance 10 --min-size 50 --padding 2
```

### 高清手游截图 (复杂背景)
```bash
python3 extract_sprites.py game.png --tolerance 40 --merge-gap 12 --min-size 200
```

### UI 面板截图 (提取按钮/图标)
```bash
python3 extract_sprites.py ui.png --tolerance 25 --min-size 80 --padding 8
```

### 角色动画帧提取
```bash
python3 extract_sprites.py frames.png --max-cols 1 --padding 0 --merge-gap 0
```

### 瓦片地图提取
```bash
python3 extract_sprites.py tiles.png --tolerance 15 --min-size 30 --padding 0 --max-cols 8
```
