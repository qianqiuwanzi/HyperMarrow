# HyperMarrow 品牌标识 · 文件说明

> 生成时间：2026-07-17
> 版本：v2（人脑版）

---

## 交付物清单

| 文件名 | 格式 | 尺寸 | 用途 |
|--------|------|------|------|
| `hypermarrow_brain_source.svg` | SVG 矢量 | 512×512 | **主源文件**（商标申请用，矢量无限放大） |
| `hypermarrow_brain_1024.png` | PNG 位图 | 1024×1024 | 对外展示、高清演示 |
| `hypermarrow_brain_512.png` | PNG 位图 | 512×512 | 社交媒体、App 图标 |
| `render_brain_simple.py` | Python 源码 | — | 可重新渲染（改参数重跑即可） |
| `preview.html` | HTML | — | 浏览器直接打开预览 SVG |
| `BRAND_GUIDE.md` | 说明文档 | — | 本文件 |

---

## 设计说明

### 图形概念
**人脑侧面轮廓** — 直观表现 HyperMarrow「类人记忆」的核心定位：
- **大脑左半球**：主体，青蓝渐变，象征主记忆区
- **胼胝体**：中间深色横带，象征左右脑连接
- **小脑**：右下方蓝紫区域，象征运动记忆与协调
- **脑干**：底部深紫，象征底层基础架构
- **沟回纹理**：白色弧线，模拟大脑皮层褶皱

### 色彩系统
| 用途 | 色值 | 说明 |
|------|------|------|
| 大脑主体 | `#00d4ff` → `#4da6ff` | 青色，智慧与记忆 |
| 小脑 | `#4da6ff` → `#7c3aed` | 蓝紫，协作区域 |
| 脑干 | `#6d28d9` → `#4c1d95` | 深紫，底层基础 |
| 背景 | `#0e1123` | 深邃科技感 |
| 纹理线 | `#ffffff` 半透明 | 皮层沟回 |

### 字体
- 主标：`Segoe UI / PingFang SC / Microsoft YaHei`，700 字重
- 副标语：同上，400 字重

---

## 商标申请提示

1. **SVG 为主文件**：矢量格式，适合所有尺寸的商标申请
2. **建议提交格式**：EPS / PDF（保留矢量）+ PNG 高清位图
3. **版权声明**：建议注明"© 2026 HyperMarrow / 智商藏不住"
4. **差异化亮点**：人脑侧面侧视图 + 三区渐变色（青/蓝/紫），在 AI/记忆类商标中具有强辨识度

---

## 重新渲染 PNG

```powershell
$env:PYTHONIOENCODING = "utf-8"
python D:\OpenClaw\workspace\HyperMarrow\branding\render_brain_simple.py
```

输出：
- `branding/hypermarrow_brain_1024.png`（高清）
- `branding/hypermarrow_brain_512.png`（中尺寸）

---

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v1 | 2026-07-17 | 神经网络星群版（太 AI 化） |
| v2 | 2026-07-17 | 人脑侧面轮廓版（当前版本） |
