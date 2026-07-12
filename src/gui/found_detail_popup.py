import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from PIL import Image, ImageTk
from pathlib import Path

class FoundDetailPopup(tb.Toplevel):
    def __init__(self, parent, account_data: dict):
        super().__init__(parent)
        self.title(f"รายละเอียดไอดี - {account_data.get('account_id', 'Unknown')}")
        self.geometry("850x650")
        self.resizable(True, True)

        self.account_data = account_data
        self._build_ui()

    def _build_ui(self):
        # หัวข้อ
        tb.Label(self, text="รายละเอียดไอดีที่เจอ", font=("Prompt", 16, "bold")).pack(pady=10)

        # รูปภาพหลัก
        img_frame = tb.Frame(self)
        img_frame.pack(pady=10, fill="x")
        try:
            img_path = self.account_data.get("screenshot")
            if img_path and Path(img_path).exists():
                img = Image.open(img_path)
                img = img.resize((600, 338), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                label = tb.Label(img_frame, image=photo)
                label.image = photo
                label.pack()
            else:
                tb.Label(img_frame, text="ไม่มีรูปภาพ", foreground="gray", font=("Prompt", 12)).pack()
        except Exception as e:
            tb.Label(img_frame, text=f"โหลดรูปไม่ได้: {e}", foreground="red").pack()

        # ข้อมูล
        info = tb.LabelFrame(self, text="ข้อมูลไอดี", padding=15)
        info.pack(fill="x", padx=20, pady=10)

        tb.Label(info, text=f"Account ID : {self.account_data.get('account_id')}", font=("Prompt", 11)).pack(anchor="w", pady=2)
        tb.Label(info, text=f"สมบัติที่ได้ : {self.account_data.get('treasures', 'ไม่มี')}", font=("Prompt", 11)).pack(anchor="w", pady=2)
        tb.Label(info, text=f"สัตว์เลี้ยงที่ได้ : {self.account_data.get('pets', 'ไม่มี')}", font=("Prompt", 11)).pack(anchor="w", pady=2)
        tb.Label(info, text=f"เวลา : {self.account_data.get('timestamp', 'N/A')}", font=("Prompt", 11)).pack(anchor="w", pady=2)

        # ปุ่ม
        btn_frame = tb.Frame(self)
        btn_frame.pack(pady=20)

        tb.Button(btn_frame, text="🚀 เปิด Emulator", bootstyle="success", width=15,
                  command=self._open_emulator).pack(side="left", padx=10)
        tb.Button(btn_frame, text="ปิด", bootstyle="secondary", width=10,
                  command=self.destroy).pack(side="left", padx=10)

    def _open_emulator(self):
        # เชื่อมต่อกับ Emulator Controller
        print(f"กำลังเปิด Emulator สำหรับ {self.account_data.get('account_id')}")
        # คุณสามารถเพิ่ม logic เรียก EmulatorController ได้ที่นี่
        tk.messagebox.showinfo("เปิด Emulator", "กำลังเปิด Emulator (กำลังพัฒนา)")