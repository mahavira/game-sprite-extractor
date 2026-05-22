#!/usr/bin/env python3
"""
Game Sprite Extractor - 从游戏截图中提取所有物件并排布为精灵表（Sprite Sheet）

用法:
    python3 extract_sprites.py <input_image> [output_image] [options]

选项:
    --tolerance N      背景色容差 (0-255, 默认 30)
    --min-size N       最小物件面积（像素）, 过滤噪点 (默认 100)
    --padding N        物件之间的间距像素 (默认 4)
    --max-cols N       最大列数 (默认 0=自动)
    --border-crop N    边缘裁剪像素, 排除边缘背景残留 (默认 0)
    --method METHOD    背景检测方法: floodfill / dominant / edges (默认 floodfill)
    --extract-dir DIR  同时输出单独提取的每个物件到此目录

输出:
    一张 RGBA PNG 精灵表, 透明背景, 物件按方格排布。
    可直接用于游戏引擎的 Texture、Sprite、Tileset 等。
"""

import argparse
import math
import os
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("错误: 需要 Pillow 库，请运行: pip install Pillow")
    sys.exit(1)


# ── 背景检测 ────────────────────────────────────────────

def sample_corner_colors(img, sample_size=5):
    """从四个角和四条边采样背景颜色"""
    w, h = img.size
    samples = []
    corners = [
        (0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
        (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2),
    ]
    for cx, cy in corners:
        for dx in range(-sample_size, sample_size + 1):
            for dy in range(-sample_size, sample_size + 1):
                x = max(0, min(w - 1, cx + dx))
                y = max(0, min(h - 1, cy + dy))
                samples.append(img.getpixel((x, y)))
    return samples


def dominant_background_color(img, sample_size=5):
    """找最常见的颜色作为背景色"""
    from collections import Counter
    samples = sample_corner_colors(img, sample_size)
    counter = Counter(samples)
    return counter.most_common(1)[0][0]


def color_distance(c1, c2):
    """RGB 空间的欧氏距离"""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))


