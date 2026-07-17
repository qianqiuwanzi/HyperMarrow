"""
HyperMarrow 人脑图标渲染脚本 v2.1 — 纯 PIL，无外部依赖
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math, os

BRAND_DIR = os.path.dirname(os.path.abspath(__file__))

# ========== 工具函数 ==========

def draw_glow_line(canvas, x1, y1, x2, y2, color, width=3, glow_r=4):
    ov = Image.new("RGBA", canvas.size, (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    d.line([(x1,y1),(x2,y2)], fill=(*color, 80), width=glow_r*2)
    blur = ov.filter(ImageFilter.GaussianBlur(radius=glow_r))
    canvas.alpha_composite(blur, (0,0))
    d2 = ImageDraw.Draw(canvas)
    d2.line([(x1,y1),(x2,y2)], fill=(*color, 200), width=width)

def cubic_bezier_pts(p0, p1, p2, p3, steps=30):
    pts = []
    for i in range(steps+1):
        t = i/steps
        mt = 1-t
        x = mt**3*p0[0] + 3*mt**2*t*p1[0] + 3*mt*t**2*p2[0] + t**3*p3[0]
        y = mt**3*p0[1] + 3*mt**2*t*p1[1] + 3*mt*t**2*p2[1] + t**3*p3[1]
        pts.append((x, y))
    return pts

def draw_bezier_curve(canvas, p0, p1, p2, p3, color, width=2, steps=30, glow_r=3):
    pts = cubic_bezier_pts(p0, p1, p2, p3, steps)
    for i in range(len(pts)-1):
        draw_glow_line(canvas,
            int(pts[i][0]),   int(pts[i][1]),
            int(pts[i+1][0]),int(pts[i+1][1]),
            color, width=width, glow_r=glow_r)

# 所有坐标基于 canvas=512，左上角 (0,0)
# 大脑中心在 (256, 230)
OX, OY = 256, 230   # origin offset

def rel(x, y):
    return (x+OX, y+OY)

# ========== 人脑路径定义 ==========
# 左半球（主要大脑皮层）bezier 链
LEFT_HEM = (
    rel(-75,-120), rel(-20,-135), rel( 30,-120), rel( 70, -95),
    rel(100, -75), rel(115, -45), rel(118,   5),
    rel(120,  45), rel(108,  80), rel( 88, 105),
    rel( 68, 128), rel( 42, 142), rel( 12, 148),
    rel(-20, 152), rel(-50, 142), rel(-72, 120),
    rel(-95,  96), rel(-108, 60), rel(-108,  18),
    rel(-108,-28), rel(-98, -72), rel(-75,-120),
)

# 胼胝体
CORPUS = (
    rel(-30,-55), rel(-15,-62), rel( 5,-62), rel( 18,-55),
    rel( 30,-48), rel( 30,-38), rel( 18,-32),
    rel(  5,-26), rel(-15,-26), rel(-30,-32),
    rel(-44,-38), rel(-44,-48), rel(-30,-55),
)

# 小脑
CEREB = (
    rel( 88,105), rel(110,118), rel(130,138), rel(135,162),
    rel(140,182), rel(130,198), rel(112,205),
    rel( 94,212), rel( 74,205), rel( 60,192),
    rel( 48,180), rel( 46,162), rel( 54,145),
    rel( 62,130), rel( 76,116), rel( 88,105),
)

# 脑干
STEM = (
    rel(-10,148), rel(  5,155), rel( 20,158), rel( 28,168),
    rel( 34,178), rel( 30,190), rel( 20,196),
    rel(  8,202), rel( -8,200), rel(-18,192),
    rel(-28,183), rel(-28,170), rel(-18,160),
    rel( -8,152), rel(  0,150), rel(-10,148),
)

# 皮层纹理曲线
GYRUS1 = rel(-68,-108), rel(-40,-118), rel(20,-100), rel(70,-80)
GYRUS2 = rel(-62, -50), rel(-38, -55), rel(15, -40), rel(70,-18)
GYRUS3 = rel(-58,  15), rel(-35,  12), rel(20,  28), rel(72, 55)
GYRUS4 = rel( 65, 130), rel( 85, 140), rel(105,158), rel(118,175)
GYRUS5 = rel( 58, 152), rel( 78, 162), rel( 96,174), rel(106,186)

# ========== 渲染 ==========

def render_brain(size=1024):
    S = size/512
    canvas = Image.new("RGBA", (size, size), (0,0,0,0))

    # ---- 背景 ----
    bg = Image.new("RGBA", (size, size), (10, 13, 26, 255))
    bd = ImageDraw.Draw(bg)
    bd.rounded_rectangle([(0,0),(size-1,size-1)], radius=int(80*S), fill=(14, 17, 36, 255))
    # 背景光晕
    gl = Image.new("RGBA", (size,size), (0,0,0,0))
    gd = ImageDraw.Draw(gl)
    gd.ellipse([int(96*S),int(80*S),int(416*S),int(390*S)], fill=(0,102,255,22))
    bg.alpha_composite(gl.filter(ImageFilter.GaussianBlur(int(40*S))), (0,0))
    canvas = bg

    CYAN = (  0, 212, 255)
    BLUE = ( 77, 166, 255)
    PURP = (109,  40, 217)
    WHITE= (255, 255, 255)
    BG0  = ( 10,  13,  26)

    # ---- 大脑整体发光 ----
    glow_layer = Image.new("RGBA", canvas.size, (0,0,0,0))
    gd2 = ImageDraw.Draw(glow_layer)
    gd2.ellipse([int(136*S),int(80*S),int(376*S),int(390*S)], fill=(0,180,255,35))
    canvas.alpha_composite(glow_layer.filter(ImageFilter.GaussianBlur(int(20*S))), (0,0))

    # ---- 左半球 ----
    def fill_polygon(canvas, pts, color, blur_r=6):
        ov = Image.new("RGBA", canvas.size, (0,0,0,0))
        od = ImageDraw.Draw(ov)
        od.polygon(pts, fill=(*color, 240))
        canvas.alpha_composite(ov.filter(ImageFilter.GaussianBlur(int(blur_r*S))), (0,0))
        od2 = ImageDraw.Draw(canvas)
        od2.polygon(pts, fill=(*color, 230))

    fill_polygon(canvas, LEFT_HEM, CYAN)
    fill_polygon(canvas, CORPUS,  BG0)
    fill_polygon(canvas, CEREB,   BLUE)
    fill_polygon(canvas, STEM,    PURP)

    # ---- 皮层纹理 ----
    def draw_gyrus(canvas, g, color, w=2, gr=3):
        p0,p1,p2,p3 = g
        draw_bezier_curve(canvas, p0,p1,p2,p3, color, width=int(w*S), steps=25, glow_r=int(gr*S))

    draw_gyrus(canvas, GYRUS1, WHITE, w=2.5, gr=3)
    draw_gyrus(canvas, GYRUS2, WHITE, w=2.5, gr=3)
    draw_gyrus(canvas, GYRUS3, WHITE, w=2.0, gr=3)
    draw_gyrus(canvas, GYRUS4, WHITE, w=1.8, gr=2.5)
    draw_gyrus(canvas, GYRUS5, WHITE, w=1.5, gr=2.5)

    # ---- 中线 ----
    draw_glow_line(canvas, int(236*S), int(110*S), int(236*S), int(378*S),
                   BG0, width=int(3*S), glow_r=int(2*S))

    # ---- 文字 ----
    try:
        font_main = ImageFont.truetype("arial.ttf", int(38*S))
        font_sub  = ImageFont.truetype("arial.ttf", int(14*S))
    except:
        font_main = ImageFont.load_default()
        font_sub  = ImageFont.load_default()

    # 阴影
    shadow = Image.new("RGBA", canvas.size, (0,0,0,0))
    ImageDraw.Draw(shadow).text((int(258*S), int(412*S)), "HyperMarrow",
                                  font=font_main, anchor="mm", fill=(0,0,0,80))
    canvas.alpha_composite(shadow, (0,0))

    td = ImageDraw.Draw(canvas)
    td.text((int(256*S), int(412*S)), "HyperMarrow",
            font=font_main, anchor="mm", fill=(224, 242, 254))
    td.text((int(256*S), int(442*S)), "\u7c7b\u4eba\u8bb0\u5fc6\u4e0e\u5b66\u4e60\u7cfb\u7edf",
            font=font_sub, anchor="mm", fill=(100, 116, 139))
    return canvas

# ========== 主程序 ==========
if __name__ == "__main__":
    for sz, fname in [(1024,"hypermarrow_brain_1024.png"),(512,"hypermarrow_brain_512.png")]:
        out = os.path.join(BRAND_DIR, fname)
        print(f"Rendering {sz}px...")
        img = render_brain(sz)
        img.save(out, "PNG", optimize=True)
        print(f"[OK] {fname} ({os.path.getsize(out)//1024}KB)")
    print("Done.")
