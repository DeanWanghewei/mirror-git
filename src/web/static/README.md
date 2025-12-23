# 静态资源目录说明

本目录用于存放 Web 应用的静态资源文件。

## 目录结构

```
static/
├── images/          # 图片资源
│   ├── favicon.ico  # 网站图标（ICO 格式）
│   ├── favicon.svg  # 网站图标（SVG 格式，现代浏览器）
│   ├── logo.png     # Logo 图片
│   └── ...
├── css/             # 自定义 CSS 文件
│   └── custom.css   # 额外的样式表
├── js/              # 自定义 JavaScript 文件
│   └── custom.js    # 额外的脚本
└── fonts/           # 字体文件
    └── ...

```

## 访问方式

所有静态资源通过 `/static/` 路径访问：

- 图片：`/static/images/logo.png`
- CSS：`/static/css/custom.css`
- JS：`/static/js/custom.js`
- Favicon：`/static/images/favicon.ico`

## Favicon 文件

### 推荐格式

1. **favicon.ico**（必需）
   - 尺寸：16x16, 32x32, 48x48（多尺寸 ICO）
   - 用于传统浏览器和浏览器标签

2. **favicon.svg**（推荐）
   - 矢量格式，支持暗色模式
   - 现代浏览器优先使用

3. **apple-touch-icon.png**（可选）
   - 尺寸：180x180
   - 用于 iOS 设备添加到主屏幕

### 在 HTML 中引用

```html
<!-- 在 <head> 中添加 -->
<link rel="icon" type="image/svg+xml" href="/static/images/favicon.svg">
<link rel="icon" type="image/x-icon" href="/static/images/favicon.ico">
<link rel="apple-touch-icon" href="/static/images/apple-touch-icon.png">
```

## 添加自定义资源

1. 将文件放到对应的子目录
2. 在 HTML 模板中引用：
   ```html
   <link rel="stylesheet" href="/static/css/custom.css">
   <script src="/static/js/custom.js"></script>
   <img src="/static/images/logo.png" alt="Logo">
   ```

## 注意事项

- 静态资源会被 FastAPI 的 `StaticFiles` 中间件处理
- 浏览器会缓存静态资源，更新后可能需要强制刷新（Ctrl+F5）
- 生产环境建议使用 CDN 或 Nginx 提供静态文件服务