def floodfill_background_mask(img, tolerance=30, border_crop=0):
    """从四条边 flood fill 标记背景区域, 返回背景 mask (True=背景)"""
    w, h = img.size
    pixels = img.load()
    mask = [[False] * w for _ in range(h)]  # True = 已访问
    bg_mask = [[False] * w for _ in range(h)]  # True = 背景

    # 从四条边每个像素开始 flood fill
    queue = deque()
    for x in range(border_crop, w - border_crop):
        queue.append((x, border_crop))
        queue.append((x, h - 1 - border_crop))
    for y in range(border_crop, h - border_crop):
        queue.append((border_crop, y))
        queue.append((w - 1 - border_crop, y))

    # 取边缘起始点的颜色作为 anchor 色（用于判断相似度）
    edge_colors = []
    for x in range(border_crop, w - border_crop):
        edge_colors.append(pixels[x, border_crop])
        edge_colors.append(pixels[x, h - 1 - border_crop])
    for y in range(border_crop, h - border_crop):
        edge_colors.append(pixels[border_crop, y])
        edge_colors.append(pixels[w - 1 - border_crop, y])

    # 使用中位数颜色作为参考
    ref_color = tuple(
        sorted([c[i] for c in edge_colors])[len(edge_colors) // 2]
        for i in range(3)
    )

    while queue:
        x, y = queue.popleft()
        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        if mask[y][x]:
            continue
        mask[y][x] = True

        pixel = pixels[x, y]
        if color_distance(pixel, ref_color) <= tolerance:
            bg_mask[y][x] = True
            # 8-邻域扩展
            for dx, dy in [
                (-1, -1), (0, -1), (1, -1),
                (-1, 0),           (1, 0),
                (-1, 1),  (0, 1),  (1, 1),
            ]:
                queue.append((x + dx, y + dy))

    return bg_mask


def dominant_method_mask(img, tolerance=30):
    """基于最常见颜色的背景标记"""
    bg_color = dominant_background_color(img)
    w, h = img.size
    pixels = img.load()
    bg_mask = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if color_distance(pixels[x, y], bg_color) <= tolerance:
                bg_mask[y][x] = True
    return bg_mask


# ── 物件检测 ────────────────────────────────────────────

def find_connected_components(bg_mask):
    """在非背景区域找连通分量 (4-邻域)"""
    h = len(bg_mask)
    w = len(bg_mask[0])
    visited = [[False] * w for _ in range(h)]
    components = []

    for y in range(h):
        for x in range(w):
            if bg_mask[y][x] or visited[y][x]:
                continue
            # BFS 收集当前连通分量
            queue = deque([(x, y)])
            visited[y][x] = True
            comp = []
            while queue:
                cx, cy = queue.popleft()
                comp.append((cx, cy))
                for nx, ny in [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]:
                    if 0 <= nx < w and 0 <= ny < h:
                        if not bg_mask[ny][nx] and not visited[ny][nx]:
                            visited[ny][nx] = True
                            queue.append((nx, ny))
            components.append(comp)

    return components


def merge_nearby_components(components, max_gap=8):
    """合并距离很近的连通分量 (解决物件被背景色切碎的问题)"""
    if len(components) <= 1:
        return components

    # 计算每个分量的包围盒
    bboxes = []
    for comp in components:
        xs = [p[0] for p in comp]
        ys = [p[1] for p in comp]
        bboxes.append((min(xs), min(ys), max(xs), max(ys), comp))

    # 贪心合并：bbox 距离 <= max_gap 的合并
    merged = []
    used = [False] * len(bboxes)

    for i, (x1, y1, x2, y2, comp_i) in enumerate(bboxes):
        if used[i]:
            continue
        group = list(comp_i)
        gx1, gy1, gx2, gy2 = x1, y1, x2, y2
        used[i] = True

        changed = True
        while changed:
            changed = False
            for j, (jx1, jy1, jx2, jy2, comp_j) in enumerate(bboxes):
                if used[j]:
                    continue
                # 计算两个 bbox 的间距
                gap_x = max(0, max(gx1, jx1) - min(gx2, jx2))
                gap_y = max(0, max(gy1, jy1) - min(gy2, jy2))
                if gap_x <= max_gap and gap_y <= max_gap:
                    group.extend(comp_j)
                    gx1 = min(gx1, jx1)
                    gy1 = min(gy1, jy1)
                    gx2 = max(gx2, jx2)
                    gy2 = max(gy2, jy2)
                    used[j] = True
                    changed = True

        merged.append(group)

    return merged


# ── 物件提取 ────────────────────────────────────────────

def extract_sprite(img, component_pixels, bg_mask):
    """提取单个物件为 RGBA 图片 (背景透明)"""
    pixels = img.load()
    xs = [p[0] for p in component_pixels]
    ys = [p[1] for p in component_pixels]
    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)

    bbox_w = x2 - x1 + 1
    bbox_h = y2 - y1 + 1
    sprite = Image.new("RGBA", (bbox_w, bbox_h), (0, 0, 0, 0))
    sp_pixels = sprite.load()

    # 构建像素集合用于快速查找
    pixel_set = set(component_pixels)

    for py in range(y1, y2 + 1):
        for px in range(x1, x2 + 1):
            if (px, py) in pixel_set:
                r, g, b = pixels[px, py][:3]
                sp_pixels[px - x1, py - y1] = (r, g, b, 255)
            elif not bg_mask[py][px]:
                # 边界像素：属于非背景但在包围盒内但不在当前组件中
                # 也保留（用于处理颜色容差导致的内部空洞）
                r, g, b = pixels[px, py][:3]
                sp_pixels[px - x1, py - y1] = (r, g, b, 255)

    return sprite


# ── 精灵表排布 ──────────────────────────────────────────

