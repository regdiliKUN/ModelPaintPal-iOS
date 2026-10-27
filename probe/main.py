# -*- coding: utf-8 -*-
"""iOS 探针：证明 Python + Kivy + Pillow 能在 iPhone 上真的跑起来。

这个工程里没有任何业务代码，它只回答四个问题，屏幕上那几行字就是答案：

1. kivy-ios 在 Xcode 26 / iOS 26 SDK 下能不能编出可安装、可启动的包；
2. 中文能不能显示（自带 NotoSansSC，不指望系统字体回退）；
3. Pillow 能不能真的打开图片、取到像素——取色功能的命根子；
4. 触摸坐标是不是屏幕坐标。Android 端在这件事上栽过三次，iOS 必须先验。

最后一条尤其要紧：Android 上 ``touch.pos`` 会被滚动容器平移、``touch.sx/sy``
才是归一化屏幕坐标，两条路对不上就会「点左边、取右边」。这里把 pos 和
sx·sy 同时打在屏幕上，截图就能看出来它们是不是同一套坐标。
"""

from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime

import kivy
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import Metrics, dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget


# ----------------------------------------------------------------- 字体定位
# iOS 上进程的工作目录就是 app 目录，但 ``__file__`` 不一定被定义
# （kivy-ios 用 exec 跑 main.py），所以两条路都试。
_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()

_FONT_CANDIDATES = (
    os.path.join("assets", "fonts", "NotoSansSC-Regular.otf"),
    os.path.join(_HERE, "assets", "fonts", "NotoSansSC-Regular.otf"),
)


def _pick_font():
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


FONT = _pick_font()

BG = (0.07, 0.08, 0.10, 1)
TEXT = (0.88, 0.90, 0.94, 1)
DIM = (0.55, 0.58, 0.64, 1)
ACCENT = (0.29, 0.62, 1.0, 1)


class Line(Label):
    """固定高度的一行状态文字。"""

    def __init__(self, text="", color=TEXT, size=14, **kwargs):
        kwargs.setdefault("font_name", FONT)
        kwargs.setdefault("font_size", sp(size))
        kwargs.setdefault("color", color)
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(26))
        super().__init__(text=text, **kwargs)
        self.bind(size=lambda inst, val: setattr(inst, "text_size", val))


class Strip(Widget):
    """一条会被触摸染色的色带：既是绘制能力的证明，也是触摸命中的可视化。"""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(56))
        super().__init__(**kwargs)
        with self.canvas:
            self._color = Color(0.20, 0.42, 0.75, 1)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def paint(self, rgba):
        self._color.rgba = rgba


class ProbeApp(App):
    title = "ModelPaintPal iOS 探针"

    def build(self):
        Window.clearcolor = BG

        root = BoxLayout(
            orientation="vertical",
            padding=[dp(18), dp(64), dp(18), dp(36)],
            spacing=dp(4),
        )

        root.add_widget(Line("ModelPaintPal", color=ACCENT, size=24))
        root.add_widget(Line("iOS 探针 · 环境自检", color=DIM, size=13))
        root.add_widget(Widget(size_hint_y=None, height=dp(10)))

        self.kivy_line = Line("Kivy …")
        self.py_line = Line("Python …")
        self.pil_line = Line("Pillow …")
        self.win_line = Line("窗口 …")
        self.store_line = Line("存储 …")
        self.font_line = Line("字体 …")
        self.up_line = Line("运行 …", color=DIM, size=12)

        for widget in (
            self.kivy_line,
            self.py_line,
            self.pil_line,
            self.win_line,
            self.store_line,
            self.font_line,
        ):
            root.add_widget(widget)

        root.add_widget(Widget(size_hint_y=None, height=dp(8)))
        self.strip = Strip()
        root.add_widget(self.strip)
        root.add_widget(Widget(size_hint_y=None, height=dp(12)))

        self.touch_line = Line("触摸：尚未点击", color=DIM, size=13)
        self.norm_line = Line("归一化：—", color=DIM, size=13)
        root.add_widget(self.touch_line)
        root.add_widget(self.norm_line)

        root.add_widget(Widget())
        root.add_widget(self.up_line)

        Clock.schedule_once(self._fill, 0.2)
        self._ticks = 0
        Clock.schedule_interval(self._tick, 1.0)
        return root

    # ------------------------------------------------------------------ 自检
    def _fill(self, *_dt):
        self.kivy_line.text = f"Kivy {kivy.__version__}"
        self.py_line.text = f"Python {sys.version.split()[0]}"

        try:
            import PIL
            from PIL import Image

            size = (4, 4)
            img = Image.new("RGB", size, (12, 200, 90))
            img = img.resize((64, 64))
            pixel = img.getpixel((32, 32))
            self.pil_line.text = f"Pillow {PIL.__version__} · 取样 {pixel}"
            self._verified_pillow = True
        except Exception as exc:  # pragma: no cover - 探针现场才触发
            self.pil_line.text = f"Pillow 失败 · {type(exc).__name__}: {exc}"
            self.pil_line.color = (1.0, 0.42, 0.42, 1)
            self._verified_pillow = False

        self.win_line.text = (
            f"窗口 {int(Window.width)}×{int(Window.height)}"
            f" · dpi {Window.dpi:.0f} · 密度 {Metrics.density:.2f}"
        )

        self._probe_storage()

        if FONT:
            self.font_line.text = f"字体 {os.path.basename(FONT)}"
        else:
            self.font_line.text = "字体 未找到，中文会显示成方框"
            self.font_line.color = (1.0, 0.42, 0.42, 1)

    def _probe_storage(self):
        try:
            base = self.user_data_dir
            os.makedirs(base, exist_ok=True)
            probe = os.path.join(base, "probe.txt")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write(datetime.now().isoformat())
            with open(probe, encoding="utf-8") as handle:
                handle.read()
            self.store_line.text = f"存储 可读写 · …{base[-28:]}"
        except Exception as exc:  # pragma: no cover
            self.store_line.text = f"存储 失败 · {type(exc).__name__}: {exc}"
            self.store_line.color = (1.0, 0.42, 0.42, 1)

    def _tick(self, *_dt):
        self._ticks += 1
        self.up_line.text = f"已运行 {self._ticks}s · {datetime.now():%H:%M:%S}"

    # ------------------------------------------------------------------ 触摸
    def on_touch_down(self, touch):
        self.touch_line.text = f"触摸 pos=({touch.x:.0f}, {touch.y:.0f})"
        self.touch_line.color = TEXT

        try:
            sx = touch.sx
            sy = touch.sy
            self.norm_line.text = (
                f"归一化 sx={sx:.3f} sy={sy:.3f}"
                f" → 屏幕 ({sx * Window.width:.0f}, {sy * Window.height:.0f})"
            )
            self.norm_line.color = TEXT
        except Exception:
            self.norm_line.text = "归一化 取不到 sx/sy"

        # 点哪里就把色带染成哪里的颜色：最直白的命中证明
        self.strip.paint((max(0.0, min(1.0, touch.x / max(1.0, Window.width))),
                          0.35,
                          max(0.0, min(1.0, touch.y / max(1.0, Window.height))),
                          1))
        return True


if __name__ == "__main__":
    try:
        ProbeApp().run()
    except Exception:
        traceback.print_exc()
        raise
