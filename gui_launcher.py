import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

# 针对打包后的路径兼容
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

# 尝试导入业务逻辑（兼容测试）
try:
    from bot_core import RocoAutoBot, REQUIRED_IMAGES, WINDOW_TITLE
except ImportError:
    RocoAutoBot = None
    REQUIRED_IMAGES = []
    WINDOW_TITLE = "洛克王国：世界"

# === 现代极简暗黑配色 (IDE风格) ===
COLORS = {
    "bg": "#2B2D30",          # 主背景色
    "panel": "#393B40",       # 面板颜色
    "input": "#1E1F22",       # 输入框/日志背景
    "text": "#DFE1E5",        # 默认文字
    "text_dim": "#A9B0B7",    # 次要文字/提示
    "primary": "#4C7AD3",     # 主按钮 (蓝)
    "primary_hover": "#5485E5",
    "danger": "#C75450",      # 停止按钮 (红)
    "danger_hover": "#D95C58",
    "success": "#579C46",     # 成功状态 (绿)
    "disabled": "#565A60"     # 禁用状态
}

FONTS = {
    "main": ("Microsoft YaHei", 10),
    "bold": ("Microsoft YaHei", 10, "bold"),
    "log": ("Consolas", 10)
}

class FlatButton(tk.Frame):
    """轻量级极简扁平按钮"""
    def __init__(self, parent, text, bg_color, hover_color, command=None, width=12):
        super().__init__(parent, bg=bg_color, cursor="hand2")
        self.base_color = bg_color
        self.hover_color = hover_color
        self.command = command
        self.is_disabled = False

        self.label = tk.Label(
            self, text=text, bg=bg_color, fg=COLORS["text"],
            font=FONTS["bold"], cursor="hand2"
        )
        self.label.pack(expand=True, fill="both", ipadx=10, ipady=6)
        self.label.config(width=width)

        self.label.bind("<Enter>", self.on_enter)
        self.label.bind("<Leave>", self.on_leave)
        self.label.bind("<Button-1>", self.on_click)

    def set_state(self, state):
        if state == "disabled":
            self.is_disabled = True
            self.config(bg=COLORS["disabled"])
            self.label.config(bg=COLORS["disabled"], fg=COLORS["text_dim"], cursor="arrow")
            self.config(cursor="arrow")
        else:
            self.is_disabled = False
            self.config(bg=self.base_color)
            self.label.config(bg=self.base_color, fg=COLORS["text"], cursor="hand2")
            self.config(cursor="hand2")

    def on_enter(self, e):
        if not self.is_disabled:
            self.config(bg=self.hover_color)
            self.label.config(bg=self.hover_color)

    def on_leave(self, e):
        if not self.is_disabled:
            self.config(bg=self.base_color)
            self.label.config(bg=self.base_color)

    def on_click(self, e):
        if not self.is_disabled and self.command:
            self.command()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("自动控制台")
        self.root.geometry("700x480")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)

        self.setup_system_appearance()

        self.bot_thread = None
        self.stop_event = None
        self.running = False

        self.window_title_var = tk.StringVar(value=WINDOW_TITLE)
        self.status_var = tk.StringVar(value="就绪")

        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.log("控制台已启动。")
        self.log("建议：以管理员身份运行此程序。")

    def setup_system_appearance(self):
        """设置纯代码生成的、金色的、极简“洛克贝”图标并调用 Windows 原生 API 将标题栏变黑"""
        
        # 1. 纯代码手绘：16x16 像素级透明“金色洛克贝”图标
        try:
            # 保持对象引用防止被垃圾回收
            self.icon_image = tk.PhotoImage(width=16, height=16)
            palette = {
                'R': '#E53935', # 红色上半球
                'W': '#FFFFFF', # 白色下半球
                'B': '#111111', # 黑色边框与腰带
                ' ': None       # 完全透明
            }
            # 咕噜球像素矩阵图
            pixels = [
                "     BBBBBB     ",
                "   BBRRRRRRBB   ",
                "  BRRRRRRRRRRB  ",
                " BRRRRRRRRRRRRB ",
                " BRRRRRRRRRRRRB ",
                "BRRRRBBBBBBBBRRB",
                "BBBBBBWWWWWWBBBB",
                "BBBBBBWWWWWWBBBB",
                "BWWWWWBBBBBBWWWB",
                " BWWWWWWWWWWWWB ",
                " BWWWWWWWWWWWWB ",
                "  BWWWWWWWWWWB  ",
                "   BBWWWWWWBB   ",
                "     BBBBBB     ",
                "                ",
                "                "
            ]
            for y, row in enumerate(pixels):
                for x, char in enumerate(row):
                    color = palette.get(char)
                    if color:
                        self.icon_image.put(color, to=(x, y))
            
            # 将绘制好的金色洛克贝应用到系统图标
            self.root.iconphoto(True, self.icon_image)
        except Exception as e:
            self.log(f"[系统] 洛克贝图标渲染跳过: {e}")

        # 2. Windows 专属原生黑化 API
        if sys.platform.startswith("win"):
            try:
                import ctypes
                # 提高清晰度
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
                # 绑定任务栏分组，确保任务栏图标生效
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('roco.simple.bot')
                
                # 调用 Windows API 开启原生深色标题栏
                self.root.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                value = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
            except Exception:
                pass

        # 3. 配置滚动条样式
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Dark.Vertical.TScrollbar",
            background=COLORS["panel"],
            troughcolor=COLORS["input"],
            bordercolor=COLORS["input"],
            arrowcolor=COLORS["text_dim"],
            relief="flat"
        )
        style.map("Dark.Vertical.TScrollbar", background=[("active", COLORS["disabled"])])

    def build_ui(self):
        # 顶部控制面板
        panel = tk.Frame(self.root, bg=COLORS["panel"])
        panel.pack(fill="x", padx=15, pady=15)

        # 参数与状态栏
        top_row = tk.Frame(panel, bg=COLORS["panel"])
        top_row.pack(fill="x", padx=15, pady=(15, 10))

        tk.Label(top_row, text="目标窗口:", font=FONTS["main"], fg=COLORS["text"], bg=COLORS["panel"]).pack(side="left")
        
        entry = tk.Entry(
            top_row, textvariable=self.window_title_var, width=28, 
            font=FONTS["main"], bg=COLORS["input"], fg=COLORS["text"], 
            insertbackground=COLORS["text"], relief="flat", bd=4
        )
        entry.pack(side="left", padx=10)

        tk.Label(top_row, text="状态:", font=FONTS["main"], fg=COLORS["text_dim"], bg=COLORS["panel"]).pack(side="left", padx=(30, 5))
        self.status_label = tk.Label(top_row, textvariable=self.status_var, font=FONTS["bold"], fg=COLORS["text"], bg=COLORS["panel"], width=10, anchor="w")
        self.status_label.pack(side="left")

        # 按钮栏
        btn_row = tk.Frame(panel, bg=COLORS["panel"])
        btn_row.pack(fill="x", padx=15, pady=(0, 15))

        self.start_btn = FlatButton(btn_row, "开始", COLORS["primary"], COLORS["primary_hover"], self.start_bot)
        self.start_btn.pack(side="left")

        self.stop_btn = FlatButton(btn_row, "停止", COLORS["danger"], COLORS["danger_hover"], self.stop_bot)
        self.stop_btn.set_state("disabled")
        self.stop_btn.pack(side="left", padx=10)

        self.clear_btn = FlatButton(btn_row, "清空日志", COLORS["panel"], COLORS["disabled"], self.clear_log)
        self.clear_btn.label.config(fg=COLORS["text_dim"]) # 弱化清空按钮视觉
        self.clear_btn.pack(side="right")

        # 提示语
        tk.Label(
            self.root,
            text="提示: 鼠标移至屏幕左上角可触发紧急停止。点击停止按钮后，会等待当前动作完成再退出。",
            font=FONTS["main"], fg=COLORS["text_dim"], bg=COLORS["bg"], anchor="w"
        ).pack(fill="x", padx=15, pady=(0, 5))

        # 日志区
        log_frame = tk.Frame(self.root, bg=COLORS["input"])
        log_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.log_box = tk.Text(
            log_frame, state="disabled", bg=COLORS["input"], fg=COLORS["text"],
            font=FONTS["log"], relief="flat", padx=10, pady=10, bd=0, highlightthickness=0
        )
        self.log_box.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_box.yview, style="Dark.Vertical.TScrollbar")
        scrollbar.pack(side="right", fill="y")
        self.log_box.config(yscrollcommand=scrollbar.set)

    def log(self, text):
        def append():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", text + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.root.after(0, append)

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def set_running(self, running: bool):
        self.running = running
        if running:
            self.status_var.set("运行中")
            self.status_label.configure(fg=COLORS["success"])
            self.start_btn.set_state("disabled")
            self.stop_btn.set_state("normal")
        else:
            self.status_var.set("已停止")
            self.status_label.configure(fg=COLORS["text"])
            self.start_btn.set_state("normal")
            self.stop_btn.set_state("disabled")

    def validate_environment(self):
        missing = [p for p in REQUIRED_IMAGES if not os.path.exists(p)]
        if missing:
            messagebox.showerror("资源缺失", "以下图片不存在：\n\n" + "\n".join(missing))
            return False
        if not self.window_title_var.get().strip():
            messagebox.showerror("错误", "目标窗口标题不能为空。")
            return False
        return True

    def bot_worker(self):
        if not RocoAutoBot:
            self.log("[测试] 未找到业务代码，运行5秒后停止...")
            import time
            time.sleep(5)
            self.root.after(0, lambda: self.set_running(False))
            return

        try:
            bot = RocoAutoBot(
                log_callback=self.log,
                stop_event=self.stop_event,
                window_title=self.window_title_var.get().strip(),
            )
            bot.run()
        except Exception as e:
            self.log(f"[错误] {e}")
            self.root.after(0, lambda: messagebox.showerror("运行失败", str(e)))
        finally:
            self.root.after(0, lambda: self.set_running(False))

    def start_bot(self):
        if self.running or not self.validate_environment():
            return
        self.stop_event = threading.Event()
        self.set_running(True)
        self.log("--- 启动 ---")
        self.bot_thread = threading.Thread(target=self.bot_worker, daemon=True)
        self.bot_thread.start()

    def stop_bot(self):
        if not self.running or not self.stop_event:
            return
        self.log("正在停止，请稍候...")
        self.stop_event.set()

    def on_close(self):
        if self.running and self.stop_event:
            self.stop_event.set()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()