import os
import random
import sys
import time
import threading
from pathlib import Path

import cv2
import mss
import numpy as np
import pydirectinput
import pyautogui
import win32gui

WINDOW_TITLE = "洛克王国：世界"
pyautogui.FAILSAFE = True
pydirectinput.PAUSE = 0

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
IMG_DIR = BASE_DIR / "images"

IMG_START_BATTLE = str(IMG_DIR / "start_battle.png")
IMG_CONFIRM_FIRST = str(IMG_DIR / "confirm_first_pet.png")
IMG_EXIT_BUTTON = str(IMG_DIR / "exit_button.png")
IMG_BATTLE_EXIT_BUTTON = str(IMG_DIR / "battle_exit.png")
IMG_SELECT_PET_UI = str(IMG_DIR / "select_pet_ui.png")
IMG_ROUND_REPORT = str(IMG_DIR / "round_report.png")
IMG_LAST_ONE = str(IMG_DIR / "last_one.png")

REQUIRED_IMAGES = [
    IMG_START_BATTLE,
    IMG_CONFIRM_FIRST,
    IMG_EXIT_BUTTON,
    IMG_BATTLE_EXIT_BUTTON,
    IMG_SELECT_PET_UI,
    IMG_ROUND_REPORT,
    IMG_LAST_ONE,
]


