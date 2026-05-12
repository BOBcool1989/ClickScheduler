"""
配置管理模块 - 保存/加载ClickScheduler配置
Author: windai@qq.com 上杉
"""
import json
import os

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", ""), "ClickScheduler")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "time_range": {
        "start": "09:00",
        "end": "17:00"
    },
    "click_mode": "coordinate",  # coordinate | uia
    "coordinates": [],  # [{x, y, description}]
    "uia_target": None,  # {window_title, element_info}
    "click_type": "left_click",  # left_click | left_double | right_click | drag
    "interval": 60,  # 秒
    "interval_unit": "seconds",  # seconds | minutes | hours
    "max_clicks": 0,  # 0 = 无限
    "enabled": False,
    "autostart": False,
    "minimize_to_tray": True
}


def ensure_config_dir():
    """确保配置目录存在"""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config():
    """加载配置，不存在则返回默认配置"""
    ensure_config_dir()
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        # 合并缺失的键（兼容旧配置）
        for key, val in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = val
        return config
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置到文件"""
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
