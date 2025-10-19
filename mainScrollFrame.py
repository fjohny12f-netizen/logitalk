import socket
import threading
import queue
import random
from datetime import datetime
from customtkinter import *

AVATARS = ["🐱", "🐻", "🦊", "🐸", "🐼", "🐧", "🐰", "🐨", "🐙", "🐝"]

THEMES = {
    "dark": {"win_bg": "#1e1f26", "frame_bg": "#2b2d38", "entry_bg": "#242633", "text_bg": "#20222b",
             "text_fg": "white", "status_fg": "lightgreen", "button_fg": "#2b2d38", "button_text": "white"},
    "light": {"win_bg": "#f0f0f0", "frame_bg": "#dcdcdc", "entry_bg": "#ffffff", "text_bg": "#eeeeee",
              "text_fg": "black", "status_fg": "green", "button_fg": "#dcdcdc", "button_text": "black"},
    "blue": {"win_bg": "#1e2f50", "frame_bg": "#27496d", "entry_bg": "#3b5998", "text_bg": "#2a3d66",
             "text_fg": "white", "status_fg": "lightblue", "button_fg": "#27496d", "button_text": "white"},
    "cyberpunk": {"win_bg": "#0b0019", "frame_bg": "#130030", "entry_bg": "#2a002a", "text_bg": "#1f001f",
                  "text_fg": "#ff00ff", "status_fg": "#00ffff", "button_fg": "#130030", "button_text": "#ff00ff"}
}