def calculate_grid_layout(sprites, padding, max_cols=0):
    """计算网格布局: 返回 (cols, rows, cell_width, cell_height)"""
    if not sprites:
        return 1, 1, 32, 32

    n = len(sprites)
    max_w = max(s.width for s in sprites)
    max_h = max(s.height for s in sprites)

    # 加上 padding
    cell_w = max_w + padding * 2
    cell_h = max_h + padding * 2

    if max_cols > 0:
        cols = min(max_cols, n)
        rows = math.ceil(n / cols)
    else:
        # 自动: 尽量接近正方形
        cols = math.ceil(math.sqrt(n * cell_w / cell_h))
        cols = max(1, cols)
        rows = math.ceil(n / cols)

    return cols, rows, cell_w, cell_h


def pack_sprites(sprites, padding=4, max_cols=0, sort_by="area"):
    """将精灵打包到精灵表中"""
    if not sprites:
        h_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        return h_img, []

    # 排序：大的先放
    if sort_by == "area":
        sorted_sprites = sorted(sprites, key=lambda s: s.width * s.height, reverse=True)
    elif sort_by == "height":
        sorted_sprites = sorted(sprites, key=lambda s: s.height, reverse=True)
    else:
        sorted_sprites = list(sprites)

    cols, rows, cell_w, cell_h = calculate_grid_layout(sorted_sprites, padding, max_cols)

    sheet_w = cols * cell_w
    sheet_h = rows * cell_h
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))

    # 放置每个精灵到网格中（居中放置）
    positions = []
    for idx, sprite in enumerate(sorted_sprites):
        row = idx // cols
        col = idx % cols

        # 在格子中居中
        ox = col * cell_w + padding + (cell_w - 2 * padding - sprite.width) // 2
        oy = row * cell_h + padding + (cell_h - 2 * padding - sprite.height) // 2

        sheet.paste(sprite, (ox, oy), sprite)
        positions.append({
            "index": idx,
            "x": ox,
            "y": oy,
            "w": sprite.width,
            "h": sprite.height,
            "col": col,
            "row": row,
        })

    return sheet, positions


# ── 主流程 ──────────────────────────────────────────────

def extract_sprites(
    input_path,
    output_path,
    tolerance=30,
    min_size=100,
    padding=4,
    max_cols=0,
    border_crop=0,
    method="floodfill",
    extract_dir=None,
    sort_by="area",
    merge_gap=8,
):
    """主提取流程"""
    print(f"[1/6] 加载图片: {input_path}")
    img = Image.open(input_path).convert("RGB")
    w, h = img.size
    print(f"      尺寸: {w}x{h}")

    # 背景检测
    print(f"[2/6] 背景检测 (方法: {method}, 容差: {tolerance})")
    if method == "floodfill":
        bg_mask = floodfill_background_mask(img, tolerance, border_crop)
    elif method == "dominant":
        bg_mask = dominant_method_mask(img, tolerance)
    else:
        # edges: 先用 floodfill 再膨胀
        bg_mask = floodfill_background_mask(img, tolerance, border_crop)

    bg_count = sum(sum(1 for v in row if v) for row in bg_mask)
    print(f"      背景像素: {bg_count} / {w * h} ({100 * bg_count / (w * h):.1f}%)")

    # 连通分量检测
    print("[3/6] 查找物件连通分量...")
    components = find_connected_components(bg_mask)
    print(f"      原始分量: {len(components)}")

    # 过滤小物件
    components = [c for c in components if len(c) >= min_size]
    print(f"      过滤后 (>= {min_size}px): {len(components)}")

    # 合并近邻分量
    if merge_gap > 0:
        components = merge_nearby_components(components, merge_gap)
        print(f"      合并近邻后 (gap={merge_gap}): {len(components)}")

    if not components:
        print("错误: 未检测到任何物件，尝试降低 --tolerance 或 --min-size")
        sys.exit(1)

    # 提取精灵
    print(f"[4/6] 提取 {len(components)} 个物件为独立精灵...")
    sprites = []
    for i, comp in enumerate(components):
        sprite = extract_sprite(img, comp, bg_mask)
        sprites.append(sprite)

    # 可选：单独保存
    if extract_dir:
        os.makedirs(extract_dir, exist_ok=True)
        for i, sprite in enumerate(sprites):
            name = f"sprite_{i:04d}.png"
            sprite.save(os.path.join(extract_dir, name))
        print(f"      单独导出: {extract_dir}/")

    # 打包精灵表
    print(f"[5/6] 排布精灵表 (padding={padding}, max_cols={max_cols or 'auto'})...")
    sheet, positions = pack_sprites(sprites, padding, max_cols, sort_by)
    print(f"      精灵表尺寸: {sheet.width}x{sheet.height}")
    print(f"      物件数量: {len(positions)}")

    # 保存
    print(f"[6/6] 保存精灵表: {output_path}")
    sheet.save(output_path, "PNG")

    # 输出元数据
    print(f"\n{'='*50}")
    print(f"精灵表已生成: {output_path}")
    print(f"尺寸: {sheet.width}x{sheet.height}")
    print(f"物件数: {len(sprites)}")
    print(f"格式: RGBA PNG, 透明背景")
    print(f"{'='*50}")

    if positions:
        print(f"\n物件索引 (网格排布):")
        for p in sorted(positions, key=lambda x: x["index"]):
            print(f"  #{p['index']:03d}  位置({p['x']:4d},{p['y']:4d})  尺寸{p['w']:3d}x{p['h']:3d}  格子({p['col']},{p['row']})")

    return sheet, positions