class RocoAutoBot:
    def __init__(self, log_callback=None, stop_event=None, window_title=WINDOW_TITLE):
        self.log_callback = log_callback
        self.stop_event = stop_event or threading.Event()
        self.window_title = window_title
        self.win_info = None
        self.last_action_time = 0
        self.sct = mss.mss()
        self.templates = self.load_templates()
        self.pet_keys = ["1", "2", "3", "4"]

        # 当前是否已经切到最后一只主力
        self.is_last_pet = False

        # 最后一只主力已按 x 的次数
        self.last_pet_x_count = 0
        self.max_last_pet_x_count = 8

        # 全局独立防卡住点击线程
        self.last_center_click_time = 0
        self.center_click_interval = 5.0
        self.center_click_thread = None

    def log(self, msg):
        line = time.strftime("[%H:%M:%S] ") + msg
        if self.log_callback:
            self.log_callback(line)
        else:
            print(line, flush=True)

    def should_stop(self):
        return self.stop_event.is_set()

    def sleep_interruptible(self, seconds, interval=0.05):
        end = time.time() + seconds
        while time.time() < end:
            if self.should_stop():
                return True
            time.sleep(min(interval, end - time.time()))
        return False

    def reset_battle_state(self):
        self.is_last_pet = False
        self.last_pet_x_count = 0

    def load_templates(self):
        templates = {}
        for path in REQUIRED_IMAGES:
            if not os.path.exists(path):
                raise FileNotFoundError(f"缺失图片: {path}")
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise RuntimeError(f"图片无法读取: {path}")
            templates[path] = img
        return templates

    def bind_window(self):
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd) and self.window_title in win32gui.GetWindowText(hwnd):
                l, t, r, b = win32gui.GetWindowRect(hwnd)
                w, h = r - l, b - t
                if w > 1000 and h > 600:
                    windows.append({"hwnd": hwnd, "left": l, "top": t, "width": w, "height": h})
            return True

        valid_windows = []
        win32gui.EnumWindows(callback, valid_windows)
        if valid_windows:
            self.win_info = max(valid_windows, key=lambda x: x["width"] * x["height"])
            self.log(f"[系统] 绑定成功: {self.win_info['width']}x{self.win_info['height']}")
            return True
        return False

    def capture_gray(self):
        monitor = {
            "top": self.win_info["top"],
            "left": self.win_info["left"],
            "width": self.win_info["width"],
            "height": self.win_info["height"],
        }
        sct_img = self.sct.grab(monitor)
        return cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2GRAY)

    def find_image(self, screen_gray, template_key, confidence=0.85):
        template = self.templates.get(template_key)
        res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= confidence:
            th, tw = template.shape
            return (
                max_loc[0] + tw // 2 + self.win_info["left"],
                max_loc[1] + th // 2 + self.win_info["top"],
            )
        return None

    def click(self, x, y):
        if win32gui.GetForegroundWindow() != self.win_info["hwnd"]:
            try:
                win32gui.SetForegroundWindow(self.win_info["hwnd"])
            except Exception:
                pass
        pydirectinput.moveTo(x, y)
        pydirectinput.click()

    def click_center(self, log_text="[防卡住] 后台定时点击窗口中心"):
        if not self.win_info:
            return
        x = self.win_info["left"] + self.win_info["width"] // 2
        y = self.win_info["top"] + self.win_info["height"] // 2
        self.log(log_text)
        self.click(x, y)

    def center_click_worker(self):
        while not self.should_stop():
            # 没绑定窗口时，不点，只等待主线程绑定
            if not self.win_info:
                if self.sleep_interruptible(0.5):
                    return
                continue

            now = time.time()
            if now - self.last_center_click_time >= self.center_click_interval:
                try:
                    self.click_center()
                    self.last_center_click_time = now
                except Exception as e:
                    self.log(f"[防卡住] 后台点击失败: {e}")

            if self.sleep_interruptible(0.1):
                return

    def start_center_click_thread(self):
        if self.center_click_thread and self.center_click_thread.is_alive():
            return
        self.center_click_thread = threading.Thread(
            target=self.center_click_worker,
            daemon=True,
            name="center-click-worker",
        )
        self.center_click_thread.start()
        self.log("[系统] 已启动后台防卡住点击线程。")

    def press_key(self, key):
        pydirectinput.keyDown(key)
        time.sleep(random.uniform(0.05, 0.08))
        pydirectinput.keyUp(key)

    def run(self):
        self.log("=== 纯视觉驱动版 FSM 启动 ===")
        self.log("提示：请以管理员身份运行，保持游戏窗口可见。")

        self.start_center_click_thread()

        while not self.should_stop():
            if not self.win_info and not self.bind_window():
                self.log("[等待] 未找到游戏窗口，1 秒后重试。")
                if self.sleep_interruptible(1):
                    break
                continue

            now = time.time()
            screen = self.capture_gray()

            # 1. 报告结算
            res_report = self.find_image(screen, IMG_ROUND_REPORT, 0.8)
            if res_report:
                self.log("[状态] 报告结算")
                self.click(*res_report)
                self.reset_battle_state()
                if self.sleep_interruptible(0.5):
                    break
                continue

            # 2. 战斗中
            res_battle = self.find_image(screen, IMG_BATTLE_EXIT_BUTTON, 0.8)
            if res_battle:
                # 2A. 换宠 UI
                res_sel = self.find_image(screen, IMG_SELECT_PET_UI, 0.75)
                if res_sel:
                    self.log("[战斗] 精灵阵亡，准备换宠...")

                    self.is_last_pet = bool(self.find_image(screen, IMG_LAST_ONE, 0.90))
                    self.last_pet_x_count = 0

                    if self.is_last_pet:
                        self.log("[视觉锁定] 检测到最后一只，切主力。")
                    else:
                        self.log("[视觉锁定] 当前不是最后一只，继续敢死队流程。")

                    ui_cleared = False
                    for key in self.pet_keys:
                        if self.should_stop():
                            break

                        self.log(f" -> 尝试按下宠物: {key}")
                        self.press_key(key)
                        if self.sleep_interruptible(0.2):
                            break

                        self.press_key("space")

                        for _ in range(6):
                            if self.sleep_interruptible(0.5):
                                break
                            new_screen = self.capture_gray()
                            if not self.find_image(new_screen, IMG_SELECT_PET_UI, 0.75):
                                ui_cleared = True
                                break

                        if ui_cleared:
                            duty = "主力(先等待后自爆)" if self.is_last_pet else "敢死队(自爆)"
                            self.log(f"[换宠] UI 已消失，职责: {duty}")
                            break

                    self.last_action_time = time.time()
                    continue

                # 2B. 正常技能逻辑
                if now - self.last_action_time > 2.0:
                    if self.is_last_pet:
                        if self.last_pet_x_count < self.max_last_pet_x_count:
                            self.press_key("x")
                            self.last_pet_x_count += 1
                            self.log(
                                f"[技能] 主力等待 (x) 第 {self.last_pet_x_count}/{self.max_last_pet_x_count} 次"
                            )
                        else:
                            self.press_key("1")
                            self.log("[技能] 主力等待次数已满，开始自爆 (1)")
                    else:
                        self.press_key("1")
                        self.log("[技能] 视觉判定为敢死队，自爆 (1)")

                    self.last_action_time = now

                if self.sleep_interruptible(0.05):
                    break
                continue

            # 3. 确认首发
            res_confirm = self.find_image(screen, IMG_CONFIRM_FIRST, 0.85)
            if res_confirm:
                self.log("[点击] 确认首发")
                self.click(*res_confirm)
                self.reset_battle_state()
                if self.sleep_interruptible(0.3):
                    break

                for _ in range(5):
                    if self.sleep_interruptible(0.5):
                        break
                    tmp_scr = self.capture_gray()
                    if not self.find_image(tmp_scr, IMG_CONFIRM_FIRST, 0.85):
                        break
                continue

            # 4. 退出战斗
            res_exit = self.find_image(screen, IMG_EXIT_BUTTON, 0.85)
            if res_exit:
                self.log("[点击] 退出战斗")
                self.click(*res_exit)
                self.reset_battle_state()
                if self.sleep_interruptible(1.0):
                    break
                continue

            # 5. 开始匹配
            res_start = self.find_image(screen, IMG_START_BATTLE, 0.85)
            if res_start:
                if now - self.last_action_time > 2.0:
                    self.log("[点击] 开始匹配")
                    self.click(*res_start)
                    self.last_action_time = now
                continue

            if self.sleep_interruptible(0.05):
                break

        self.log("[系统] 脚本已停止。")