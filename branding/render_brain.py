"""
HyperMarrow 产品图标渲染脚本
使用纯 PIL + 内置 tkinter/wx 图形库绘制，无需外部 SVG 转换器
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
import math
import sys
import os

# ---------- 配置 ----------
SIZE = 1024  # PNG 输出尺寸（SVG viewBox = 512，2x = 1024px）
OUT_PNG = os.path.join(os.path.dirname(__file__), "hypermarrow_logo_1024.png")
OUT_PNG_SMALL = os.path.join(os.path.dirname(__file__), "hypermarrow_logo_512.png")

# SVG 坐标 → 1024px 缩放比例
S = SIZE / 512

def rad_g(cx, cy, r, color_inner, color_outer):
    """生成径向渐变 RGBA 像素数据（中心亮→边缘暗）"""
    img = Image.new("RGBA", (r*2+2, r*2+2), (0,0,0,0))
    px = img.load()
    for y in range(r*2+2):
        for x in range(r*2+2):
            dist = math.sqrt((x-r)**2 + (y-r)**2)
            t = min(dist/r, 1.0)
            t2 = t*t
            # 线性插值
            ri = int(color_inner[0]*(1-t2) + color_outer[0]*t2)
            gi = int(color_inner[1]*(1-t2) + color_outer[1]*t2)
            bi = int(color_inner[2]*(1-t2) + color_outer[2]*t2)
            ai = int(color_inner[3]*(1-t) + color_outer[3]*t)
            px[x,y] = (ri, gi, bi, ai)
    return img

def glow_circle(draw, cx, cy, r, color, glow_r=12, alpha=180):
    """画一个发光圆（模糊层 + 锐利层）"""
    # 模糊发光层
    glow_img = Image.new("RGBA", (glow_r*2+r*2+4, glow_r*2+r*2+4), (0,0,0,0))
    gd = ImageDraw.Draw(glow_img)
    cx2 = glow_r + r + 2
    cy2 = glow_r + r + 2
    gd.ellipse([cx2-r, cy2-r, cx2+r, cy2+r], fill=(*color[:3], alpha))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=glow_r))
    # 转成可 draw 的
    glow_resized = glow_img.resize((glow_r*2+r*2+4, glow_r*2+r*2+4), Image.LANCZOS)
    # paste 到主画布
    paste_x = cx - cx2
    paste_y = cy - cy2
    return glow_resized, paste_x, paste_y

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def lerp(a, b, t):
    return tuple(int(a[i]*(1-t) + b[i]*t) for i in range(len(a)))

def make_radial(r, inner, outer):
    """生成 r*2+4 大小的径向渐变 RGBA 图，中心亮→边缘半透明
    inner=(r,g,b), outer=(r,g,b)"""
    sz = r*2+4
    img = Image.new("RGBA", (sz, sz), (0,0,0,0))
    px = img.load()
    for dy in range(-r-2, r+3):
        for dx in range(-r-2, r+3):
            d = math.sqrt(dx*dx + dy*dy)
            if d > r+1:
                continue
            t = max(0.0, min(1.0, d/(r+0.5)))
            t2 = t*t
            ri = int(inner[0]*(1-t2) + outer[0]*t2)
            gi = int(inner[1]*(1-t2) + outer[1]*t2)
            bi = int(inner[2]*(1-t2) + outer[2]*t2)
            ai = int(200*(1-t) + 80*t)
            px[dx+r+2, dy+r+2] = (ri, gi, bi, ai)
    return img

def draw_line_glow(canvas, x1, y1, x2, y2, color, width=3, glow_w=6):
    """在画布上画发光线"""
    overlay = Image.new("RGBA", canvas.size, (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    # 发光层
    od.line([(x1,y1),(x2,y2)], fill=(*color[:3], 60), width=glow_w)
    blur_glow = overlay.filter(ImageFilter.GaussianBlur(radius=glow_w/2))
    # 清晰层
    od.line([(x1,y1),(x2,y2)], fill=(*color[:3], 160), width=width)
    # 合成
    canvas.alpha_composite(blur_glow, (0,0))
    od2 = ImageDraw.Draw(canvas)
    od2.line([(x1,y1),(x2,y2)], fill=(*color[:3], 200), width=width)

def render_icon(size=1024):
    S = size / 512
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    # --- 背景 ---
    bg_r = int(80*S)
    # 背景
    bg = Image.new("RGBA", (size, size), (10, 13, 26, 255))
    bd = ImageDraw.Draw(bg)
    bd.rounded_rectangle([(0,0),(size-1,size-1)], radius=bg_r, fill=(26, 31, 58, 255))
    # 背景光晕
    for r, c, a in [(int(180*S), (0, 102, 255), 18), (int(100*S), (0, 212, 255), 12)]:
        hi = Image.new("RGBA", (r*2, r*2), (0,0,0,0))
        hd = ImageDraw.Draw(hi)
        hd.ellipse([0,0,r*2-1,r*2-1], fill=(*c, a))
        hi_blur = hi.filter(ImageFilter.GaussianBlur(radius=int(30*S)))
        paste_x = int(256*S) - r
        paste_y = int(230*S) - r
        bg.alpha_composite(hi_blur, (paste_x, paste_y))
    img = bg

    # --- 节点颜色定义 ---
    # (inner_rgb, outer_rgb, alpha)
    BLUE    = (( 77, 166, 255), (  0,  82, 204), 220)
    PURPLE  = ((167, 139, 250), (109,  40, 217), 220)
    TEAL    = (( 34, 211, 238), (  8, 145, 178), 220)
    PINK    = ((244, 114, 182), (190,  24, 133), 220)
    GREEN   = (( 52, 211, 153), (  5, 150, 105), 220)
    OUTER1  = (( 96, 165, 250), ( 30,  64, 175), 200)
    OUTER2  = ((192, 132, 252), (126,  34, 207), 200)
    CORE_IN = (  0, 212, 255)
    CORE_OUT= (  0,  51, 204)

    CYAN = (0, 212, 255)

    # 节点位置（缩放后）
    def p(x, y): return (int(x*S), int(y*S))

    # 节点定义：(x, y, inner, outer, radius_px)
    outer_nodes = [
        p(62,182), p(78,248), p(88,268), p(100,358), p(130,108), p(155,82),
        p(450,182), p(434,248), p(424,268), p(412,358), p(382,108), p(357,82),
        p(256,400), p(220,390), p(292,390), p(140,390), p(372,390),
        p(42,310), p(470,310), p(256,62),
    ]
    outer_colors = [
        OUTER1, OUTER2, BLUE, PURPLE, TEAL, OUTER1,
        OUTER1, OUTER2, BLUE, PURPLE, TEAL, OUTER1,
        GREEN, BLUE, BLUE, PURPLE, PURPLE,
        TEAL, TEAL, GREEN,
    ]
    outer_radii = [int(r*S) for r in [11,9,12,10,10,8, 11,9,12,10,10,8, 12,10,10,8,8, 9,9,9]]

    mid_nodes = [
        p(165,248), p(347,248), p(175,328), p(337,328),
        p(256,310), p(128,200), p(384,200), p(185,148), p(327,148),
    ]
    mid_colors = [BLUE, PURPLE, TEAL, PINK, GREEN, PURPLE, BLUE, GREEN, TEAL]
    mid_radii = [int(r*S) for r in [22,22,20,20,21,20,20,19,19]]

    # --- 绘制连接线 ---
    overlay_lines = Image.new("RGBA", img.size, (0,0,0,0))
    ld = ImageDraw.Draw(overlay_lines)

    # 核心到内圈
    core_pos = p(256, 200)
    for nx, ny in mid_nodes:
        ld.line([core_pos, (nx,ny)], fill=(*CYAN, 90), width=int(1.8*S))
    for nx, ny in outer_nodes:
        ld.line([core_pos, (nx,ny)], fill=(*CYAN, 60), width=int(1.2*S))

    # 内圈到外圈
    for i, (mx, my) in enumerate(mid_nodes):
        for j, (ox, oy) in enumerate(outer_nodes):
            # 判断是否应该连线（空间上接近）
            dist = math.sqrt((mx-ox)**2 + (my-oy)**2)
            if dist < int(130*S):
                ld.line([(mx,my),(ox,oy)], fill=(77,166,255,50), width=int(1*S))

    # 外圈内部弱连线
    for i in range(len(outer_nodes)):
        for j in range(i+1, len(outer_nodes)):
            x1,y1 = outer_nodes[i]
            x2,y2 = outer_nodes[j]
            dist = math.sqrt((x1-x2)**2+(y1-y2)**2)
            if dist < int(90*S):
                ld.line([(x1,y1),(x2,y2)], fill=(77,166,255,25), width=int(0.8*S))

    # 模糊发光线
    lines_blur = overlay_lines.filter(ImageFilter.GaussianBlur(radius=int(2.5*S)))
    img.alpha_composite(lines_blur, (0,0))
    img.alpha_composite(overlay_lines, (0,0))

    # --- 绘制节点 ---
    def draw_node(canvas, cx, cy, r, inner, outer, glow_s=6):
        # 外发光
        glow_img = Image.new("RGBA", canvas.size, (0,0,0,0))
        gd = ImageDraw.Draw(glow_img)
        gd.ellipse([cx-r-glow_s, cy-r-glow_s, cx+r+glow_s, cy+r+glow_s],
                   fill=(inner[0], inner[1], inner[2], 120))
        glow_blur = glow_img.filter(ImageFilter.GaussianBlur(radius=glow_s))
        canvas.alpha_composite(glow_blur, (0,0))
        # 主体
        node = make_radial(r, inner, outer)
        canvas.alpha_composite(node, (cx-r-2, cy-r-2))

    # 外圈节点
    for i, (nx,ny) in enumerate(outer_nodes):
        c = outer_colors[i]
        r = outer_radii[i]
        draw_node(img, nx, ny, r, c[0], c[1])

    # 内圈节点
    for i, (nx,ny) in enumerate(mid_nodes):
        c = mid_colors[i]
        r = mid_radii[i]
        draw_node(img, nx, ny, r, c[0], c[1], glow_s=int(6*S))

    # --- 核心节点 ---
    cx, cy = core_pos
    cr = int(36*S)
    # 外发光
    glow_bg = Image.new("RGBA", img.size, (0,0,0,0))
    gd = ImageDraw.Draw(glow_bg)
    gd.ellipse([cx-cr*2, cy-cr*2, cx+cr*2, cy+cr*2], fill=(*CYAN, 60))
    glow_blur = glow_bg.filter(ImageFilter.GaussianBlur(radius=int(20*S)))
    img.alpha_composite(glow_blur, (0,0))
    # 第二层光环
    halo = Image.new("RGBA", img.size, (0,0,0,0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse([cx-int(46*S), cy-int(46*S), cx+int(46*S), cy+int(46*S)],
               fill=(0,0,0,0), outline=(*CYAN, 128))
    img.alpha_composite(halo, (0,0))
    # 核心渐变圆
    core = make_radial(cr, CORE_IN, CORE_OUT)
    dark_core = Image.new("RGBA", (cr*2+4, cr*2+4), (13,27,74,255))
    dc_d = ImageDraw.Draw(dark_core)
    dc_d.ellipse([2,2,cr*2+2,cr*2+2], fill=(13,27,74,255))
    dark_core.alpha_composite(core, (0,0))
    img.alpha_composite(dark_core, (cx-cr-2, cy-cr-2))
    # 内核高光
    hi_r = int(14*S)
    hi = Image.new("RGBA", (hi_r*2+4, hi_r*2+4), (0,0,0,0))
    hd = ImageDraw.Draw(hi)
    hd.ellipse([2,2,hi_r*2+2,hi_r*2+2], fill=(255,255,255,51))
    img.alpha_composite(hi, (cx-hi_r-2, cy-hi_r-2))
    # 中心亮点
    c_r = int(5*S)
    cg = Image.new("RGBA", (c_r*2+4, c_r*2+4), (0,0,0,0))
    cd = ImageDraw.Draw(cg)
    cd.ellipse([2,2,c_r*2+2,c_r*2+2], fill=(255,255,255,204))
    img.alpha_composite(cg, (cx-c_r-2, cy-c_r-2))

    # --- 文字 ---
    # 品牌名
    font_size = int(36*S)
    try:
        font_main = ImageFont.truetype("arial.ttf", font_size)
        font_sub  = ImageFont.truetype("arial.ttf", int(13*S))
    except:
        font_main = ImageFont.load_default()
        font_sub  = ImageFont.load_default()

    # 文字阴影
    shadow = Image.new("RGBA", img.size, (0,0,0,0))
    sd = ImageDraw.Draw(shadow)
    tx, ty_main = int(256*S), int(462*S)
    sd.text((tx+2, ty_main+2), "HyperMarrow", font=font_main, anchor="mm",
            fill=(0,0,0,100))
    img.alpha_composite(shadow, (0,0))
    td = ImageDraw.Draw(img)
    td.text((tx, ty_main), "HyperMarrow", font=font_main, anchor="mm",
            fill=(224, 242, 254))

    # 副标题
    tx2, ty2 = int(256*S), int(488*S)
    td.text((tx2, ty2), "类人记忆与学习系统", font=font_sub, anchor="mm",
            fill=(100, 116, 139))

    return img

# ---------- 主渲染 ----------
print("正在渲染 1024px PNG...")
img_1024 = render_icon(1024)
img_1024.save(OUT_PNG, "PNG", optimize=True)
print(f"[OK] saved: {OUT_PNG}")

print("正在渲染 512px PNG...")
img_512 = render_icon(512)
img_512.save(OUT_PNG_SMALL, "PNG", optimize=True)
print(f"[OK] saved: {OUT_PNG_SMALL}")

print("\n完成！")