def main():
    parser = argparse.ArgumentParser(
        description="游戏精灵提取器 - 从截图提取所有物件生成精灵表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 extract_sprites.py screenshot.png
  python3 extract_sprites.py screenshot.png output.png --tolerance 40
  python3 extract_sprites.py screenshot.png --min-size 200 --padding 8
  python3 extract_sprites.py screenshot.png --method dominant --extract-dir ./sprites/
        """,
    )
    parser.add_argument("input", help="输入图片路径 (游戏截图)")
    parser.add_argument("output", nargs="?", default=None, help="输出精灵表路径 (默认: input_sheet.png)")
    parser.add_argument("--tolerance", type=int, default=30, help="背景色容差 (默认 30)")
    parser.add_argument("--min-size", type=int, default=100, help="最小物件像素面积 (默认 100)")
    parser.add_argument("--padding", type=int, default=4, help="物件间距像素 (默认 4)")
    parser.add_argument("--max-cols", type=int, default=0, help="最大列数 (默认 0=自动)")
    parser.add_argument("--border-crop", type=int, default=0, help="边缘裁剪像素 (默认 0)")
    parser.add_argument("--method", default="floodfill", choices=["floodfill", "dominant", "edges"], help="背景检测方法 (默认 floodfill)")
    parser.add_argument("--extract-dir", default=None, help="单独导出每个物件的目录")
    parser.add_argument("--sort-by", default="area", choices=["area", "height"], help="排序方式 (默认 area)")
    parser.add_argument("--merge-gap", type=int, default=8, help="合并近邻物件的间距 (默认 8, 0=不合并)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 找不到输入文件 {args.input}")
        sys.exit(1)

    if args.output is None:
        p = Path(args.input)
        args.output = str(p.parent / f"{p.stem}_sheet.png")

    extract_sprites(
        args.input,
        args.output,
        tolerance=args.tolerance,
        min_size=args.min_size,
        padding=args.padding,
        max_cols=args.max_cols,
        border_crop=args.border_crop,
        method=args.method,
        extract_dir=args.extract_dir,
        sort_by=args.sort_by,
        merge_gap=args.merge_gap,
    )


if __name__ == "__main__":
    main()
