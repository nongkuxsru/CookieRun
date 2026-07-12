import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import tkinter.font as tkfont
import os
from PIL import Image, ImageTk  # pip install pillow if needed for icons

class NongkuBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NONGKU BOT • COOKIE RUN v0.1")
        self.root.geometry("1200x700")
        self.root.configure(bg="#0a0a0a")  # Dark retro background
        
        # 8-bit style configuration
        self.setup_8bit_style()
        
        # Main container with pixel border
        self.main_frame = tk.Frame(self.root, bg="#1a1a2e", bd=8, relief="ridge")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.create_header()
        self.create_layout()
        
        # Bind close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def setup_8bit_style(self):
        """Setup retro 8-bit look"""
        style = ttk.Style()
        style.theme_use('clam')  # Modern base but we'll override
        
        # Custom colors - 8-bit palette
        self.colors = {
            'bg': '#0a0a0a',
            'panel': '#1a1a2e',
            'accent': '#00ff00',  # Neon green
            'highlight': '#ffff00',  # Yellow
            'text': '#ffffff',
            'button': '#2a2a4a',
            'success': '#00cc00',
            'danger': '#cc0000'
        }
        
        # Try to use pixel-like font
        try:
            self.pixel_font = tkfont.Font(family="Courier", size=10, weight="bold")
            self.title_font = tkfont.Font(family="Courier", size=16, weight="bold")
        except:
            self.pixel_font = tkfont.Font(family="TkFixedFont", size=10)
            self.title_font = tkfont.Font(family="TkFixedFont", size=14, weight="bold")
    
    def create_header(self):
        """Retro header"""
        header = tk.Frame(self.main_frame, bg="#16213e", height=60)
        header.pack(fill="x", padx=5, pady=5)
        header.pack_propagate(False)
        
        # Logo area (8-bit style text)
        logo = tk.Label(header, text="🍪 NONGKU BOT", 
                       font=self.title_font, fg=self.colors['accent'], bg="#16213e")
        logo.pack(side="left", padx=20)
        
        version = tk.Label(header, text="COOKIE RUN v0.1", 
                          font=self.pixel_font, fg=self.colors['highlight'], bg="#16213e")
        version.pack(side="left", padx=10)
        
        # VIP status
        vip = tk.Label(header, text="⭐ VIP 1/1", 
                      font=self.pixel_font, fg="#ffaa00", bg="#16213e")
        vip.pack(side="right", padx=20)
        
        # Tabs like original
        tab_frame = tk.Frame(header, bg="#16213e")
        tab_frame.pack(side="right", padx=20)
        
        tk.Button(tab_frame, text="ตั้งค่าบอท", bg=self.colors['button'], fg="white", 
                 font=self.pixel_font, relief="ridge", bd=3).pack(side="left", padx=5)
        tk.Button(tab_frame, text="รีโหลด-สุ่ม", bg=self.colors['accent'], fg="black", 
                 font=self.pixel_font, relief="ridge", bd=3).pack(side="left", padx=5)
    
    def create_layout(self):
        """Main two-column layout"""
        content = tk.Frame(self.main_frame, bg=self.colors['panel'])
        content.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Left panel (60%)
        left_panel = tk.Frame(content, bg=self.colors['panel'], width=700)
        left_panel.pack(side="left", fill="both", expand=True, padx=5)
        
        self.create_left_panel(left_panel)
        
        # Right panel (40%)
        right_panel = tk.Frame(content, bg=self.colors['panel'], width=450)
        right_panel.pack(side="right", fill="both", padx=5)
        
        self.create_right_panel(right_panel)
    
    def create_left_panel(self, parent):
        """Left side - Settings"""
        # Account section
        acc_frame = tk.LabelFrame(parent, text="🧭 ACCOUNT", fg=self.colors['accent'], 
                                 bg=self.colors['panel'], font=self.pixel_font)
        acc_frame.pack(fill="x", padx=8, pady=8)
        
        tk.Label(acc_frame, text="Tater Trader + Victor's Feather Laurel Wreath", 
                fg=self.colors['text'], bg=self.colors['panel'], font=self.pixel_font).pack(anchor="w", padx=10, pady=5)
        
        # Number input
        num_frame = tk.Frame(acc_frame, bg=self.colors['panel'])
        num_frame.pack(anchor="w", padx=10, pady=5)
        tk.Label(num_frame, text="จำนวนครั้ง:", fg=self.colors['highlight'], bg=self.colors['panel']).pack(side="left")
        self.spin = tk.Spinbox(num_frame, from_=1, to=100, width=5, bg="#2a2a4a", fg="white")
        self.spin.pack(side="left", padx=5)
        self.spin.delete(0, tk.END)
        self.spin.insert(0, "10")
        
        # Checkboxes
        checks = [
            "ทำตามกาชาแน่นอน (ไม่จำกัด)",
            "เลือกประเภทกาชา (เลือกได้ทั้งหมด)",
            "สุ่มชุด (treasure)",
            "สุ่มชุดพิเศษ (Luxury ฯลฯ)"
        ]
        for text in checks:
            var = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(acc_frame, text=text, variable=var, 
                               bg=self.colors['panel'], fg=self.colors['text'], 
                               selectcolor="#00ff00", font=self.pixel_font)
            cb.pack(anchor="w", padx=10)
        
        # Notifications
        noti_frame = tk.LabelFrame(parent, text="📡 NOTIFICATIONS", fg=self.colors['accent'], 
                                  bg=self.colors['panel'], font=self.pixel_font)
        noti_frame.pack(fill="x", padx=8, pady=8)
        
        # Telegram
        tk.Label(noti_frame, text="Telegram Bot Token:", bg=self.colors['panel'], fg=self.colors['text']).pack(anchor="w", padx=10)
        self.tg_token = tk.Entry(noti_frame, width=50, bg="#2a2a4a", fg="white")
        self.tg_token.pack(fill="x", padx=10, pady=2)
        
        tk.Label(noti_frame, text="Chat ID:", bg=self.colors['panel'], fg=self.colors['text']).pack(anchor="w", padx=10)
        self.chat_id = tk.Entry(noti_frame, width=30, bg="#2a2a4a", fg="white")
        self.chat_id.pack(anchor="w", padx=10, pady=2)
        
        # Discord
        tk.Label(noti_frame, text="Discord Webhook:", bg=self.colors['panel'], fg=self.colors['text']).pack(anchor="w", padx=10)
        self.discord = tk.Entry(noti_frame, width=80, bg="#2a2a4a", fg="white")
        self.discord.pack(fill="x", padx=10, pady=2)
        self.discord.insert(0, "https://discord.com/api/webhooks/...")  # Example
        
        # MuMu Instances
        mumu_frame = tk.LabelFrame(parent, text="🖥️ MuMu INSTANCES", fg=self.colors['accent'], 
                                  bg=self.colors['panel'], font=self.pixel_font)
        mumu_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        btn_frame = tk.Frame(mumu_frame, bg=self.colors['panel'])
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        buttons = [
            ("➕ เพิ่ม Instance", self.colors['button']),
            ("▶️ เปิด Emulator", self.colors['success']),
            ("🔄 Restart Selected", "#444466"),
            ("🔄 Restart All", "#666688"),
            ("✅ เลือกทั้งหมด", self.colors['success']),
            ("🗑️ ลบทั้งหมด", self.colors['danger'])
        ]
        
        for text, color in buttons:
            btn = tk.Button(btn_frame, text=text, bg=color, fg="white", 
                           font=self.pixel_font, relief="raised", bd=4)
            btn.pack(side="left", padx=3, pady=3)
        
        # Status
        status = tk.Label(parent, text="✅ พร้อมใช้งาน — เปิด MuMu ก่อนเริ่มงาน", 
                         fg="#00ff88", bg=self.colors['panel'], font=self.pixel_font)
        status.pack(pady=5)
    
    def create_right_panel(self, parent):
        """Right side - Stats & Logs"""
        # Stats
        stats_frame = tk.LabelFrame(parent, text="📊 STATISTICS", fg=self.colors['accent'], 
                                   bg=self.colors['panel'], font=self.pixel_font)
        stats_frame.pack(fill="x", padx=8, pady=8)
        
        stats_grid = tk.Frame(stats_frame, bg=self.colors['panel'])
        stats_grid.pack(padx=10, pady=10)
        
        stat_data = [
            ("0", "สุ่มแล้ว", "#00ffff"),
            ("0", "เจอแล้ว", "#00ff00"),
            ("0", "+ กระเป๋า", "#ffaa00"),
            ("0", "+ ชุด", "#ffff00"),
            ("0", "Premium", "#cc88ff"),
            ("0", "pet", "#88ff88")
        ]
        
        for i, (val, label, color) in enumerate(stat_data):
            row = i // 3
            col = i % 3
            f = tk.Frame(stats_grid, bg=self.colors['panel'])
            f.grid(row=row, column=col, padx=15, pady=8)
            
            tk.Label(f, text=val, font=("Courier", 18, "bold"), fg=color, bg=self.colors['panel']).pack()
            tk.Label(f, text=label, font=self.pixel_font, fg=self.colors['text'], bg=self.colors['panel']).pack()
        
        # Action area
        action = tk.Frame(parent, bg=self.colors['panel'])
        action.pack(fill="x", padx=8, pady=5)
        
        tk.Button(action, text="▶️ เริ่มสุ่ม", bg="#00cc00", fg="black", 
                 font=("Courier", 12, "bold"), height=2, relief="ridge").pack(fill="x", pady=5)
        
        # Log
        log_frame = tk.LabelFrame(parent, text="📜 LOG การทำงาน", fg=self.colors['accent'], 
                                 bg=self.colors['panel'], font=self.pixel_font)
        log_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, bg="#0a1a0a", fg="#00ff88", 
                                                 font=("Courier", 9))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Sample logs
        self.log_text.insert(tk.END, "[MAIN] MuMuManager.exe: C:\\Program Files\\Netease\\MuMuPlayer...\n")
        self.log_text.insert(tk.END, "[MAIN] Instance เริ่ม initialization fallback ใหม่\n")
        
        # Bottom controls
        bottom = tk.Frame(parent, bg=self.colors['panel'])
        bottom.pack(fill="x", padx=8, pady=8)
        
        controls = ["▶️ เริ่ม", "⏹️ หยุด", "⏭️ ถัดไป", "📋 บันทึก"]
        for txt in controls:
            btn = tk.Button(bottom, text=txt, bg=self.colors['button'], fg="white", 
                           font=self.pixel_font, width=8)
            btn.pack(side="left", padx=4)
    
    def on_close(self):
        if messagebox.askokcancel("ออกจากโปรแกรม", "ต้องการปิด Nongku BOT ใช่หรือไม่?"):
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = NongkuBotGUI(root)
    root.mainloop()