"""
UIA元素识别模块 - 使用pywinauto识别窗口内可点击元素
Author: windai@qq.com 上杉
"""
import time

try:
    from pywinauto import Application, Desktop
    from pywinauto.controls.uiawrapper import UIAWrapper
    HAS_PYWINAUTO = True
except ImportError:
    HAS_PYWINAUTO = False


def get_window_list():
    """获取当前所有顶层窗口列表"""
    if not HAS_PYWINAUTO:
        return []
    windows = []
    try:
        desktop = Desktop(backend="uia")
        for w in desktop.windows():
            try:
                title = w.window_text()
                if title and w.is_visible() and w.rectangle() != (0, 0, 0, 0):
                    windows.append({
                        "title": title,
                        "handle": w.handle,
                        "rect": w.rectangle()
                    })
            except Exception:
                continue
    except Exception:
        pass
    return windows


def find_clickable_elements(window_title=None, window_handle=None):
    """识别窗口内所有可点击元素"""
    if not HAS_PYWINAUTO:
        return []
    elements = []
    try:
        if window_handle:
            app = Application(backend="uia").connect(handle=window_handle)
            win = app.window(handle=window_handle)
        elif window_title:
            app = Application(backend="uia").connect(title=window_title)
            win = app.window(title=window_title)
        else:
            return elements

        # 遍历所有子元素，找可点击的
        def walk(element, depth=0):
            if depth > 10:  # 防止过深递归
                return
            try:
                if element.is_visible() and element.is_enabled():
                    ctrl_type = element.element_info.control_type
                    name = element.element_info.name or ""
                    rect = element.rectangle()
                    # 可点击控件类型
                    clickable_types = [
                        "Button", "MenuItem", "Hyperlink",
                        "CheckBox", "RadioButton", "ComboBox"
                    ]
                    if ctrl_type in clickable_types and rect != (0, 0, 0, 0):
                        elements.append({
                            "name": name,
                            "control_type": ctrl_type,
                            "rect": rect,
                            "x": (rect.left + rect.right) // 2,
                            "y": (rect.top + rect.bottom) // 2,
                            "automation_id": element.element_info.automation_id or "",
                            "class_name": element.element_info.class_name or ""
                        })
            except Exception:
                pass
            try:
                for child in element.children():
                    walk(child, depth + 1)
            except Exception:
                pass

        walk(win)
    except Exception as e:
        print(f"UIA识别错误: {e}")
    return elements


def click_uia_element(window_title, element_info, click_type="left_click"):
    """通过UIA元素坐标进行点击（使用pyautogui，更精确）"""
    if not HAS_PYWINAUTO:
        return False
    try:
        # 优先使用保存的坐标点击
        if "x" in element_info and "y" in element_info:
            return click_by_coordinate(element_info["x"], element_info["y"], click_type)
        
        # 降级：用UIA原生点击
        app = Application(backend="uia").connect(title=window_title)
        win = app.window(title=window_title)
        
        target = None
        if element_info.get("automation_id"):
            target = win.child_window(
                auto_id=element_info["automation_id"],
                control_type=element_info["control_type"]
            )
        elif element_info.get("name"):
            target = win.child_window(
                title=element_info["name"],
                control_type=element_info["control_type"]
            )
        
        if target:
            target.click_input()
            return True
    except Exception as e:
        print(f"UIA点击失败: {e}")
    return False


def click_by_coordinate(x, y, click_type="left_click", drag_to=None):
    """通过坐标点击"""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False

        if click_type == "left_click":
            pyautogui.click(x, y, button="left")
        elif click_type == "left_double":
            pyautogui.doubleClick(x, y, button="left")
        elif click_type == "right_click":
            pyautogui.click(x, y, button="right")
        elif click_type == "drag" and drag_to:
            pyautogui.dragTo(drag_to[0], drag_to[1], duration=0.5, button="left")
        return True
    except Exception as e:
        print(f"坐标点击失败: {e}")
        return False
