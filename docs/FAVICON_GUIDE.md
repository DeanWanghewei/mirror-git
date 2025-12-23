# Favicon 设置指南

## 📁 文件位置

所有静态资源文件存放在：`src/web/static/`

```
src/web/static/
├── images/
│   ├── favicon.svg              # SVG 图标（推荐，现代浏览器）
│   ├── favicon-dark.svg         # 暗色主题 SVG 图标
│   ├── favicon.ico              # ICO 图标（兼容旧浏览器）
│   └── apple-touch-icon.png     # Apple 设备图标 (180x180)
├── css/                         # 自定义样式表
├── js/                          # 自定义脚本
└── fonts/                       # 字体文件
```

## 🎨 已提供的 Favicon

### 1. **favicon.svg**（主图标）
- ✅ 矢量格式，任意尺寸清晰
- ✅ 文件小，加载快
- ✅ 现代浏览器优先使用
- 🎨 设计：双圆圈 + 同步箭头（代表 GitHub 和 Gitea 之间的镜像同步）

### 2. **favicon-dark.svg**（暗色主题版本）
- ✅ 支持暗色模式的自适应图标
- ✅ 使用 CSS 变量，自动跟随系统主题

### 3. **favicon.ico**（待生成）
- 📋 多尺寸 ICO 文件
- 📋 兼容旧版浏览器

### 4. **apple-touch-icon.png**（待生成）
- 📋 180x180 PNG 图片
- 📋 用于 iOS 设备"添加到主屏幕"

## 🔧 生成 ICO 文件

### 方法 1：使用 Python 脚本（推荐）

```bash
# 安装依赖
pip install Pillow cairosvg

# 运行生成脚本
python src/web/static/generate_favicon.py
```

### 方法 2：在线工具

如果 Python 脚本失败，使用以下在线工具：

1. **RealFaviconGenerator**（推荐）
   - 网址：https://realfavicongenerator.net/
   - 上传 `favicon.svg`
   - 自动生成所有尺寸和格式

2. **Favicon.io**
   - 网址：https://favicon.io/
   - 简单易用，支持 PNG/SVG 转换

3. **Convertio**
   - 网址：https://convertio.co/zh/svg-ico/
   - SVG 转 ICO

生成后，将文件放到 `src/web/static/images/` 目录。

## 📝 HTML 引用（已自动添加）

已在 `src/web/templates/index.html` 的 `<head>` 中添加：

```html
<!-- Favicon -->
<link rel="icon" type="image/svg+xml" href="/static/images/favicon.svg">
<link rel="alternate icon" type="image/x-icon" href="/static/images/favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="/static/images/apple-touch-icon.png">
```

## 🎨 自定义 Favicon

### 修改现有 SVG

编辑 `src/web/static/images/favicon.svg`：

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <!-- 修改颜色 -->
  <circle cx="32" cy="32" r="30" fill="#你的颜色"/>
  <!-- 修改图标内容 -->
  ...
</svg>
```

### 使用自己的图标

1. **替换 SVG**：将你的 SVG 文件重命名为 `favicon.svg`
2. **生成其他格式**：运行 `generate_favicon.py` 或使用在线工具
3. **确保尺寸**：SVG viewBox 推荐 `0 0 64 64`

### 推荐尺寸

- **SVG**：64x64（viewBox）
- **ICO**：16x16, 32x32, 48x48（多尺寸）
- **Apple Touch**：180x180

## 🌐 浏览器兼容性

| 格式              | Chrome | Firefox | Safari | Edge | IE11 |
|-------------------|--------|---------|--------|------|------|
| SVG               | ✅ 80+ | ✅ 41+ | ✅ 9+  | ✅ 79+ | ❌  |
| ICO               | ✅     | ✅      | ✅     | ✅   | ✅   |
| Apple Touch Icon  | ✅     | ✅      | ✅     | ✅   | ❌  |

**建议**：同时提供 SVG 和 ICO 以确保最佳兼容性。

## 🐛 故障排除

### Favicon 不显示？

1. **强制刷新浏览器缓存**
   ```
   Chrome/Edge: Ctrl+Shift+R (Win) / Cmd+Shift+R (Mac)
   Firefox: Ctrl+F5 / Cmd+Shift+R
   ```

2. **清除浏览器缓存**
   - 设置 → 隐私和安全 → 清除浏览数据
   - 选择"缓存的图片和文件"

3. **检查文件路径**
   ```bash
   # 确认文件存在
   ls -la src/web/static/images/favicon.*

   # 访问测试（应用运行时）
   curl http://localhost:8000/static/images/favicon.svg
   ```

4. **检查静态文件挂载**
   - 查看 `src/web/app.py` 中的 `StaticFiles` 配置
   - 确保 `src/web/static/` 目录存在

### SVG 显示异常？

- 确保 SVG 文件编码为 UTF-8
- 检查 XML 语法是否正确
- 在浏览器中直接打开 SVG 查看

## 📊 文件大小参考

- SVG：< 1 KB（优化后）
- ICO（多尺寸）：< 15 KB
- PNG (180x180)：< 5 KB

## 🚀 生产环境优化

### 1. 启用 Gzip 压缩

在 Nginx 配置中：
```nginx
gzip_types image/svg+xml;
```

### 2. 添加缓存头

```nginx
location /static/ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### 3. 使用 CDN

将静态资源上传到 CDN，修改 HTML 引用：
```html
<link rel="icon" href="https://cdn.example.com/favicon.svg">
```

## 📚 相关资源

- [MDN: Favicon](https://developer.mozilla.org/en-US/docs/Glossary/Favicon)
- [W3C: Link types](https://html.spec.whatwg.org/multipage/links.html#rel-icon)
- [Favicon 生成器对比](https://css-tricks.com/favicon-quiz/)

---

**提示**：当前已提供的 SVG 图标可直接使用，ICO 文件可选择生成或使用在线工具创建。
