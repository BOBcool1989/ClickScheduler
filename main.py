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
from uia_helper import get_window_list, find_clickable_elements, HAS_PYWINAUTO
from uia_picker import pick_uia_element
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
        self.window_list = []
        self.elements = []

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

        # Tab3: UIA模式
        tab3 = ttk.Frame(notebook)
        notebook.add(tab3, text="UIA模式")
        self._build_uia_tab(tab3)

        # Tab4: 设置
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

    def _build_uia_tab(self, parent):
        """UIA模式Tab"""
        if not HAS_PYWINAUTO:
            ttk.Label(parent, text="pywinauto 未安装，UIA模式不可用\n请运行: pip install pywinauto",
                       foreground="red", font=("微软雅黑", 10)).pack(pady=20)
            return

        ttk.Label(parent, text="UIA模式：识别窗口内元素并点击",
                   font=("微软雅黑", 10, "bold")).pack(pady=5)

        # 窗口选择
        win_frame = ttk.Frame(parent)
        win_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(win_frame, text="目标窗口:").pack(side="left", padx=5)
        self.window_var = tk.StringVar()
        self.window_combo = ttk.Combobox(win_frame, textvariable=self.window_var,
                                            width=40, state="readonly")
        self.window_combo.pack(side="left", padx=5)
        ttk.Button(win_frame, text="刷新窗口列表",
                    command=self.refresh_windows).pack(side="left", padx=5)

        # 元素列表
        ttk.Label(parent, text="可点击元素 (点击列表可查看坐标):").pack(anchor="w", padx=10)
        self.element_listbox = tk.Listbox(parent, width=60, height=10)
        self.element_listbox.pack(fill="both", expand=True, padx=10, pady=5)
        self.element_listbox.bind("<<ListboxSelect>>", self.on_element_select)

        # 坐标显示
        self.element_coord_var = tk.StringVar(value="选中元素坐标: 无")
        ttk.Label(parent, textvariable=self.element_coord_var,
                   foreground="green", font=("Consolas", 10)).pack(padx=10)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="识别元素",
                    command=self.recognize_elements).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="可视化选择元素",
                    command=self.visual_pick_element).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="使用选中元素",
                    command=self.use_selected_element).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="测试点击",
                    command=self.test_click_element).pack(side="left", padx=5)

        # 当前选择
        self.uia_status_var = tk.StringVar(value="未选择元素")
        ttk.Label(parent, textvariable=self.uia_status_var,
                   foreground="blue").pack(pady=5)

        # 加载已有配置
        if self.config.get("uia_target"):
            self.uia_status_var.set(f"当前目标: {self.config['uia_target']['window_title']}")

        # 初始刷新窗口
        self.refresh_windows()

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
        ttk.Label(about_frame, text="ClickScheduler v1.0\n定时点击工具\n支持坐标+UIA双模式",
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

    def refresh_windows(self):
        """刷新窗口列表"""
        windows = get_window_list()
        self.window_list = windows
        titles = [w["title"] for w in windows]
        self.window_combo["values"] = titles
        if titles:
            self.window_combo.current(0)

    def recognize_elements(self):
        """识别选中窗口的元素"""
        idx = self.window_combo.current()
        if idx < 0 or not hasattr(self, 'window_list'):
            messagebox.showwarning("警告", "请先选择窗口")
            return
        window = self.window_list[idx]
        self.element_listbox.delete(0, "end")
        self.elements = find_clickable_elements(window_handle=window["handle"])
        for el in self.elements:
            name = el["name"] or "(无名称)"
            self.element_listbox.insert("end", f"{el['control_type']}: {name} [{el['x']},{el['y']}]")

    def use_selected_element(self):
        """使用选中的元素"""
        sel = self.element_listbox.curselection()
        if not sel or not hasattr(self, 'elements'):
            messagebox.showwarning("警告", "请先识别并选择元素")
            return
        idx = sel[0]
        element = self.elements[idx]
        window_title = self.window_var.get()
        self.config["uia_target"] = {
            "window_title": window_title,
            "element": element
        }
        self.config["click_mode"] = "uia"
        self.uia_status_var.set(f"当前目标: {window_title} - {element['name'] or element['control_type']} [X={element['x']}, Y={element['y']}]")
        self.save_current_config()
        messagebox.showinfo("成功", f"UIA目标已设置\n点击位置: X={element['x']}, Y={element['y']}")

    def on_element_select(self, event):
        """当选中元素时，显示其坐标"""
        sel = self.element_listbox.curselection()
        if not sel or not hasattr(self, 'elements'):
            return
        idx = sel[0]
        element = self.elements[idx]
        x, y = element["x"], element["y"]
        name = element["name"] or "(无名称)"
        self.element_coord_var.set(f"选中元素坐标: X={x}, Y={y}  ({name})")

    def test_click_element(self):
        """测试点击选中元素（用坐标点击）"""
        sel = self.element_listbox.curselection()
        if not sel or not hasattr(self, 'elements'):
            messagebox.showwarning("警告", "请先识别并选择元素")
            return
        idx = sel[0]
        element = self.elements[idx]
        x, y = element["x"], element["y"]
        
        from uia_helper import click_by_coordinate
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.click(x, y)
            messagebox.showinfo("测试点击", f"已点击坐标:\nX={x}, Y={y}")
        except Exception as e:
            messagebox.showerror("错误", f"测试点击失败: {e}")

    def visual_pick_element(self):
        """启动可视化UIA元素选择"""
        if not HAS_PYWINAUTO:
            messagebox.showerror("错误", "pywinauto 未安装")
            return
        
        # 获取当前选中的窗口
        idx = self.window_combo.current()
        window_title = self.window_var.get()
        window_handle = None
        if idx >= 0 and hasattr(self, 'window_list') and idx < len(self.window_list):
            window_handle = self.window_list[idx]["handle"]
        
        def callback(elem_info):
            if elem_info:
                self.config["uia_target"] = {
                    "window_title": window_title,
                    "element": elem_info
                }
                self.config["click_mode"] = "uia"
                x, y = elem_info["x"], elem_info["y"]
                name = elem_info.get("name") or elem_info.get("control_type", "")
                self.uia_status_var.set(f"当前目标: {window_title} - {name} [X={x}, Y={y}]")
                self.save_current_config()
                messagebox.showinfo("成功", f"UIA目标已设置\n名称: {name}\n坐标: X={x}, Y={y}")
            else:
                messagebox.showinfo("取消", "已取消可视化选择")
        
        # 在主线程中启动（需要在有Tkinter主循环的环境中）
        pick_uia_element(callback, window_handle=window_handle, window_title=window_title)

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

        # 如果坐标列表有内容，设置为坐标模式
        if self.config.get("coordinates"):
            self.config["click_mode"] = "coordinate"
        elif self.config.get("uia_target"):
            self.config["click_mode"] = "uia"

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
