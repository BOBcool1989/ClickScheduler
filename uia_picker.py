"""
可视化UIA元素选择器 - 鼠标移动到元素上自动高亮，点击选中
Author: windai@qq.com 上杉
"""
import tkinter as tk
from tkinter import font

try:
    from pywinauto import Desktop
    HAS_PYWINAUTO = True
except ImportError:
    HAS_PYWINAUTO = False


class VisualElementPicker:
    """
    可视化元素选择器：
    - 全屏半透明遮罩
    - 鼠标移动时自动获取下方窗口的元素并高亮
    - 左键点击选中元素，右键/ESC取消
    """

    def __init__(self, callback=None, window_handle=None, window_title=None):
        self.callback = callback  # 回调：(element_info_dict) -> None
        self.window_handle = window_handle
        self.window_title = window_title
        self.picking = False
        self.last_element = None
        self.root = None
        self.overlay = None
        self.highlight_win = None
        self.info_win = None

    def start_picking(self):
        """启动可视化选择"""
        if not HAS_PYWINAUTO:
            if self.callback:
                self.callback(None)
            return

        self.picking = True
        self.root = tk.Tk()
        self.root.withdraw()  # 隐藏主窗口

        # 创建全屏半透明遮罩（用来捕捉鼠标事件）
        self.overlay = tk.Toplevel(self.root)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-alpha", 0.15)
        self.overlay.configure(bg="gray20")
        self.overlay.overrideredirect(True)
        self.overlay.config(cursor="crosshair")

        # 提示标签
        hint = tk.Label(
            self.overlay,
            text="🖱 移动鼠标到目标元素上 | 左键选中 | 右键/ESC取消",
            font=("微软雅黑", 13, "bold"),
            bg="#2196F3",
            fg="white",
            padx=20,
            pady=8
        )
        hint.place(x=0, y=0)

        # 元素信息显示窗口（固定在左上角）
        self.info_win = tk.Toplevel(self.overlay)
        self.info_win.overrideredirect(True)
        self.info_win.attributes("-topmost", True)
        self.info_win.configure(bg="#222222")
        self.info_text = tk.Text(
            self.info_win,
            width=55,
            height=6,
            bg="#222222",
            fg="#00FF7F",
            font=("Consolas", 9),
            relief="flat",
            padx=8,
            pady=5
        )
        self.info_text.pack()
        self.info_win.withdraw()  # 初始隐藏

        # 高亮窗口（蓝色边框，无背景）
        self.highlight_win = tk.Toplevel(self.overlay)
        self.highlight_win.overrideredirect(True)
        self.highlight_win.attributes("-topmost", True)
        self.highlight_win.configure(bg="systemTransparent")
        self.highlight_win.attributes("-alpha", 0.7)
        # 用 Frame 画边框
        self.highlight_frame = tk.Frame(
            self.highlight_win,
            bg="systemTransparent",
            highlightbackground="#2196F3",
            highlightthickness=3
        )
        self.highlight_frame.pack(fill="both", expand=True)
        self.highlight_win.withdraw()

        # 绑定事件
        self.overlay.bind("<Motion>", self._on_motion)
        self.overlay.bind("<Button-1>", self._on_left_click)
        self.overlay.bind("<Button-3>", self._on_right_click)
        self.overlay.bind("<Escape>", self._on_right_click)
        self.overlay.focus_set()

        self.root.mainloop()

    def _on_motion(self, event):
        """鼠标移动：获取元素并高亮"""
        if not self.picking:
            return
        try:
            x, y = event.x_root, event.y_root
            desktop = Desktop(backend="uia")
            elem = desktop.from_point(x, y)
            if elem is None:
                self._hide_highlight()
                return

            self.last_element = elem
            rect = elem.rectangle()

            # 过滤无效矩形
            if rect.left == rect.right or rect.top == rect.bottom:
                self._hide_highlight()
                return

            # 移动高亮窗口到元素位置
            self._show_highlight(rect)

            # 显示元素信息
            self._show_element_info(elem, rect)
        except Exception as e:
            pass  # 忽略 transient 错误

    def _show_highlight(self, rect):
        """显示高亮边框"""
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return
        geo = f"{w}x{h}+{rect.left}+{rect.top}"
        self.highlight_win.geometry(geo)
        self.highlight_win.deiconify()
        self.highlight_win.lift()

    def _hide_highlight(self):
        """隐藏高亮"""
        try:
            self.highlight_win.withdraw()
            self.info_win.withdraw()
        except Exception:
            pass

    def _show_element_info(self, elem, rect):
        """在元素旁边显示元素信息"""
        try:
            info = []
            info.append(f"类型: {elem.element_info.control_type}")
            name = elem.element_info.name or '(无名称)'
            info.append(f"名称: {name}")
            info.append(f"坐标: X={rect.left}, Y={rect.top}")
            info.append(f"大小: {rect.right - rect.left} x {rect.bottom - rect.top}")
            aid = elem.element_info.automation_id or '(无)'
            info.append(f"AutomationId: {aid}")

            self.info_text.delete("1.0", "end")
            self.info_text.insert("1.0", "\n".join(info))

            # 信息窗口放在元素右侧（如果空间不够就放左侧）
            info_x = rect.right + 10
            info_y = rect.top
            screen_w = self.root.winfo_screenwidth()
            info_w = 400
            if info_x + info_w > screen_w:
                info_x = rect.left - info_w - 10
            if info_x < 0:
                info_x = 10
            self.info_win.geometry(f"+{info_x}+{info_y}")
            self.info_win.deiconify()
            self.info_win.lift()
        except Exception:
            pass

    def _on_left_click(self, event):
        """左键点击：选中当前元素"""
        if self.last_element is not None:
            elem = self.last_element
            rect = elem.rectangle()
            elem_info = {
                "name": elem.element_info.name or "",
                "control_type": elem.element_info.control_type,
                "x": (rect.left + rect.right) // 2,
                "y": (rect.top + rect.bottom) // 2,
                "rect": {
                    "left": rect.left, "top": rect.top,
                    "right": rect.right, "bottom": rect.bottom
                },
                "automation_id": elem.element_info.automation_id or "",
                "class_name": elem.element_info.class_name or ""
            }
            self._cleanup()
            if self.callback:
                self.callback(elem_info)
        else:
            self._cleanup()
            if self.callback:
                self.callback(None)

    def _on_right_click(self, event=None):
        """右键/ESC：取消"""
        self._cleanup()
        if self.callback:
            self.callback(None)

    def _cleanup(self):
        """清理资源"""
        self.picking = False
        try:
            if self.overlay:
                self.overlay.destroy()
            if self.root:
                self.root.destroy()
        except Exception:
            pass


def pick_uia_element(callback, window_handle=None, window_title=None):
    """
    启动可视化UIA元素选择
    callback: 回调函数，接收 element_info_dict 或 None
    """
    picker = VisualElementPicker(callback, window_handle, window_title)
    picker.start_picking()


if __name__ == "__main__":
    def on_result(elem_info):
        if elem_info:
            print("选中元素：")
            print(f"  名称: {elem_info['name']}")
            print(f"  类型: {elem_info['control_type']}")
            print(f"  坐标: ({elem_info['x']}, {elem_info['y']})")
        else:
            print("已取消")

    print("请在弹出的遮罩中移动鼠标选择元素...")
    pick_uia_element(on_result)