class ChatClient:
    def __init__(self):
        self.sock = None
        self.nickname = None
        self.host = None
        self.port = None
        self.running = False
        self.recv_queue = queue.Queue()
        self.avatar = None
        self.current_theme_index = 0
        self.theme_names = list(THEMES.keys())
        self.widgets_to_update = []

        set_appearance_mode("dark")
        set_default_color_theme("blue")

        self.win = CTk()
        self.win.geometry("420x350")
        self.win.title("💬 OP Overlord — Вхід")
        self.win.configure(fg_color=THEMES["dark"]["win_bg"])

        CTkLabel(self.win, text="🔗 Підключення до чату", font=("Arial", 18, "bold")).pack(pady=10)
        CTkLabel(self.win, text="Нікнейм:").pack()
        self.nickname_entry = CTkEntry(self.win, placeholder_text="Anon")
        self.nickname_entry.pack(pady=5)
        CTkLabel(self.win, text="Хост:").pack()
        self.host_entry = CTkEntry(self.win, placeholder_text="127.0.0.1")
        self.host_entry.pack(pady=5)
        CTkLabel(self.win, text="Порт:").pack()
        self.port_entry = CTkEntry(self.win, placeholder_text="12345")
        self.port_entry.pack(pady=5)

        self.login_button = CTkButton(self.win, text="Увійти в чат", command=self.connect_server)
        self.login_button.pack(pady=20)

        self.win.bind("<Return>", lambda e: self.connect_server())
        self.win.protocol("WM_DELETE_WINDOW", self.close_client)
        self.win.mainloop()

    def connect_server(self):
        host = self.host_entry.get().strip() or "127.0.0.1"
        nickname = self.nickname_entry.get().strip() or "Anon"
        port_text = self.port_entry.get().strip()

        try:
            port = int(port_text) if port_text else 12345
        except ValueError:
            self.show_error("Невірний порт!")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.sock.send(nickname.encode("utf-8"))
        except Exception as e:
            self.show_error(f"Не вдалося підключитись: {e}")
            return

        self.avatar = random.choice(AVATARS)
        self.host, self.port, self.nickname = host, port, nickname
        self.running = True

        self.open_chat_window()
        threading.Thread(target=self.receive_messages, daemon=True).start()
        self.process_incoming()

    def open_chat_window(self):
        for w in self.win.winfo_children():
            w.destroy()

        theme = THEMES[self.theme_names[self.current_theme_index]]
        self.win.configure(fg_color=theme["win_bg"])
        self.win.title(f"💬 OP Overlord — {self.nickname}")
        self.win.geometry("900x550")

        main_frame = CTkFrame(self.win, fg_color=theme["frame_bg"], corner_radius=15)
        main_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.widgets_to_update.append(main_frame)

        self.text_area = CTkTextbox(main_frame, wrap="word", state="disabled",
                                    fg_color=theme["text_bg"], text_color=theme["text_fg"], font=("Consolas", 13))
        self.text_area.pack(fill="both", expand=True, pady=5, padx=5)
        self.widgets_to_update.append(self.text_area)

        entry_frame = CTkFrame(main_frame, fg_color=theme["frame_bg"])
        entry_frame.pack(fill="x")
        self.widgets_to_update.append(entry_frame)

        self.entry = CTkEntry(entry_frame, placeholder_text="Введіть повідомлення...",
                               fg_color=theme["entry_bg"], text_color=theme["text_fg"], font=("Arial", 13))
        self.entry.pack(side="left", fill="x", expand=True, padx=5, pady=8)
        self.entry.bind("<Return>", lambda e: self.send_message())
        self.widgets_to_update.append(self.entry)

        emoji_btn = CTkButton(entry_frame, text="😀", width=40, command=self.insert_emoji,
                              fg_color=theme["button_fg"], text_color=theme["button_text"])
        emoji_btn.pack(side="left", padx=3)
        self.widgets_to_update.append(emoji_btn)

        send_btn = CTkButton(entry_frame, text="📨", width=60, command=self.send_message,
                             fg_color=theme["button_fg"], text_color=theme["button_text"])
        send_btn.pack(side="right", padx=5)
        self.widgets_to_update.append(send_btn)

        side_frame = CTkFrame(self.win, width=180, fg_color=theme["frame_bg"], corner_radius=15)
        side_frame.pack(side="right", fill="y", padx=10, pady=10)
        self.widgets_to_update.append(side_frame)

        CTkLabel(side_frame, text="👥 У мережі", font=("Arial", 16, "bold")).pack(pady=10)
        CTkLabel(side_frame, text=f"{self.avatar}  {self.nickname}", font=("Arial", 14, "bold")).pack(pady=5)

        self.user_list = CTkScrollableFrame(side_frame, fg_color=theme["frame_bg"])
        self.user_list.pack(fill="both", expand=True, padx=5, pady=5)
        self.widgets_to_update.append(self.user_list)

        CTkButton(side_frame, text="🎨 Змінити тему", command=self.change_theme,
                  fg_color=theme["button_fg"], text_color=theme["button_text"]).pack(pady=10)

        self.status_label = CTkLabel(self.win, text="🟢 Підключено", text_color=theme["status_fg"], font=("Arial", 12))
        self.status_label.pack(side="bottom", pady=5)
        self.widgets_to_update.append(self.status_label)

        self.entry.focus()

    def change_theme(self):
        self.current_theme_index = (self.current_theme_index + 1) % len(self.theme_names)
        theme_name = self.theme_names[self.current_theme_index]
        theme = THEMES[theme_name]

        self.win.configure(fg_color=theme["win_bg"])
        for widget in self.widgets_to_update:
            try:
                widget.configure(fg_color=theme.get("frame_bg", widget.cget("fg_color")),
                                 text_color=theme.get("text_fg", widget.cget("text_color")))
            except:
                pass
        self.add_message(f"🎨 Тема змінена на: {theme_name}")

    def receive_messages(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8")
                while "\nEND\n" in buffer:
                    packet, buffer = buffer.split("\nEND\n", 1)
                    self.recv_queue.put(packet.strip())
            except Exception as e:
                self.recv_queue.put(f"MSG:⚠️ Помилка прийому: {e}")
                break
        self.recv_queue.put("MSG:⚠️ З'єднання закрито сервером.")
        self.running = False

    def process_incoming(self):
        while not self.recv_queue.empty():
            msg = self.recv_queue.get()
            if msg.startswith("MSG:"):
                self.add_message(msg[4:].strip())
            elif msg.startswith("USERS:"):
                users = [u.strip() for u in msg[6:].split(",") if u.strip()]
                self.update_user_list(users)
        if self.running:
            self.win.after(100, self.process_incoming)

    def add_message(self, msg: str):
        self.text_area.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M")
        if msg.startswith(f"{self.nickname}:"):
            _, text = msg.split(":", 1)
            formatted = f"\n🫵 [{timestamp}] Ви: {text.strip()}\n"
            tag = "self"
        elif msg.startswith(("🔵", "🔴", "⚠️", "🎨")):
            formatted = f"\n{msg}\n"
            tag = "system"
        else:
            formatted = f"\n💬 [{timestamp}] {msg}\n"
            tag = "other"

        self.text_area.insert("end", formatted, tag)
        self.text_area.tag_config("self", foreground="#00bfff")
        self.text_area.tag_config("other", foreground="#7fff00")
        self.text_area.tag_config("system", foreground="#ffcc00")
        self.text_area.see("end")
        self.text_area.configure(state="disabled")

    def update_user_list(self, users):
        for widget in self.user_list.winfo_children():
            widget.destroy()
        for u in users:
            avatar = random.choice(AVATARS)
            label = CTkLabel(self.user_list, text=f"{avatar}  {u}" + (" (ви)" if u == self.nickname else ""),
                             text_color="lightgreen")
            label.pack(anchor="w", padx=5, pady=3)

    def send_message(self):
        msg = self.entry.get().strip()
        if msg and self.running:
            try:
                self.sock.send(f"MSG:{msg}\nEND\n".encode("utf-8"))
            except Exception as e:
                self.add_message(f"⚠️ Помилка відправки: {e}")
                self.running = False
            self.entry.delete(0, "end")

    def insert_emoji(self):
        emoji_list = ["😀", "😂", "😎", "❤️", "👍", "🔥", "🎉", "💀", "😢", "😡"]
        popup = CTkToplevel(self.win)
        popup.title("Виберіть emoji")
        popup.geometry("240x120")
        popup.configure(fg_color="#2b2d38")

        frame = CTkFrame(popup, fg_color="#2b2d38")
        frame.pack(pady=10)
        for e in emoji_list:
            b = CTkButton(frame, text=e, width=35, command=lambda em=e: self.add_emoji(em, popup))
            b.pack(side="left", padx=3)

    def add_emoji(self, emoji, popup):
        current = self.entry.get()
        self.entry.delete(0, "end")
        self.entry.insert(0, current + emoji)
        popup.destroy()

    def close_client(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        self.win.destroy()

    def show_error(self, message):
        err = CTkToplevel(self.win)
        err.title("❌ Помилка")
        err.geometry("300x120")
        CTkLabel(err, text=message, text_color="red", wraplength=280).pack(pady=15)
        CTkButton(err, text="OK", command=err.destroy).pack(pady=5)


if __name__ == "__main__":
    ChatClient()
