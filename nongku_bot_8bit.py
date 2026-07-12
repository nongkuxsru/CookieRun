import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import tkinter.font as tkfont

class NongkuBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NONGKU BOT • COOKIE RUN v0.1")
        self.root.geometry("920x590")
        self.root.resizable(False, False)
        self.root.configure(bg="#0a0a0a")
        
        self.setup_8bit_style()
        
        self.main_frame = tk.Frame(self.root, bg="#1a1a2e", bd=6, relief="ridge")
        self.main_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        self.create_header()
        self.create_layout()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def setup_8bit_style(self):
        self.colors = {
            'bg': '#0a0a0a',
            'panel': '#1a1a2e',
            'accent': '#00ff00',
            'highlight': '#ffff00',
            'text': '#ffffff',
            'button': '#2a2a4a',
            'success': '#00cc00',
            'danger': '#cc0000'
        }
        
        self.pixel_font = tkfont.Font(family="Courier", size=9, weight="bold")
        self.title_font = tkfont.Font(family="Courier", size=14, weight="bold")
    
    def create_header(self):
        """Header with new Notification button"""
        header = tk.Frame(self.main_frame, bg="#16213e", height=50)
        header.pack(fill="x", padx=6, pady=6)
        header.pack_propagate(False)
        
        logo = tk.Label(header, text="🍪 NONGKU BOT", 
                       font=self.title_font, fg=self.colors['accent'], bg="#16213e")
        logo.pack(side="left", padx=18)
        
        version = tk.Label(header, text="COOKIE RUN v0.1", 
                          font=self.pixel_font, fg=self.colors['highlight'], bg="#16213e")
        version.pack(side="left", padx=10)
        
        vip = tk.Label(header, text="⭐ VIP 1/1", 
                      font=self.pixel_font, fg="#ffaa00", bg="#16213e")
        vip.pack(side="right", padx=18)
        
        # Tab buttons
        tab_frame = tk.Frame(header, bg="#16213e")
        tab_frame.pack(side="right", padx=15)
        
        tk.Button(tab_frame, text="ตั้งค่าบอท", bg=self.colors['button'], fg="white", 
                 font=self.pixel_font, relief="ridge", bd=3, command=self.open_settings).pack(side="left", padx=4)
        
        tk.Button(tab_frame, text="การแจ้งเตือน", bg="#ff8800", fg="white", 
                 font=self.pixel_font, relief="ridge", bd=3, command=self.open_notification_popup).pack(side="left", padx=4)
        
        tk.Button(tab_frame, text="รีโหลด-สุ่ม", bg=self.colors['accent'], fg="black", 
                 font=self.pixel_font, relief="ridge", bd=3).pack(side="left", padx=4)
    
    def create_layout(self):
        content = tk.Frame(self.main_frame, bg=self.colors['panel'])
        content.pack(fill="both", expand=True, padx=8, pady=6)
        
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        
        left_panel = tk.Frame(content, bg=self.colors['panel'])
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        
        right_panel = tk.Frame(content, bg=self.colors['panel'])
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        self.create_left_panel(left_panel)
        self.create_right_panel(right_panel)
    
    def create_left_panel(self, parent):
        """Left panel: Account + MuMu Instances (ขยายใหญ่ขึ้น)"""
        # Account
        acc_frame = tk.LabelFrame(parent, text="🧭 SETTING", fg=self.colors['accent'], 
                                 bg=self.colors['panel'], font=self.pixel_font)
        acc_frame.pack(fill="x", padx=6, pady=6)
        
        tk.Label(acc_frame, text="Tater Trader", 
                fg=self.colors['text'], bg=self.colors['panel'], font=self.pixel_font).pack(anchor="w", padx=10, pady=5)
        tk.Label(acc_frame, text="Victor's Feather Laurel Wreath", 
                fg=self.colors['text'], bg=self.colors['panel'], font=self.pixel_font).pack(anchor="w", padx=10, pady=5)
        
        num_frame = tk.Frame(acc_frame, bg=self.colors['panel'])
        num_frame.pack(anchor="w", padx=10, pady=5)
        tk.Label(num_frame, text="จำนวนครั้ง:", fg=self.colors['highlight'], bg=self.colors['panel']).pack(side="left")
        self.spin = tk.Spinbox(num_frame, from_=1, to=100, width=4, bg="#2a2a4a", fg="white")
        self.spin.pack(side="left", padx=5)
        self.spin.delete(0, tk.END)
        self.spin.insert(0, "10")
        
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
            cb.pack(anchor="w", padx=10, pady=1)
        
        # ==================== MuMu Instances ====================
        mumu_frame = tk.LabelFrame(parent, text="🖥️ MuMu INSTANCES", fg=self.colors['accent'], 
                                  bg=self.colors['panel'], font=self.pixel_font)
        mumu_frame.pack(fill="both", expand=True, padx=6, pady=6)
        
        # Control buttons
        btn_frame = tk.Frame(mumu_frame, bg=self.colors['panel'])
        btn_frame.pack(fill="x", padx=6, pady=6)
        
        tk.Button(btn_frame, text="🔍 สแกนหา Instance", bg=self.colors['success'], fg="white", 
                 font=self.pixel_font, relief="raised", bd=3).pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="🗑️ ลบข้อมูลเกมส์", bg=self.colors['danger'], fg="white", 
                 font=self.pixel_font, relief="raised", bd=3).pack(side="left", padx=4)
        
        # Instances Checklist
        list_frame = tk.LabelFrame(mumu_frame, text="เลือก Instance ที่ต้องการควบคุม", fg=self.colors['highlight'], 
                                  bg=self.colors['panel'], font=self.pixel_font)
        list_frame.pack(fill="both", expand=True, padx=6, pady=6)
        
        # Sample Instances (3-4 ตัวอย่าง)
        self.instance_vars = []
        instances = [
            "MuMu Instance 1 - Emulator 1",
            "MuMu Instance 2 - Emulator 2",
            "MuMu Instance 3 - Emulator 3",
            "MuMu Instance 4 - Emulator 4"
        ]
        
        for inst in instances:
            var = tk.BooleanVar(value=True)
            self.instance_vars.append(var)
            cb = tk.Checkbutton(list_frame, text=inst, variable=var, 
                               bg=self.colors['panel'], fg=self.colors['text'], 
                               selectcolor="#00ff00", font=self.pixel_font, anchor="w")
            cb.pack(fill="x", padx=10, pady=2)
        
        # Status
        status = tk.Label(parent, text="✅ พร้อมใช้งาน — เปิด MuMu ก่อนเริ่มงาน", 
                         fg="#00ff88", bg=self.colors['panel'], font=self.pixel_font)
        status.pack(pady=6)
    
    def create_right_panel(self, parent):
        """Right panel - Statistics & Log"""
        stats_frame = tk.LabelFrame(parent, text="📊 STATISTICS", fg=self.colors['accent'], 
                                   bg=self.colors['panel'], font=self.pixel_font)
        stats_frame.pack(fill="x", padx=6, pady=6)
        
        stats_grid = tk.Frame(stats_frame, bg=self.colors['panel'])
        stats_grid.pack(padx=8, pady=8)
        
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
            f.grid(row=row, column=col, padx=10, pady=6)
            tk.Label(f, text=val, font=("Courier", 18, "bold"), fg=color, bg=self.colors['panel']).pack()
            tk.Label(f, text=label, font=self.pixel_font, fg=self.colors['text'], bg=self.colors['panel']).pack()
        
        # Start Button
        tk.Button(parent, text="▶️ เริ่มสุ่ม", bg="#00cc00", fg="black", 
                 font=("Courier", 12, "bold"), height=2, relief="ridge").pack(fill="x", padx=6, pady=6)
        
        # Log
        log_frame = tk.LabelFrame(parent, text="📜 LOG การทำงาน", fg=self.colors['accent'], 
                                 bg=self.colors['panel'], font=self.pixel_font)
        log_frame.pack(fill="both", expand=True, padx=6, pady=6)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, bg="#0a1a0a", fg="#00ff88", 
                                                 font=("Courier", 9))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text.insert(tk.END, "[MAIN] MuMuManager.exe: C:\\Program Files\\Netease\\MuMuPlayer...\n")
        self.log_text.insert(tk.END, "[MAIN] Instance เริ่ม initialization fallback ใหม่\n")
        
        # Bottom controls
        bottom = tk.Frame(parent, bg=self.colors['panel'])
        bottom.pack(fill="x", padx=6, pady=6)
        for txt in ["▶️ เริ่ม", "⏹️ หยุด", "⏭️ ถัดไป", "📋 บันทึก"]:
            btn = tk.Button(bottom, text=txt, bg=self.colors['button'], fg="white", 
                           font=self.pixel_font, width=8)
            btn.pack(side="left", padx=4)
    
    # ==================== Popup Functions ====================
    def open_notification_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("การแจ้งเตือน")
        popup.geometry("500x400")
        popup.resizable(False, False)
        popup.configure(bg="#1a1a2e")
        
        tk.Label(popup, text="การตั้งค่าแจ้งเตือน", font=("Courier", 14, "bold"), 
                fg=self.colors['accent'], bg="#1a1a2e").pack(pady=15)
        
        # Telegram
        tk.Label(popup, text="Telegram Bot Token:", bg="#1a1a2e", fg="white").pack(anchor="w", padx=20)
        tk.Entry(popup, width=50, bg="#2a2a4a", fg="white").pack(padx=20, pady=5, fill="x")
        
        tk.Label(popup, text="Chat ID:", bg="#1a1a2e", fg="white").pack(anchor="w", padx=20)
        tk.Entry(popup, width=30, bg="#2a2a4a", fg="white").pack(padx=20, pady=5, anchor="w")
        
        # Discord
        tk.Label(popup, text="Discord Webhook:", bg="#1a1a2e", fg="white").pack(anchor="w", padx=20, pady=(10,0))
        tk.Entry(popup, width=60, bg="#2a2a4a", fg="white").pack(padx=20, pady=5, fill="x")
        
        tk.Button(popup, text="บันทึกการตั้งค่า", bg=self.colors['success'], fg="black", 
                 font=self.pixel_font, command=popup.destroy).pack(pady=20)
    
    def open_settings(self):
        messagebox.showinfo("ตั้งค่าบอท", "ฟังก์ชันตั้งค่าบอทจะถูกเพิ่มในเวอร์ชันถัดไป")
    
    def on_close(self):
        if messagebox.askokcancel("ออกจากโปรแกรม", "ต้องการปิด Nongku BOT ใช่หรือไม่?"):
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = NongkuBotGUI(root)
    root.mainloop()