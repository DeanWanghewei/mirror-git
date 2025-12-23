#!/usr/bin/env python3
"""
Generate favicon.ico from SVG using Pillow and cairosvg
"""

import sys
from pathlib import Path

try:
    from PIL import Image
    import cairosvg
    import io
except ImportError:
    print("错误：缺少依赖库")
    print("\n请安装：")
    print("  pip install Pillow cairosvg")
    print("\n或者使用在线工具生成 favicon.ico：")
    print("  https://realfavicongenerator.net/")
    print("  https://favicon.io/")
    sys.exit(1)

# Paths
STATIC_DIR = Path(__file__).parent
SVG_FILE = STATIC_DIR / "images" / "favicon.svg"
ICO_FILE = STATIC_DIR / "images" / "favicon.ico"
PNG_FILE = STATIC_DIR / "images" / "apple-touch-icon.png"

def svg_to_png(svg_path, size):
    """Convert SVG to PNG at specified size"""
    svg_data = open(svg_path, 'rb').read()
    png_data = cairosvg.svg2png(bytestring=svg_data, output_width=size, output_height=size)
    return Image.open(io.BytesIO(png_data))

def generate_favicon():
    """Generate multi-size favicon.ico"""
    if not SVG_FILE.exists():
        print(f"错误：找不到 SVG 文件：{SVG_FILE}")
        return False

    print("正在生成 favicon.ico...")

    # Generate multiple sizes for ICO
    sizes = [16, 32, 48, 64]
    images = []

    for size in sizes:
        print(f"  - 生成 {size}x{size} 图标...")
        img = svg_to_png(SVG_FILE, size)
        images.append(img)

    # Save as ICO
    print(f"  - 保存到 {ICO_FILE}...")
    images[0].save(
        ICO_FILE,
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )

    # Also generate 180x180 for Apple Touch Icon
    print("正在生成 apple-touch-icon.png (180x180)...")
    apple_icon = svg_to_png(SVG_FILE, 180)
    apple_icon.save(PNG_FILE, format='PNG')

    print("\n✓ 成功生成：")
    print(f"  - {ICO_FILE.relative_to(STATIC_DIR.parent.parent.parent)}")
    print(f"  - {PNG_FILE.relative_to(STATIC_DIR.parent.parent.parent)}")
    print("\n提示：请在 HTML <head> 中添加：")
    print('  <link rel="icon" type="image/svg+xml" href="/static/images/favicon.svg">')
    print('  <link rel="icon" type="image/x-icon" href="/static/images/favicon.ico">')
    print('  <link rel="apple-touch-icon" href="/static/images/apple-touch-icon.png">')

    return True

if __name__ == "__main__":
    try:
        success = generate_favicon()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 生成失败：{e}")
        print("\n备选方案：")
        print("1. 使用在线工具：https://realfavicongenerator.net/")
        print("2. 或直接使用 SVG 版本（现代浏览器支持）")
        sys.exit(1)
