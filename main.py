"""
ClickScheduler 主程序 - 系统托盘 + 主窗口
Author: windai@qq.com 上杉
"""
import sys
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import datetime
import base64
import tempfile

# 添加当前目录到path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import load_config, save_config
from click_engine import ClickEngine
from coordinate_picker import pick_coordinate, pick_multiple_coordinates
from autostart import is_autostart_enabled, set_autostart


def create_tray_icon_image():
    """动态生成托盘图标"""
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 画一个蓝色圆形背景
        draw.ellipse([8, 8, 56, 56], fill="#2196F3")
        # 画白色鼠标指针
        draw.polygon([(32, 12), (20, 44), (30, 36), (42, 48), (36, 36)], fill="white")
        return img
    except Exception as e:
        print(f"创建图标失败: {e}")
        return None


class ClickSchedulerApp:
    def __init__(self, minimized=False):
        self.config = load_config()
        self.engine = ClickEngine()
        self.engine.status_callback = self.on_status_change
        self.tray_icon = None
        self.root = None
        self.minimized = minimized

    def on_status_change(self, msg):
        """状态回调"""
        if hasattr(self, 'status_var'):
            self.status_var.set(msg)

    def create_main_window(self):
        """创建主窗口"""
        self.root = tk.Tk()
        self.root.title("定时点击工具 - ClickScheduler")
        self.root.geometry("680x780")
        self.root.resizable(False, False)

        # 设置图标
        try:
            from PIL import Image, ImageTk
            img = create_tray_icon_image()
            if img:
                tk_img = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, tk_img)
        except Exception:
            pass

        self._build_ui()

        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        if self.minimized:
            self.root.withdraw()
            self.start_tray()
        else:
            self.start_tray()

    def _build_ui(self):
        """构建UI"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab1: 基本设置
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="基本设置")
        self._build_basic_tab(tab1)

        # Tab2: 坐标模式
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text="坐标模式")
        self._build_coordinate_tab(tab2)

        # Tab3: 设置
        tab4 = ttk.Frame(notebook)
        notebook.add(tab4, text="设置")
        self._build_settings_tab(tab4)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var,
                               relief="sunken", anchor="w",
                               font=("微软雅黑", 9))
        status_bar.pack(side="bottom", fill="x")

    def _build_basic_tab(self, parent):
        """基本设置Tab"""
        # 时间范围
        time_frame = ttk.LabelFrame(parent, text="时间范围")
        time_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(time_frame, text="开始时间:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.start_time_var = tk.StringVar(value=self.config["time_range"]["start"])
        ttk.Entry(time_frame, textvariable=self.start_time_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(time_frame, text="结束时间:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.end_time_var = tk.StringVar(value=self.config["time_range"]["end"])
        ttk.Entry(time_frame, textvariable=self.end_time_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(time_frame, text="(格式: HH:MM)").grid(row=0, column=4, padx=5, pady=5)

        # 点击类型
        click_frame = ttk.LabelFrame(parent, text="点击类型")
        click_frame.pack(fill="x", padx=10, pady=5)

        self.click_type_var = tk.StringVar(value=self.config["click_type"])
        types = [
            ("左键单击", "left_click"),
            ("左键双击", "left_double"),
            ("右键单击", "right_click"),
            ("拖拽", "drag")
        ]
        for i, (text, val) in enumerate(types):
            ttk.Radiobutton(click_frame, text=text, variable=self.click_type_var,
                              value=val).grid(row=0, column=i, padx=10, pady=5)

        # 执行频率
        freq_frame = ttk.LabelFrame(parent, text="执行频率")
        freq_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(freq_frame, text="间隔:").grid(row=0, column=0, padx=5, pady=5)
        self.interval_var = tk.IntVar(value=self.config["interval"])
        ttk.Entry(freq_frame, textvariable=self.interval_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        self.interval_unit_var = tk.StringVar(value=self.config["interval_unit"])
        ttk.Combobox(freq_frame, textvariable=self.interval_unit_var,
                       values=["seconds", "minutes", "hours"],
                       state="readonly", width=10).grid(row=0, column=2, padx=5, pady=5)

        # 点击次数
        count_frame = ttk.LabelFrame(parent, text="点击次数")
        count_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(count_frame, text="最大次数 (0=无限):").grid(row=0, column=0, padx=5, pady=5)
        self.max_clicks_var = tk.IntVar(value=self.config.get("max_clicks", 0))
        ttk.Entry(count_frame, textvariable=self.max_clicks_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        # 控制按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", padx=10, pady=10)

        self.toggle_btn = ttk.Button(btn_frame, text="启用", command=self.toggle_engine)
        self.toggle_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="保存配置", command=self.save_current_config).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="最小化到托盘", command=self.minimize_to_tray).pack(side="left", padx=5)

    def _build_coordinate_tab(self, parent):
        """坐标模式Tab"""
        ttk.Label(parent, text="坐标模式：在指定屏幕坐标处点击",
                   font=("微软雅黑", 10, "bold")).pack(pady=5)

        # 坐标列表
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.coord_listbox = tk.Listbox(list_frame, width=60, height=10)
        self.coord_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, command=self.coord_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.coord_listbox.config(yscrollcommand=scrollbar.set)

        # 刷新坐标列表
        self._refresh_coord_list()

        # 按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="添加坐标 (抓取)",
                    command=self.add_coordinate).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="添加坐标 (手动输入)",
                    command=self.manual_add_coordinate).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="删除选中",
                    command=self.delete_coordinate).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="清空列表",
                    command=self.clear_coordinates).pack(side="left", padx=5)

        # 说明
        ttk.Label(parent, text="提示：抓取坐标时会全屏半透明显示，移动鼠标查看坐标，左键点击获取",
                   foreground="gray").pack(pady=5)

    def _build_settings_tab(self, parent):
        """设置Tab"""
        # 开机自启
        autostart_frame = ttk.LabelFrame(parent, text="开机自启")
        autostart_frame.pack(fill="x", padx=10, pady=5)

        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        ttk.Checkbutton(autostart_frame, text="开机时自动启动",
                         variable=self.autostart_var,
                         command=self.toggle_autostart).pack(padx=10, pady=10)

        # 托盘设置
        tray_frame = ttk.LabelFrame(parent, text="托盘设置")
        tray_frame.pack(fill="x", padx=10, pady=5)

        self.minimize_to_tray_var = tk.BooleanVar(value=self.config.get("minimize_to_tray", True))
        ttk.Checkbutton(tray_frame, text="关闭按钮最小化到托盘（不退出）",
                         variable=self.minimize_to_tray_var).pack(padx=10, pady=10)

        # 关于
        about_frame = ttk.LabelFrame(parent, text="关于")
        about_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(about_frame, text="ClickScheduler v1.0\n定时点击工具\n支持坐标模式",
                   justify="center").pack(pady=10)

    def _refresh_coord_list(self):
        """刷新坐标列表显示"""
        self.coord_listbox.delete(0, "end")
        for i, coord in enumerate(self.config.get("coordinates", [])):
            desc = coord.get("description", f"点{i+1}")
            self.coord_listbox.insert("end", f"{desc}: X={coord['x']}, Y={coord['y']}")

    def add_coordinate(self):
        """抓取坐标"""
        def on_result(x, y):
            if x is not None and y is not None:
                desc = simpledialog.askstring("描述", "输入坐标描述（可选）:", parent=self.root)
                if not desc:
                    desc = f"点{len(self.config['coordinates']) + 1}"
                self.config["coordinates"].append({"x": x, "y": y, "description": desc})
                self._refresh_coord_list()
                self.save_current_config()
        pick_coordinate(on_result)

    def manual_add_coordinate(self):
        """手动输入坐标"""
        x_str = simpledialog.askstring("X坐标", "输入X坐标:", parent=self.root)
        if not x_str:
            return
        y_str = simpledialog.askstring("Y坐标", "输入Y坐标:", parent=self.root)
        if not y_str:
            return
        try:
            x, y = int(x_str), int(y_str)
            desc = simpledialog.askstring("描述", "输入坐标描述（可选）:", parent=self.root)
            if not desc:
                desc = f"点{len(self.config['coordinates']) + 1}"
            self.config["coordinates"].append({"x": x, "y": y, "description": desc})
            self._refresh_coord_list()
            self.save_current_config()
        except ValueError:
            messagebox.showerror("错误", "坐标必须是数字")

    def delete_coordinate(self):
        sel = self.coord_listbox.curselection()
        for i in reversed(sel):
            self.config["coordinates"].pop(i)
        self._refresh_coord_list()
        self.save_current_config()

    def clear_coordinates(self):
        self.config["coordinates"] = []
        self._refresh_coord_list()
        self.save_current_config()

    def toggle_autostart(self):
        """切换开机自启"""
        enable = self.autostart_var.get()
        if set_autostart(enable):
            messagebox.showinfo("成功", f"开机自启已{'启用' if enable else '禁用'}")
        else:
            messagebox.showerror("错误", "设置开机自启失败")
            self.autostart_var.set(not enable)

    def toggle_engine(self):
        """切换引擎状态"""
        self.save_current_config()
        result = self.engine.toggle()
        if result == "running":
            self.toggle_btn.config(text="暂停")
        elif result == "paused":
            self.toggle_btn.config(text="恢复")
        else:
            self.toggle_btn.config(text="启用")

    def save_current_config(self):
        """保存当前配置"""
        self.config["time_range"]["start"] = self.start_time_var.get()
        self.config["time_range"]["end"] = self.end_time_var.get()
        self.config["click_type"] = self.click_type_var.get()
        self.config["interval"] = self.interval_var.get()
        self.config["interval_unit"] = self.interval_unit_var.get()
        self.config["max_clicks"] = self.max_clicks_var.get()
        self.config["minimize_to_tray"] = self.minimize_to_tray_var.get()

        # 坐标模式
        self.config["click_mode"] = "coordinate"

        save_config(self.config)
        self.engine.update_config(self.config)
        self.status_var.set("配置已保存")

    def minimize_to_tray(self):
        """最小化到托盘"""
        self.root.withdraw()

    def start_tray(self):
        """启动系统托盘"""
        if self.tray_icon:
            return
        try:
            from pystray import Icon, Menu, MenuItem
            img = create_tray_icon_image()
            if img is None:
                return

            def on_show(icon, item):
                if self.root:
                    self.root.deiconify()
                    self.root.lift()

            def on_toggle(icon, item):
                self.toggle_engine()

            def on_quit(icon, item):
                self.quit_app()

            menu = Menu(
                MenuItem("显示主窗口", on_show),
                MenuItem("启用/暂停", on_toggle),
                Menu.SEPARATOR,
                MenuItem("退出", on_quit)
            )

            self.tray_icon = Icon("ClickScheduler", img, "ClickScheduler", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except ImportError:
            print("pystray 未安装")
        except Exception as e:
            print(f"启动托盘失败: {e}")

    def on_close(self):
        """窗口关闭事件"""
        if self.config.get("minimize_to_tray", True) and self.tray_icon:
            self.root.withdraw()
        else:
            self.quit_app()

    def quit_app(self):
        """退出程序"""
        self.engine.stop()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        if self.root:
            self.root.destroy()
        sys.exit(0)

    def run(self):
        """运行主循环"""
        self.create_main_window()
        if self.root:
            self.root.mainloop()


def main():
    minimized = "--minimized" in sys.argv
    app = ClickSchedulerApp(minimized=minimized)
    app.run()


if __name__ == "__main__":
    main()
