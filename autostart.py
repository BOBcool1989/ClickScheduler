"""
开机自启模块 - 通过注册表实现开机自启
Author: windai@qq.com 上杉
"""
import os
import sys

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ClickScheduler"


def get_executable_path():
    """获取当前可执行文件路径"""
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后的exe
        return sys.executable
    else:
        # 脚本模式
        return os.path.abspath(__file__)


def is_autostart_enabled():
    """检查是否已启用开机自启"""
    if not HAS_WINREG:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def enable_autostart():
    """启用开机自启"""
    if not HAS_WINREG:
        return False
    try:
        exe_path = get_executable_path()
        # 添加 --minimized 参数，启动时最小化到托盘
        cmd = f'"{exe_path}" --minimized'
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"启用开机自启失败: {e}")
        return False


def disable_autostart():
    """禁用开机自启"""
    if not HAS_WINREG:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_WRITE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"禁用开机自启失败: {e}")
        return False


def set_autostart(enable):
    """设置开机自启状态"""
    if enable:
        return enable_autostart()
    else:
        return disable_autostart()
