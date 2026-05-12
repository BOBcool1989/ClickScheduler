"""
定时点击执行引擎 - 后台线程定时执行点击
Author: windai@qq.com 上杉
"""
import threading
import time
import datetime
from coordinate_picker import click_by_coordinate
from config_manager import load_config, save_config


class ClickEngine:
    """定时点击引擎，后台线程运行"""

    def __init__(self):
        self.config = load_config()
        self.running = False
        self.paused = False
        self.thread = None
        self.click_count = 0
        self.status_callback = None  # 状态回调 (status_msg) -> None

    def update_config(self, config):
        """更新配置"""
        self.config = config
        save_config(config)

    def _is_in_time_range(self):
        """判断当前时间是否在设定范围内"""
        now = datetime.datetime.now().time()
        start_str = self.config["time_range"]["start"]
        end_str = self.config["time_range"]["end"]

        start_time = datetime.datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.datetime.strptime(end_str, "%H:%M").time()

        if start_time <= end_time:
            return start_time <= now <= end_time
        else:  # 跨午夜的情况（如22:00-06:00）
            return now >= start_time or now <= end_time

    def _get_interval_seconds(self):
        """获取间隔秒数"""
        interval = self.config["interval"]
        unit = self.config["interval_unit"]
        if unit == "seconds":
            return interval
        elif unit == "minutes":
            return interval * 60
        elif unit == "hours":
            return interval * 3600
        return interval

    def _do_click(self):
        """执行一次点击"""
        mode = self.config["click_mode"]
        click_type = self.config["click_type"]

        if mode == "coordinate":
            coords = self.config.get("coordinates", [])
            if not coords:
                return False
            # 按顺序点击所有坐标
            for coord in coords:
                x, y = coord["x"], coord["y"]
                click_by_coordinate(x, y, click_type)
                time.sleep(0.1)
            return True

        return False

    def _run_loop(self):
        """主循环"""
        while self.running:
            if self.paused:
                time.sleep(1)
                continue

            if not self._is_in_time_range():
                # 不在时间范围内，等待
                if self.status_callback:
                    self.status_callback("等待时间范围...")
                time.sleep(30)
                continue

            # 检查点击次数限制
            max_clicks = self.config.get("max_clicks", 0)
            if max_clicks > 0 and self.click_count >= max_clicks:
                if self.status_callback:
                    self.status_callback("已完成指定次数点击")
                self.running = False
                break

            # 执行点击
            try:
                self._do_click()
                self.click_count += 1
                if self.status_callback:
                    self.status_callback(f"已点击 {self.click_count} 次")
            except Exception as e:
                if self.status_callback:
                    self.status_callback(f"点击出错: {e}")

            # 等待间隔
            interval = self._get_interval_seconds()
            time.sleep(interval)

        if self.status_callback:
            self.status_callback("已停止")

    def start(self):
        """启动引擎"""
        if self.running:
            return
        self.running = True
        self.paused = False
        self.click_count = 0
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        if self.status_callback:
            self.status_callback("运行中...")

    def stop(self):
        """停止引擎"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.status_callback:
            self.status_callback("已停止")
        self.thread = None

    def pause(self):
        """暂停"""
        self.paused = True
        if self.status_callback:
            self.status_callback("已暂停")

    def resume(self):
        """恢复"""
        self.paused = False
        if self.status_callback:
            self.status_callback("运行中...")

    def toggle(self):
        """切换启用/暂停状态"""
        if self.running and not self.paused:
            self.pause()
            return "paused"
        elif self.running and self.paused:
            self.resume()
            return "running"
        else:
            self.start()
            return "running"
