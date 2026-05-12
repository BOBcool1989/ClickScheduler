"""
坐标抓取模块 - 全屏遮罩 + 鼠标坐标实时显示
Author: windai@qq.com 上杉
"""
import tkinter as tk
from tkinter import messagebox


class CoordinatePicker:
    """全屏透明窗口，实时显示鼠标坐标，点击获取坐标"""

    def __init__(self, callback=None):
        self.callback = callback  # (x, y) -> None
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black")
        self.root.attributes("-alpha", 0.3)  # 半透明

        # 取消全屏的提示标签
        self.label = tk.Label(
            self.root,
            text="移动鼠标到目标位置，点击左键获取坐标，右键或ESC取消",
            font=("微软雅黑", 14),
            bg="yellow",
            fg="black",
            padx=20,
            pady=10
        )
        self.label.place(x=0, y=0)

        # 坐标显示标签（跟随鼠标）
        self.coord_label = tk.Label(
            self.root,
            text="",
            font=("Consolas", 16, "bold"),
            bg="red",
            fg="white",
            padx=10,
            pady=5
        )

        self.root.bind("<Motion>", self.on_motion)
        self.root.bind("<Button-1>", self.on_click)
        self.root.bind("<Button-3>", self.on_cancel)
        self.root.bind("<Escape>", self.on_cancel)
        # 禁止关闭按钮
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

    def on_motion(self, event):
        x, y = event.x_root, event.y_root
        text = f"X={x}, Y={y}"
        self.coord_label.config(text=text)
        # 标签跟随鼠标（偏移到右下方）
        self.coord_label.place(x=x + 15, y=y + 15)

    def on_click(self, event):
        x, y = event.x_root, event.y_root
        self.root.destroy()
        if self.callback:
            self.callback(x, y)

    def on_cancel(self, event=None):
        self.root.destroy()
        if self.callback:
            self.callback(None, None)

    def run(self):
        self.root.mainloop()


def pick_coordinate(callback):
    """启动坐标抓取，结果通过callback(x, y)返回"""
    picker = CoordinatePicker(callback)
    picker.run()


class MultiCoordinatePicker:
    """多坐标抓取 - 支持添加多个坐标点"""

    def __init__(self, callback=None):
        self.callback = callback  # ([(x,y,desc), ...]) -> None
        self.points = []
        self.root = tk.Tk()
        self.root.title("多坐标抓取")
        self.root.geometry("400x500")
        self.root.attributes("-topmost", True)

        tk.Label(self.root, text="点击'开始抓取'，然后在目标位置点击左键\n右键或ESC结束抓取",
                 font=("微软雅黑", 10)).pack(pady=5)

        self.btn_start = tk.Button(self.root, text="开始抓取",
                                    command=self.start_picking,
                                    bg="#4CAF50", fg="white",
                                    font=("微软雅黑", 10))
        self.btn_start.pack(pady=5)

        self.listbox = tk.Listbox(self.root, width=50, height=15)
        self.listbox.pack(pady=5, fill="both", expand=True)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="删除选中", command=self.delete_selected,
                  bg="#f44336", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="清空列表", command=self.clear_list,
                  bg="#FF9800", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="完成", command=self.finish,
                  bg="#2196F3", fg="white").pack(side="left", padx=5)

        self.picking = False
        self.picker_window = None

    def start_picking(self):
        self.picking = True
        self.btn_start.config(state="disabled", text="抓取中...")
        self.root.withdraw()  # 隐藏主窗口
        self._show_picker()

    def _show_picker(self):
        """显示全屏抓取窗口"""
        pw = tk.Toplevel()
        pw.attributes("-fullscreen", True)
        pw.attributes("-topmost", True)
        pw.configure(bg="black")
        pw.attributes("-alpha", 0.3)

        lbl = tk.Label(pw, text=f"已记录 {len(self.points)} 个点 | 左键添加 | 右键/ESC完成",
                       font=("微软雅黑", 14), bg="yellow", fg="black", padx=20, pady=10)
        lbl.place(x=0, y=0)

        coord_lbl = tk.Label(pw, text="", font=("Consolas", 16, "bold"),
                              bg="red", fg="white", padx=10, pady=5)
        pw.bind("<Motion>", lambda e: self._on_picker_motion(e, coord_lbl, pw))
        pw.bind("<Button-1>", lambda e: self._on_picker_click(e, pw))
        pw.bind("<Button-3>", lambda e: self._finish_picking(pw))
        pw.bind("<Escape>", lambda e: self._finish_picking(pw))
        pw.focus_set()

    def _on_picker_motion(self, event, label, window):
        x, y = event.x_root, event.y_root
        label.config(text=f"X={x}, Y={y}")
        label.place(x=x + 15, y=y + 15)

    def _on_picker_click(self, event, window):
        x, y = event.x_root, event.y_root
        desc = f"点{len(self.points) + 1}"
        self.points.append((x, y, desc))
        self.listbox.insert("end", f"X={x}, Y={y} ({desc})")
        window.destroy()
        # 继续抓取下一个
        self.root.after(200, self._show_picker)

    def _finish_picking(self, window):
        window.destroy()
        self.picking = False
        self.btn_start.config(state="normal", text="继续添加")
        self.root.deiconify()

    def delete_selected(self):
        sel = self.listbox.curselection()
        for i in reversed(sel):
            self.listbox.delete(i)
            self.points.pop(i)

    def clear_list(self):
        self.listbox.delete(0, "end")
        self.points.clear()
        self.btn_start.config(text="开始抓取")

    def finish(self):
        self.root.destroy()
        if self.callback:
            self.callback(self.points)


def pick_multiple_coordinates(callback):
    """抓取多个坐标点"""
    app = MultiCoordinatePicker(callback)
    app.root.mainloop()


if __name__ == "__main__":
    # 测试
    def on_result(x, y):
        print(f"坐标: ({x}, {y})")

    def on_multi_result(points):
        print("多点坐标:", points)

    # pick_coordinate(on_result)
    pick_multiple_coordinates(on_multi_result)
