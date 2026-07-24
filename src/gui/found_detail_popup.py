import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from PIL import Image, ImageTk
from pathlib import Path


class FoundDetailPopup(tb.Toplevel):
    def __init__(self, parent, record: dict):
        super().__init__(parent)
        self.record = record
        self.title(f"รายละเอียดไอดี - {record.get('email', 'Unknown')}")
        self.geometry("700x760")
        self.resizable(True, True)
        self._photo_refs = []  # กัน PhotoImage ถูก garbage collect
        self._build_ui()

    def _build_image_block(self, parent, title: str, path_str: str | None) -> None:
        tb.Label(parent, text=title, font=("Prompt", 10, "bold")).pack(anchor="w", pady=(8, 2))
        frame = tb.Frame(parent, bootstyle="secondary")
        frame.pack(fill="x")
        try:
            if path_str and Path(path_str).exists():
                img = Image.open(path_str)
                img.thumbnail((640, 320), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._photo_refs.append(photo)
                tb.Label(frame, image=photo).pack(pady=4)
            else:
                tb.Label(frame, text="ไม่มีรูปภาพ", foreground="gray", font=("Prompt", 10)).pack(pady=20)
        except Exception as e:
            tb.Label(frame, text=f"โหลดรูปไม่ได้: {e}", foreground="red").pack(pady=10)

    def _build_ui(self):
        tb.Label(self, text="รายละเอียดไอดีที่เจอ", font=("Prompt", 16, "bold")).pack(pady=10)

        info = tb.Labelframe(self, text="ข้อมูลบัญชี", padding=15)
        info.pack(fill="x", padx=20, pady=(0, 10))

        email = self.record.get("email", "-")
        password = self.record.get("password", "-")
        pet_name = self.record.get("pet_name") or "-"
        treasures = ", ".join(self.record.get("treasures") or []) or "-"
        found_time = self.record.get("found_time") or self.record.get("time", "N/A")
        instance = self.record.get("instance", "-")

        def _row(label, value, copyable=True):
            r = tb.Frame(info)
            r.pack(fill="x", pady=2)
            tb.Label(r, text=f"{label} :", font=("Prompt", 11, "bold"), width=14, anchor="w").pack(side="left")
            tb.Label(r, text=value, font=("Consolas", 11)).pack(side="left", padx=(4, 8))
            if copyable:
                tb.Button(
                    r, text="คัดลอก", bootstyle="secondary-outline", width=8,
                    command=lambda v=value: self._copy_to_clipboard(v),
                ).pack(side="right")

        _row("📧 Email", email)
        _row("🔑 Password", password)
        _row("🐾 สัตว์เลี้ยง", pet_name, copyable=False)
        _row("💎 สมบัติ", treasures, copyable=False)
        _row("🖥 จอ", instance, copyable=False)
        _row("🕒 เวลา", found_time, copyable=False)

        # ภาพหน้าสุ่มเจอสมบัติ + สัตว์เลี้ยง แยกกันชัดเจน
        self._build_image_block(self, "💎 ภาพหน้าสุ่มเจอสมบัติ", self.record.get("treasure_screenshot_path"))
        self._build_image_block(self, "🐾 ภาพหน้าสุ่มเจอสัตว์เลี้ยง", self.record.get("pet_screenshot_path"))

        btn_frame = tb.Frame(self)
        btn_frame.pack(pady=16)
        tb.Button(
            btn_frame, text="📋 คัดลอก Email|Password", bootstyle="info", width=22,
            command=lambda: self._copy_to_clipboard(f"{email}|{password}"),
        ).pack(side="left", padx=6)
        tb.Button(btn_frame, text="ปิด", bootstyle="secondary", width=10, command=self.destroy).pack(side="left", padx=6)

    def _copy_to_clipboard(self, value: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        messagebox.showinfo("คัดลอกแล้ว", "คัดลอกไปยังคลิปบอร์ดแล้ว", parent=self)