# HyperMarrow 品牌标识 · 文件说明

> 生成时间：2026-07-17
> 设计师：绿鲤鱼与驴（AI）

---

## 交付物清单

| 文件名 | 格式 | 尺寸 | 用途 |
|--------|------|------|------|
| `hypermarrow_logo_source.svg` | SVG 矢量 | 512×512 | **主源文件**（商标申请用） |
| `hypermarrow_logo_1024.png` | PNG 位图 | 1024×1024 | 对外展示、高清演示 |
| `hypermarrow_logo_512.png` | PNG 位图 | 512×512 | 社交媒体、App 图标 |
| `render_brain.py` | Python 源码 | — | 可重新渲染的脚本 |
| `preview.html` | HTML | — | 浏览器预览（SVG 直接打开） |

---

## 设计说明

### 图形概念
**脑神经网络 × 星群星座** — 象征 HyperMarrow 的核心定位：
- **中心光核**：最亮的青色节点，象征中央智能（Core Intelligence）
- **三层辐射网络**：核心 → 中圈 → 外圈，代表记忆从中心扩散到末梢的架构
- **连接线**：发光的青色线条，代表神经元突触和记忆连接
- **多色节点**：蓝 / 紫 / 青 / 绿 / 粉，代表不同记忆模块的协作

### 色彩系统
| 用途 | 色值 | 说明 |
|------|------|------|
| 深色背景 | `#1a1f3a` → `#0a0d1a` | 科技感、沉稳 |
| 核心光效 | `#00d4ff` | 青色，智慧、记忆 |
| 网络连线 | `#00d4ff` 半透明 | 神经网络 |
| 节点辅色 | `#4da6ff` `#a78bfa` `#22d3ee` `#34d399` `#f472b6` | 多模块协作 |

### 字体
- 主标：`Segoe UI / PingFang SC / Microsoft YaHei`，700 字重
- 副标语：同上，400 字重

---

## 商标申请提示

1. **SVG 为主文件**：矢量无限放大，适合各种尺寸的商标申请
2. **建议提交格式**：EPS 或 PDF（保留矢量），同时附 PNG 高清位图
3. **版权声明**：建议在申请时注明"© 2026 HyperMarrow / 智商藏不住"
4. **差异化要点**：独特的三层神经网络辐射布局 + 中心光核，在 AI/记忆类商标中具有辨识度

---

## 重新渲染

如需修改颜色或尺寸：

```powershell
$env:PYTHONIOENCODING="utf-8"
python D:\OpenClaw\workspace\HyperMarrow\branding\render_brain.py
```

输出：`branding/hypermarrow_logo_1024.png` 和 `_512.png`
