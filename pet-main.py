import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk, ImageOps
import threading
import random
import requests
import json
import datetime
import re
import os

# ==========================================
# ⚙️ 核心配置区 (开源使用请在此处修改)
# ==========================================
# images folder path
PET_FOLDER_PATH = r"E:\petimage" 

# LLM API Options
API_KEY = "sk-xxxxxxx"
API_BASE = "https://api.xxxxxxx.com/v1"
API_MODEL = "xxxxxxxxxx"

# window size
WINDOW_SIZE = 32
# ⚠️ Note: If your original image has a pure white background, put "#FFFFFF" here; if it's pure black, put "#000000"
TRANSPARENT_COLOR = "#FFFFFF" 
# ==========================================

class TkinterDesktopPet:
    def __init__(self, root):
        self.root = root
        self.root.title("Desktop Pet")
        
        # window basic
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.config(bg=TRANSPARENT_COLOR)
        self.root.attributes("-transparentcolor", TRANSPARENT_COLOR)
        
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.screen_x = screen_w // 2
        self.screen_y = screen_h // 2
        self.root.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}+{self.screen_x}+{self.screen_y}")
        
        # load images
        try:
            if not os.path.exists(PET_FOLDER_PATH):
                raise FileNotFoundError(f"找不到图片文件夹: {PET_FOLDER_PATH}")
                
            img_files = [f for f in os.listdir(PET_FOLDER_PATH) if f.endswith('.png')]
            img_files.sort() # Sort by filename 1.png, 2.png
            
            self.frames = []
            self.frames_flipped = []
            
            print(f"Loading images...")
            for file_name in img_files:
                frame = Image.open(os.path.join(PET_FOLDER_PATH, file_name)).convert("RGBA")
                
                # Scale proportionally to prevent the image from getting squashed
                calc_scale = min(WINDOW_SIZE / frame.width, WINDOW_SIZE / frame.height)
                new_w = int(frame.width * calc_scale)
                new_h = int(frame.height * calc_scale)
                
                frame = frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # save image
                self.frames.append(ImageTk.PhotoImage(frame))
                self.frames_flipped.append(ImageTk.PhotoImage(ImageOps.mirror(frame)))
                
        except Exception as e:
            print(f"loading error!: {e}")
            self.root.destroy()
            return

        self.total_frames = len(self.frames)
        if self.total_frames == 0:
            print("error: in folder not have images! plz download!")
            self.root.destroy()
            return

        # pet
        self.label = tk.Label(self.root, bg=TRANSPARENT_COLOR, bd=0)
        self.label.pack(fill="both", expand=True)
        self.label.configure(image=self.frames[0])
        
        # idk how to write here
        self.current_frame = 0
        self.facing_right = True
        self.is_moving = False
        self.is_thinking = False
        
        self.target_x = self.screen_x
        self.target_y = self.screen_y
        self.move_speed = 6 #move speed

        # mouse
        self.label.bind("<Button-1>", self.start_drag)    # 左键拖拽
        self.label.bind("<B1-Motion>", self.do_drag)
        self.label.bind("<Button-3>", self.open_chat)     # 右键聊天
        
        # LLM chat History
        # force output json
        self.messages = [
            {"role": "system", "content": "你是一个可爱的桌面宠物。你每次只能回复一个JSON对象，不能包含其他任何内容。格式：{\"reply\": \"你的回复\", \"action\": \"动作\"}。动作必须是 move_left, move_right, move_up, move_down, stay 中的一个。"}
        ]

        # start time
        self.root.after(1000, self.idle_brain)        # 5 seconds think how to move
        self.animate()                                # animate play
        self.root.after(15000, self.proactive_chat)   # 15 seconds start speak

    # ==========================================
    # animate and move
    # ==========================================
    def animate(self):
        """控制图片帧的轮播，实现行走动画"""
        if self.is_moving:
            self.current_frame = (self.current_frame + 1) % self.total_frames 
        else:
            self.current_frame = 0 # 停下来时保持第一帧
            
        # 根据朝向选择是否翻转图片
        if self.facing_right:
            self.label.configure(image=self.frames[self.current_frame])
        else:
            self.label.configure(image=self.frames_flipped[self.current_frame])
            
        self.root.after(150, self.animate)

    def move_tick(self):
        """物理移动的核心逻辑 (每 20ms 执行一次)"""
        if not self.is_moving:
            return
            
        dx = self.target_x - self.screen_x
        dy = self.target_y - self.screen_y
        dist = (dx**2 + dy**2)**0.5
        
        # 如果快到目标点了，直接吸附并停止
        if dist < self.move_speed:
            self.screen_x = self.target_x
            self.screen_y = self.target_y
            self.is_moving = False
            self.root.geometry(f"+{int(self.screen_x)}+{int(self.screen_y)}")
            return
            
        # 每次移动一小步
        self.screen_x += (dx / dist) * self.move_speed
        self.screen_y += (dy / dist) * self.move_speed
        
        # 实时判断朝向（向左走则翻转）
        if dx < 0: self.facing_right = False
        elif dx > 0: self.facing_right = True
            
        self.root.geometry(f"+{int(self.screen_x)}+{int(self.screen_y)}")
        self.root.after(20, self.move_tick)

    def start_walking(self, direction):
        """设定一个目标点并开始移动"""
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        step = 200 # 每次走动的距离
        
        if direction == "left":
            self.target_x = max(0, self.screen_x - step)
            self.target_y = self.screen_y
        elif direction == "right":
            self.target_x = min(screen_w - WINDOW_SIZE, self.screen_x + step)
            self.target_y = self.screen_y
        elif direction == "up":
            self.target_x = self.screen_x
            self.target_y = max(0, self.screen_y - step)
        elif direction == "down":
            self.target_x = self.screen_x
            self.target_y = min(screen_h - WINDOW_SIZE - 50, self.screen_y + step)
            
        self.is_moving = True
        self.move_tick()

    def idle_brain(self):
        """发呆大脑：如果没有在思考或移动，就随机溜达"""
        if not self.is_moving and not self.is_thinking:
            direction = random.choice(["left", "right", "up", "down", "stay"])
            if direction != "stay":
                self.start_walking(direction)
                    
        self.root.after(5000, self.idle_brain)

    # ==========================================
    # 💬 AI 对话与交互逻辑
    # ==========================================
    def start_drag(self, event):
        """鼠标左键按住时"""
        self.drag_x = event.x
        self.drag_y = event.y
        self.is_moving = False # 拖拽时停止自动行走

    def do_drag(self, event):
        """鼠标拖拽过程中"""
        x = self.root.winfo_x() + (event.x - self.drag_x)
        y = self.root.winfo_y() + (event.y - self.drag_y)
        self.screen_x, self.screen_y = x, y
        self.root.geometry(f"+{x}+{y}")

    def open_chat(self, event):
        """鼠标右键点击：弹窗对话"""
        if self.is_thinking: return
        
        text = simpledialog.askstring("和桌宠对话", "对它说点什么：")
        if text and text.strip():
            self.is_thinking = True
            self.show_bubble("思考中...")
            # 开启子线程请求 API，防止阻塞 UI
            threading.Thread(target=self._call_llm, args=(text,), daemon=True).start()

    def proactive_chat(self):
        """主动搭话功能：根据时间段找话题"""
        if not self.is_thinking and not self.is_moving:
            hour = datetime.datetime.now().hour
            if 6 <= hour < 12: time_feel = "现在是上午。"
            elif 12 <= hour < 18: time_feel = "现在是下午。"
            elif 18 <= hour < 24: time_feel = "现在是晚上。"
            else: time_feel = "现在是半夜。"
                
            prompt = f"[系统指令] {time_feel} 主动跟我说一句话，记得用JSON格式。"
            
            self.is_thinking = True
            self.show_bubble("（盯~）") 
            threading.Thread(target=self._call_llm, args=(prompt,), daemon=True).start()

        # 随机 30~60 秒后再次触发
        next_time = random.randint(30000, 60000)
        self.root.after(next_time, self.proactive_chat)

    def _call_llm(self, user_input):
        """调用大模型 API"""
        self.messages.append({"role": "user", "content": user_input})
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        payload = {"model": API_MODEL, "messages": self.messages, "temperature": 0.7, "max_tokens": 100}
        
        try:
            resp = requests.post(f"{API_BASE.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            # 正则提取 JSON，兼容各种大模型的废话
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                    reply = result.get("reply", "...")
                    action = result.get("action", "stay")
                except json.JSONDecodeError:
                    reply = "脑电波解析失败..."
                    action = "stay"
            else:
                reply = content[:30] # 如果没按格式，截取前30字
                action = "stay"
                
        except Exception as e:
            reply = f"API通信报错..."
            action = "stay"
            print(f"❌ 请求出错: {e}")

        # 记录上下文并限制长度
        self.messages.append({"role": "assistant", "content": reply})
        if len(self.messages) > 11:
            self.messages = [self.messages[0]] + self.messages[-10:]

        # 切回主线程更新 UI
        self.root.after(0, lambda: self.on_llm_finish(reply, action))

    def on_llm_finish(self, reply, action):
        """处理大模型返回的结果"""
        print(f"👻 [宠物表现]: {reply} | [动作]: {action}")
        self.show_bubble(reply)
        if action != "stay":
            direction = action.replace("move_", "")
            self.start_walking(direction)
        self.is_thinking = False

    def show_bubble(self, text):
        """在头顶弹出一个白色气泡显示文字"""
        if hasattr(self, "bubble") and self.bubble.winfo_exists():
            self.bubble.destroy()
            
        self.bubble = tk.Toplevel(self.root)
        self.bubble.overrideredirect(True)
        self.bubble.attributes("-topmost", True)
        
        self.bubble.config(bg="black") # 黑色边框
        lbl = tk.Label(self.bubble, text=text, bg="#FFFFFF", font=("Microsoft YaHei", 10), padx=10, pady=5)
        lbl.pack(padx=1, pady=1)
        
        # 计算气泡位置（宠物头顶居中）
        self.bubble.update_idletasks()
        bx = self.screen_x + (WINDOW_SIZE - self.bubble.winfo_width()) // 2
        by = self.screen_y - self.bubble.winfo_height() - 10
        self.bubble.geometry(f"+{int(bx)}+{int(by)}")
        
        # 4 秒后自动销毁
        self.root.after(4000, lambda: self.bubble.destroy() if self.bubble.winfo_exists() else None)

if __name__ == '__main__':
    try:
        print("====== 👻 桌宠启动 ======")
        root = tk.Tk()
        app = TkinterDesktopPet(root)
        root.mainloop()
    except KeyboardInterrupt:
        print("\n👋 桌宠已安全下班，下次见！")
