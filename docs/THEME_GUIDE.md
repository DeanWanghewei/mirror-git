# 主题切换功能说明

## 功能特性

已成功添加三种主题模式：

### 1. ☀️ 浅色主题（Light）
- 明亮的背景色
- 适合白天使用
- 清晰的对比度

### 2. 🌙 深色主题（Dark）
- 深色背景，浅色文字
- 减少眼睛疲劳
- 适合夜间使用

### 3. 🔄 跟随系统（Auto）
- 自动跟随操作系统主题设置
- 当系统切换主题时自动变化
- 默认模式

## 使用方法

1. **打开应用**：访问 http://localhost:8000

2. **切换主题**：在导航栏右侧找到主题切换器
   - 点击太阳图标 ☀️ - 切换到浅色主题
   - 点击半圆图标 ◐ - 跟随系统主题（默认）
   - 点击月亮图标 🌙 - 切换到深色主题

3. **主题保存**：
   - 您的主题选择会自动保存到浏览器的 localStorage
   - 下次访问时会自动应用您上次选择的主题

## 技术实现

### CSS 变量系统

```css
/* 浅色主题变量 */
:root {
    --bg-primary: #F9FAFB;
    --bg-secondary: #FFFFFF;
    --text-primary: #111827;
    /* ... */
}

/* 深色主题变量 */
[data-theme="dark"] {
    --bg-primary: #111827;
    --bg-secondary: #1F2937;
    --text-primary: #F9FAFB;
    /* ... */
}
```

### JavaScript 功能

- **自动检测系统主题**：使用 `window.matchMedia('(prefers-color-scheme: dark)')`
- **主题持久化**：使用 localStorage 保存用户偏好
- **实时响应**：监听系统主题变化事件
- **平滑过渡**：CSS transition 实现主题切换动画

### 组件适配

所有 UI 组件都已适配主题：
- ✅ 卡片（Cards）
- ✅ 表格（Tables）
- ✅ 表单（Forms）
- ✅ 按钮（Buttons）
- ✅ 导航栏（Navbar）
- ✅ Toast 通知（Toast Notifications）
- ✅ 模态框（Modals）

## 测试建议

1. **测试浅色主题**：
   - 点击太阳图标
   - 检查所有页面元素是否正常显示
   - 检查对比度是否清晰

2. **测试深色主题**：
   - 点击月亮图标
   - 验证暗色背景和浅色文字
   - 检查所有按钮和表单元素

3. **测试跟随系统**：
   - 点击半圆图标
   - 在操作系统中切换主题
   - 验证应用是否自动跟随变化

4. **测试持久化**：
   - 选择一个主题
   - 刷新页面
   - 验证主题是否保持

## 浏览器兼容性

- ✅ Chrome 76+
- ✅ Firefox 67+
- ✅ Safari 12.1+
- ✅ Edge 79+

## 故障排除

如果主题切换不工作：

1. **清除浏览器缓存**：
   ```bash
   Ctrl/Cmd + Shift + R
   ```

2. **检查 localStorage**：
   打开浏览器开发者工具 → Application → Local Storage
   找到 `mirror-git-theme` 键

3. **手动重置**：
   在浏览器控制台运行：
   ```javascript
   localStorage.removeItem('mirror-git-theme');
   location.reload();
   ```

## 自定义主题

如果需要自定义主题颜色，修改 `src/web/templates/index.html` 中的 CSS 变量：

```css
:root {
    /* 修改浅色主题颜色 */
    --primary-color: #你的颜色;
}

[data-theme="dark"] {
    /* 修改深色主题颜色 */
    --primary-color: #你的颜色;
}
```

---

**提示**：主题功能完全在客户端实现，不会增加服务器负担。
