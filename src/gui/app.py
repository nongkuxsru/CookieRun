"""Main GUI window: "PD Bot Game - Cookie run".

The app has two switchable modes/pages selected by the header tabs, matching
the two reference mockups the user provided:

  - "referral" (🤍 ปั้มทำใจ-ชวนเพื่อน) - simple referral/invite-friend farming:
    launch -> send referral link -> log in -> collect account -> repeat until
    a target account count is reached.
  - "reroll" (🔄 รีไอดี-สุ่มของ) - roll gacha (treasure/pet) each account until
    the target item/pet is found or currency runs out, unlimited accounts
    until cancelled, with a running list of found account IDs.

The "จอ (MuMu instances)" panel, the Log panel, and the Start/Pause/Resume/
Cancel bar are shared between both modes. See README.md for what still needs
game-specific templates before "เริ่ม" produces useful results in-game.
"""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, W, X, Y
from ttkbootstrap.scrolled import ScrolledText

from src.automation.stats import RunStats
from src.automation.worker_control import WorkerControl
from src.core import emulator_scanner
from src.core.adb_client import AdbClient
from src.core.config import Config
from src.core.logger import get_logger, setup_logging
from src.data.recorder import Recorder
from src.gui.automation_worker import AutomationWorker
from src.gui.log_queue_handler import QueueLogHandler
from src.notification.discord_manager import DiscordManager

log = get_logger(__name__)

APP_TITLE = "Nongku BOT • Cookie run"
APP_VERSION = "v0.0.1"

_ALL_SCREENS_LABEL = "รวมทุกจอ"
_FOUND_PAGE_SIZE = 5

# ── ฟอนต์หลัก ──
_FONT = "Prompt"
_FONT_MONO = "Consolas"


class BotApp(tb.Window):
    def __init__(self):
        super().__init__(title=APP_TITLE, themename="flatly")
        self.geometry("880x680")
        self.minsize(780, 600)

        self.config_obj = Config.load()
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.found_queue: "queue.Queue[str]" = queue.Queue()
        self.instances: list = []
        self.instance_vars: dict[int, tk.BooleanVar] = {}
        self.stats = RunStats()
        self.control = WorkerControl()
        self.recorder = Recorder(self.config_obj.get("paths.output_dir", "data_output"))
        self.worker: AutomationWorker | None = None
        self.log_lines: list[str] = []
        self.found_items: list[str] = []
        self.found_page_index = 0
        self.current_log_filter = tk.StringVar(value=_ALL_SCREENS_LABEL)
        self.current_mode = tk.StringVar(value="reroll")
        self.instance_names = {}
        self.instance_status = {}   # {index: "running" | "success" | "stopped"}
        self.discord = DiscordManager(self.config_obj)

        self._build_vars()
        self._attach_log_handler()
        # NOTE: สำหรับ checkbox ที่ไม่ได้ใช้ bootstyle toolbutton เราเลือกใช้ tk.Checkbutton แบบดั้งเดิม
        # เนื่องจากพบว่า ttk.Checkbutton/ttkbootstrap Checkbutton แบบมี indicator เป็นรูปภาพจะ segfault
        # ตอน destroy ในบางสภาพแวดล้อม (Pillow/Tcl-Tk เก่าเกนเกินไป) - tk.Checkbutton ดั้งเดิมไม่เกิดปัญหานี้
        self._checkbox_bg = self.style.colors.bg
        self._checkbox_fg = self.style.colors.fg
        self._build_layout()
        self._switch_mode("reroll")
        self._set_status_idle()

        self.after(200, self._poll_log_queue)
        self.after(300, self._poll_found_queue)
        self.after(500, self._poll_stats)
        self.after(100, self._refresh_log_filter_options)   # ← เพิ่ม

    # ------------------------------------------------------------- setup --
    def _build_vars(self) -> None:
        cfg = self.config_obj
        # โหมด "ปั้มทำใจ-ชวนเพื่อน"
        self.referral_link_var = tk.StringVar(value=cfg.get("referral.link", ""))
        self.send_referral_var = tk.BooleanVar(
            value=cfg.get("referral.send_before_open", False)
        )
        self.target_count_var = tk.IntVar(value=cfg.get("run.target_account_count", 1))
        self.cleanup_method_var = tk.StringVar(
            value=cfg.get("run.cleanup_method", "clear_data")
        )
        self.create_new_account_var = tk.BooleanVar(
            value=cfg.get("run.create_new_account_each_cycle", True)
        )

        # โหมด "รีไอดี-สุ่มของ"
        target_display = cfg.get("reroll.target_item_display_name") or cfg.get(
            "game.target_pet", "CHANGE_ME"
        )
        self.target_item_display_var = tk.StringVar(value=f"ของที่หา: {target_display}")
        self.rolls_per_round_var = tk.IntVar(
            value=cfg.get("reroll.rolls_per_round", 10)
        )
        self.unlimited_rolls_var = tk.BooleanVar(
            value=cfg.get("reroll.unlimited_rolls", False)
        )
        self.reroll_treasure_var = tk.BooleanVar(
            value=cfg.get("reroll.enable_treasure", True)
        )
        self.reroll_pet_var = tk.BooleanVar(
            value=cfg.get("reroll.enable_pet_luxury", True)
        )
        self.telegram_bot_token_var = tk.StringVar(
            value=cfg.get("telegram.bot_token", "")
        )
        self.telegram_chat_id_var = tk.StringVar(value=cfg.get("telegram.chat_id", ""))

        # === Discord Webhook ===
        self.discord_found_webhook_var = tk.StringVar(
            value=cfg.get("discord.found_webhook_url", "")
        )

        self.discord_status_webhook_var = tk.StringVar(
            value=cfg.get("discord.status_webhook_url", "")
        )

        self.discord_error_webhook_var = tk.StringVar(
            value=cfg.get("discord.error_webhook_url", "")
        )

    def _attach_log_handler(self) -> None:
        setup_logging(self.config_obj.get("paths.logs_dir", "logs"))
        
        handler = QueueLogHandler(self.log_queue)
        handler.setFormatter(
            logging.Formatter(
                "[%(instance)s] %(message)s",   # แสดงเฉพาะ Instance + ข้อความ
                datefmt="%H:%M:%S"
            )
        )
        logging.getLogger().addHandler(handler)

    # ------------------------------------------------------------ layout --
    def _build_layout(self) -> None:
        root = tb.Frame(self, padding=(8, 6, 8, 6))
        root.pack(fill=BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        self._build_header(root)

        body = tb.Frame(root)
        body.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        body.columnconfigure(0, weight=38, minsize=280)
        body.columnconfigure(1, weight=62, minsize=380)
        body.rowconfigure(0, weight=1)

        left = tb.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        right = tb.Frame(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.settings_container = tb.Frame(left)
        self.settings_container.grid(row=0, column=0, sticky="ew")

        self.referral_settings_frame = tb.Labelframe(
            self.settings_container, text="  ⚙  ตั้งค่า  ", padding=6
        )
        self._build_referral_settings(self.referral_settings_frame)

        self.reroll_settings_frame = tb.Labelframe(
            self.settings_container, text="  ⚙  ตั้งค่า  ", padding=6
        )
        self._build_reroll_settings(self.reroll_settings_frame)

        self._build_instances_card(left)

        self.right_top_container = tb.Frame(right)
        self.right_top_container.grid(row=0, column=0, sticky="ew")

        self.referral_right_frame = tb.Frame(self.right_top_container)
        self._build_referral_stats(self.referral_right_frame)

        self.reroll_right_frame = tb.Frame(self.right_top_container)
        self._build_reroll_right(self.reroll_right_frame)

        self._build_log_card(right)

        self._build_control_bar(root)

    def _build_header(self, parent: tb.Frame) -> None:
        header_outer = tb.Frame(parent)
        header_outer.grid(row=0, column=0, sticky="ew")
        parent.columnconfigure(0, weight=1)

        header = tb.Frame(header_outer)
        header.pack(fill=X)

        left = tb.Frame(header)
        left.pack(side=LEFT)
        brand = tb.Frame(left, bootstyle="primary", padding=(8, 4))
        brand.pack(side=LEFT, padx=(0, 8))
        tb.Label(
            brand, text="🍪", font=("Segoe UI Emoji", 16), bootstyle="inverse-primary"
        ).pack(side=LEFT, padx=(0, 4))
        tb.Label(
            brand,
            text=f"{APP_TITLE}  {APP_VERSION}",
            font=(_FONT, 11, "bold"),
            bootstyle="inverse-primary",
        ).pack(side=LEFT)

        middle = tb.Frame(header)
        middle.pack(side=LEFT, padx=(4, 0))
        self.mode_referral_btn = tb.Button(
            middle,
            text="🤍  ปั้มทำใจ-ชวนเพื่อน",
            command=lambda: self._switch_mode("referral"),
            width=22,
        )
        self.mode_referral_btn.pack(side=LEFT, padx=2)
        self.mode_reroll_btn = tb.Button(
            middle,
            text="🔄  รีไอดี-สุ่มของ",
            command=lambda: self._switch_mode("reroll"),
            width=22,
        )
        self.mode_reroll_btn.pack(side=LEFT, padx=2)

        right = tb.Frame(header)
        right.pack(side=RIGHT)
        registered = self.config_obj.get("license.registered_devices", 1)
        max_devices = self.config_obj.get("license.max_devices", 1)
        tb.Label(
            right,
            text=f"👑  VIP  {registered}/{max_devices}",
            bootstyle="warning",
            font=(_FONT, 9, "bold"),
            padding=(8, 4),
        ).pack(side=RIGHT)

        tb.Separator(header_outer, orient="horizontal").pack(fill=X, pady=(4, 0))

    def _switch_mode(self, mode: str) -> None:
        self.current_mode.set(mode)

        self.referral_settings_frame.pack_forget()
        self.reroll_settings_frame.pack_forget()
        self.referral_right_frame.pack_forget()
        self.reroll_right_frame.pack_forget()

        if mode == "referral":
            self.referral_settings_frame.pack(fill=X, pady=(0, 4))
            self.referral_right_frame.pack(fill=X)
            self.mode_referral_btn.configure(bootstyle="primary")
            self.mode_reroll_btn.configure(bootstyle="secondary-outline")
        else:
            self.reroll_settings_frame.pack(fill=X, pady=(0, 4))
            self.reroll_right_frame.pack(fill=X)
            self.mode_reroll_btn.configure(bootstyle="primary")
            self.mode_referral_btn.configure(bootstyle="secondary-outline")

    # ------------------------------------------------ left: referral mode --
    def _build_referral_settings(self, card: tb.Labelframe) -> None:
        tb.Label(card, text="Referral link", font=(_FONT, 9)).pack(anchor=W)
        tb.Entry(card, textvariable=self.referral_link_var, font=(_FONT, 9)).pack(fill=X, pady=(1, 6))

        target_row = tb.Frame(card)
        target_row.pack(fill=X, pady=(0, 6))
        tb.Label(target_row, text="เป้าหมายรวม (ไอดี)", font=(_FONT, 9)).pack(anchor=W)
        target_input_row = tb.Frame(target_row)
        target_input_row.pack(fill=X, pady=(1, 0))
        tb.Spinbox(
            target_input_row,
            from_=1,
            to=100000,
            textvariable=self.target_count_var,
            width=8,
            font=(_FONT, 9),
        ).pack(side=LEFT)
        tb.Label(target_input_row, text="(หยุดเมื่อครบจำนวน)", bootstyle="secondary", font=(_FONT, 8)).pack(
            side=LEFT, padx=6
        )

        tb.Label(card, text="วิธีเก็บเมื่อจบรอบ", font=(_FONT, 9)).pack(anchor=W, pady=(0, 2))
        cleanup_row = tb.Frame(card)
        cleanup_row.pack(fill=X, pady=(0, 6))
        tb.Radiobutton(
            cleanup_row,
            text="🚪 ออกจากระบบ",
            value="logout",
            variable=self.cleanup_method_var,
            bootstyle="warning-toolbutton",
        ).pack(side=LEFT, expand=True, fill=X, padx=(0, 4))
        tb.Radiobutton(
            cleanup_row,
            text="🗑 ลบข้อมูลเกม",
            value="clear_data",
            variable=self.cleanup_method_var,
            bootstyle="warning-toolbutton",
        ).pack(side=LEFT, expand=True, fill=X, padx=(4, 0))

        self._themed_checkbutton(
            card, "ส่งคำเชิญเพื่อน (referrer) ก่อนเปิด", self.send_referral_var
        ).pack(anchor=W, pady=(2, 1))
        self._themed_checkbutton(
            card,
            "สมัครไอดีใหม่ (สุ่มจบ/เก็บ - เก็บ new_accounts.txt)",
            self.create_new_account_var,
        ).pack(anchor=W, pady=1)

    def _build_referral_stats(self, parent: tb.Frame) -> None:
        card = tb.Labelframe(parent, text="  💾  สถานะงาน  ", padding=6)
        card.pack(fill=X)

        row = tb.Frame(card)
        row.pack(fill=X)
        self.stat_vars = {
            "started": tk.StringVar(value="0"),
            "success": tk.StringVar(value="0"),
            "failed": tk.StringVar(value="0"),
            "remaining": tk.StringVar(value="0"),
        }
        self._build_stat_mini(row, "เริ่ม", self.stat_vars["started"], "info")
        self._build_stat_mini(row, "สำเร็จ", self.stat_vars["success"], "success")
        self._build_stat_mini(row, "ไม่สำเร็จ", self.stat_vars["failed"], "danger")
        self._build_stat_mini(row, "เหลือ", self.stat_vars["remaining"], "warning")

        self.progress_bar = tb.Progressbar(
            card, bootstyle="success-striped", maximum=100, value=0
        )
        self.progress_bar.pack(fill=X, pady=(6, 0))

    # -------------------------------------------------- left: reroll mode --
    def _build_reroll_settings(self, card: tb.Labelframe) -> None:
        tb.Label(
            card,
            textvariable=self.target_item_display_var,
            font=(_FONT, 10, "bold"),
        ).pack(anchor=W, pady=(0, 6))

        count_row = tb.Frame(card)
        count_row.pack(fill=X, pady=(0, 4))
        tb.Label(count_row, text="จำนวนครั้ง (ต่อรอบ)", font=(_FONT, 9)).pack(anchor=W)
        input_row = tb.Frame(count_row)
        input_row.pack(fill=X, pady=(1, 0))
        self.rolls_per_round_spin = tb.Spinbox(
            input_row,
            from_=1,
            to=100000,
            textvariable=self.rolls_per_round_var,
            width=8,
            font=(_FONT, 9),
        )
        self.rolls_per_round_spin.pack(side=LEFT)

        self._themed_checkbutton(
            card, "∞ ทำจนกว่าจะหมด (ไม่จำกัด)", self.unlimited_rolls_var
        ).pack(anchor=W, pady=(0, 6))
        self.unlimited_rolls_var.trace_add(
            "write", lambda *_: self._update_rolls_input_state()
        )

        tb.Label(card, text="เลือกประเภทการสุ่ม (เลือกได้พร้อมกัน)", font=(_FONT, 9)).pack(
            anchor=W, pady=(0, 2)
        )
        self._themed_checkbutton(
            card, "🎁 สุ่มสมบัติ (treasure)", self.reroll_treasure_var
        ).pack(anchor=W, pady=1)
        self._themed_checkbutton(
            card, "🎫 สุ่มสัตว์เลี้ยง (Luxury จนเจอเป้าหมาย)", self.reroll_pet_var
        ).pack(anchor=W, pady=1)

        tg_row = tb.Frame(card)
        tg_row.pack(fill=X)
        tg_row.columnconfigure(0, weight=1)
        tg_row.columnconfigure(1, weight=1)
        token_col = tb.Frame(tg_row)
        token_col.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        # === Discord Webhook ===
        discord_frame = tb.Frame(card)
        discord_frame.pack(fill=X, padx=5, pady=(5, 0))
        tb.Label(
            discord_frame,
            text="Found Webhook (แจ้งเมื่อเจอไอดี)",
            font=(_FONT, 8)
        ).pack(anchor=W)

        tb.Entry(
            discord_frame,
            textvariable=self.discord_found_webhook_var,
            font=(_FONT, 8)
        ).pack(fill=X, pady=(1, 5))

        tb.Label(
            discord_frame,
            text="Status Webhook (แจ้งสถานะการทำงาน)",
            font=(_FONT, 8)
        ).pack(anchor=W)

        tb.Entry(
            discord_frame,
            textvariable=self.discord_status_webhook_var,
            font=(_FONT, 8)
        ).pack(fill=X)

        self._update_rolls_input_state()

    def _update_rolls_input_state(self) -> None:
        state = "disabled" if self.unlimited_rolls_var.get() else "normal"
        self.rolls_per_round_spin.configure(state=state)

    def _build_reroll_right(self, parent: tb.Frame) -> None:
        stats_card = tb.Labelframe(
            parent, text="  🎁  สถานะรีไอดี (รอบนี้)  ", padding=10
        )
        stats_card.pack(fill=X, pady=(0, 8))

        row1 = tb.Frame(stats_card)
        row1.pack(fill=X)
        row2 = tb.Frame(stats_card)
        row2.pack(fill=X, pady=(8, 0))

        # NOTE: "+ กระเป๋า" / "+ สัตว์" / "Premium" / "pet" ยังเป็นค่าตั้งต้น "0" คงที่
        # (placeholder) เนื่องจากยังไม่มีการแยกนับตามประเภทไอเทมที่สุ่มได้จริงในระบบ backend
        # ตอนนี้ - รอรายละเอียดเพิ่มจากผู้ใช้ว่าแต่ละประเภทควรนับอย่างไร
        self.reroll_stat_vars = {
            "rolled": tk.StringVar(value="0"),
            "found": tk.StringVar(value="0"),
            "bag": tk.StringVar(value="0"),
            "pet_plus": tk.StringVar(value="0"),
            "premium": tk.StringVar(value="0"),
            "target_pet": tk.StringVar(value="0"),
        }
        self._build_stat_mini(row1, "สุ่มแล้ว", self.reroll_stat_vars["rolled"], "info")
        self._build_stat_mini(row1, "เจอแล้ว", self.reroll_stat_vars["found"], "success")
        self._build_stat_mini(row1, "+ กระเป๋า", self.reroll_stat_vars["bag"], "warning")
        self._build_stat_mini(
            row2, "+ สัตว์", self.reroll_stat_vars["pet_plus"], "secondary"
        )
        self._build_stat_mini(
            row2, "Premium", self.reroll_stat_vars["premium"], "warning"
        )
        self._build_stat_mini(
            row2, "pet", self.reroll_stat_vars["target_pet"], "success"
        )

        found_card = tb.Labelframe(parent, text="  🎯  ไอดีที่เจอ  ", padding=10)
        found_card.pack(fill=X, pady=(0, 8))

        header_row = tb.Frame(found_card)
        header_row.pack(fill=X, pady=(0, 6))
        tb.Button(
            header_row,
            text="📋  คัดลอกทั้งหมด",
            bootstyle="secondary-outline",
            command=self._on_copy_found,
        ).pack(side=RIGHT)
        tb.Button(
            header_row,
            text="🔍 ดูรายละเอียด",
            bootstyle="info-outline",
            command=self._show_selected_detail,
        ).pack(side=RIGHT, padx=5)

        nav_row = tb.Frame(header_row)
        nav_row.pack(side=RIGHT, padx=(0, 8))
        tb.Button(
            nav_row,
            text="◄",
            width=3,
            bootstyle="secondary-outline",
            command=self._on_found_prev,
        ).pack(side=LEFT)
        self.found_page_label = tb.Label(nav_row, text="0/0", width=6, anchor="center")
        self.found_page_label.pack(side=LEFT, padx=4)
        tb.Button(
            nav_row,
            text="►",
            width=3,
            bootstyle="secondary-outline",
            command=self._on_found_next,
        ).pack(side=LEFT)

        self.found_text = ScrolledText(found_card, height=5, autohide=True, wrap="word")
        self.found_text.pack(fill=X)
        self.found_text.text.configure(state="disabled", font=("Consolas", 9))
        self._render_found_page()

    # ------------------------------------------------- left: shared panel --
    def _build_instances_card(self, parent: tb.Frame) -> None:
        card = tb.Labelframe(parent, text="  🖥  จอ MuMu instances  ", padding=10)
        card.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        btn_row = tb.Frame(card)
        btn_row.pack(fill=X, pady=(0, 8))
        self.scan_button = tb.Button(
            btn_row, text="🔍 สแกนหาจอ", bootstyle="warning", command=self._on_scan
        )
        self.scan_button.pack(side=LEFT, expand=True, fill=X, padx=(0, 4))
        # เพิ่มปุ่มเปิด Emulator
        # tb.Button(
        #     btn_row,
        #     text="🚀 เปิด Emulator",
        #     bootstyle="info",
        #     command=self._open_selected_emulator,
        # ).pack(side=LEFT, expand=True, fill=X, padx=4)
        # เพิ่มปุ่ม Restart
        # tb.Button(
        #     btn_row,
        #     text="🔄 Restart Selected",
        #     bootstyle="primary",
        #     command=self._restart_selected_instances,
        # ).pack(side=LEFT, expand=True, fill=X, padx=4)
        # tb.Button(
        #     btn_row,
        #     text="🔄 Restart All",
        #     bootstyle="primary-outline",
        #     command=self._restart_all_instances,
        # ).pack(side=LEFT, expand=True, fill=X, padx=4)
        tb.Button(
            btn_row,
            text="✅ เลือกทั้งหมด",
            bootstyle="success",
            command=self._on_select_all,
        ).pack(side=LEFT, expand=True, fill=X, padx=4)
        tb.Button(
            btn_row,
            text="🗑 ลบข้อมูลเกม",
            bootstyle="danger",
            command=self._on_clear_selected_data,
        ).pack(side=LEFT, expand=True, fill=X, padx=(4, 0))

        scroll_outer = tb.Frame(card)
        scroll_outer.pack(fill=BOTH, expand=True)
        scroll_outer.rowconfigure(0, weight=1)
        scroll_outer.columnconfigure(0, weight=1)
        self.instance_canvas = tk.Canvas(
            scroll_outer, height=100, highlightthickness=0, bg=self._checkbox_bg
        )
        scrollbar = tb.Scrollbar(
            scroll_outer, orient="vertical", command=self.instance_canvas.yview
        )
        self.instance_rows_frame = tb.Frame(self.instance_canvas)
        self.instance_rows_frame.bind(
            "<Configure>",
            lambda _e: self.instance_canvas.configure(
                scrollregion=self.instance_canvas.bbox("all")
            ),
        )
        self.instance_canvas.create_window(
            (0, 0), window=self.instance_rows_frame, anchor="nw"
        )
        self.instance_canvas.configure(yscrollcommand=scrollbar.set)
        self.instance_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.instance_warning_label = tb.Label(
            card, text="⚠ ไม่พบจอ — เปิด MuMu ก่อนแล้วสแกน", bootstyle="secondary"
        )
        self.instance_warning_label.pack(anchor=W, pady=(6, 0))

    def _themed_checkbutton(
        self, parent, text: str, variable: tk.BooleanVar
    ) -> tk.Checkbutton:
        """Plain (non-ttk) Checkbutton, styled to blend with the ttkbootstrap theme.

        We avoid ttk/ttkbootstrap's styled Checkbutton here (default indicator style)
        because on some Tcl/Tk + Pillow combinations it segfaults when the window is
        destroyed. Toolbutton-style ttkbootstrap Checkbuttons (used in the header) are
        unaffected since they don't use the custom image-based indicator.
        """
        return tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            bg=self._checkbox_bg,
            fg=self._checkbox_fg,
            activebackground=self._checkbox_bg,
            activeforeground=self._checkbox_fg,
            selectcolor="#ffffff",
            highlightthickness=0,
            bd=0,
            anchor="w",
        )

    def _build_stat_mini(
        self, parent: tb.Frame, caption: str, var: tk.StringVar, style: str
    ) -> None:
        box = tb.Frame(parent, padding=(4, 2))
        box.pack(side=LEFT, expand=True, fill=X, padx=2)
        tb.Label(
            box,
            textvariable=var,
            font=("Segoe UI", 18, "bold"),
            bootstyle=style,
            anchor="center",
        ).pack(fill=X)
        tb.Label(
            box, text=caption, bootstyle="secondary", anchor="center", font=("Segoe UI", 8)
        ).pack(fill=X)

    def _build_log_card(self, parent: tb.Frame) -> None:
        card = tb.Labelframe(parent, text="  📋  Log การทำงาน  ", padding=10)
        card.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        header_row = tb.Frame(card)
        header_row.pack(fill=X, pady=(0, 6))
        tb.Button(
            header_row,
            text="🗑  ล้าง",
            bootstyle="secondary-outline",
            command=self._on_clear_log,
        ).pack(side=RIGHT)
        self.log_filter_combo = tb.Combobox(
            header_row,
            textvariable=self.current_log_filter,
            values=[_ALL_SCREENS_LABEL],
            state="readonly",
            width=18,
        )
        self.log_filter_combo.pack(side=RIGHT, padx=(0, 8))
        self.log_filter_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._rerender_log()
        )

        self.log_text = ScrolledText(card, height=12, autohide=True, wrap="word")
        self.log_text.pack(fill=BOTH, expand=True)
        self.log_text.text.configure(state="disabled", font=("Consolas", 9))

    # ------------------------------------------------------------ bottom --
    def _build_control_bar(self, parent: tb.Frame) -> None:
        footer = tb.Labelframe(parent, text="", padding=(16, 12))
        footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        parent.columnconfigure(0, weight=1)

        bar = tb.Frame(footer)
        bar.pack(fill=X)

        # ---------------- Status ----------------
        self.status_label = tb.Label(
            bar,
            text="● พร้อม",
            bootstyle="secondary",
            font=("Segoe UI", 10, "bold"),
        )
        self.status_label.pack(side=LEFT, padx=(6, 0), pady=2)

        # ---------------- Buttons ----------------
        btn_row = tb.Frame(bar)
        btn_row.pack(side=RIGHT)

        BTN_WIDE = 16
        BTN_NORMAL = 11

        self.start_selected_button = tb.Button(
            btn_row,
            text="▶ เริ่มที่เลือก",
            bootstyle="primary",
            command=self._start_selected_instances,
            width=BTN_WIDE,
        )

        self.start_button = tb.Button(
            btn_row,
            text="▶ เริ่มทั้งหมด",
            bootstyle="success",
            command=self._on_start,
            width=BTN_WIDE,
        )

        self.pause_button = tb.Button(
            btn_row,
            text="⏸ พัก",
            bootstyle="warning-outline",
            command=self._on_pause,
            width=BTN_NORMAL,
        )

        self.resume_button = tb.Button(
            btn_row,
            text="▶ ทำต่อ",
            bootstyle="info-outline",
            command=self._on_resume,
            width=BTN_NORMAL,
        )

        self.cancel_button = tb.Button(
            btn_row,
            text="◼ ยกเลิก",
            bootstyle="danger-outline",
            command=self._on_cancel,
            width=BTN_NORMAL,
        )

        buttons = (
            self.start_selected_button,
            self.start_button,
            self.pause_button,
            self.resume_button,
            self.cancel_button,
        )

        for btn in buttons:
            btn.pack(side=LEFT, padx=4, pady=2)

    def _open_selected_emulator(self) -> None:
        """เปิด Emulator ที่เลือก"""
        selected = self._checked_instances()
        if not selected:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกจอก่อน")
            return

        for inst in selected:
            try:
                # ใช้ MuMuManager เปิด
                import subprocess
                cmd = [self.config_obj.get("emulator.mumu_manager_path"), "control", str(inst.index), "open"]
                subprocess.Popen(cmd)
                log.info(f"เปิด Emulator {inst.name} สำเร็จ")
            except Exception as e:
                log.error(f"เปิด Emulator ล้มเหลว: {e}")

    def _restart_selected_instances(self) -> None:
        """เริ่มการทำงานใหม่เฉพาะจอที่เลือก"""
        selected = self._checked_instances()
        if not selected:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกจอที่ต้องการ restart")
            return

        if not messagebox.askyesno("ยืนยัน", f"ต้องการ restart {len(selected)} จอที่เลือกหรือไม่?"):
            return

        # หยุด worker เดิมถ้ามี
        if self.worker and self.worker.is_alive():
            self.control.stop()

        # เริ่มใหม่เฉพาะจอที่เลือก
        self.control.reset()

        def _notify_finished():
            self.after(0, self._on_worker_finished)

        self.worker = AutomationWorker(
            config=self.config_obj,
            instances=selected,          # ใช้เฉพาะจอที่เลือก
            stats=self.stats,
            control=self.control,
            recorder=self.recorder,
            on_finished=_notify_finished,
            mode=self.current_mode.get(),
            found_queue=self.found_queue,
            discord=self.discord,
        )
        self.worker.start()
        self._set_status_running()
        log.info(f"เริ่มการทำงานใหม่ {len(selected)} จอ")

    def _restart_all_instances(self) -> None:
        """เริ่มการทำงานใหม่ทั้งหมด"""
        if not messagebox.askyesno("ยืนยัน", "ต้องการ restart ทุกจอหรือไม่?"):
            return

        if self.worker and self.worker.is_alive():
            self.control.stop()

        self.control.reset()

        def _notify_finished():
            self.after(0, self._on_worker_finished)

        self.worker = AutomationWorker(
            config=self.config_obj,
            instances=self.instances,   # ทุกจอ
            stats=self.stats,
            control=self.control,
            recorder=self.recorder,
            on_finished=_notify_finished,
            mode=self.current_mode.get(),
            found_queue=self.found_queue,
            discord=self.discord,
        )
        self.worker.start()
        self._set_status_running()
    def _start_selected_instances(self) -> None:
        """เริ่มการทำงานเฉพาะจอที่เลือก"""
        selected = self._selected_instances()
        if not selected:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกจออย่างน้อย 1 จอ")
            return

        self.control.reset()

        def _notify_finished():
            self.after(0, self._on_worker_finished)

        self.worker = AutomationWorker(
            config=self.config_obj,
            instances=selected,               # ← เฉพาะที่เลือก
            stats=self.stats,
            control=self.control,
            recorder=self.recorder,
            on_finished=_notify_finished,
            mode=self.current_mode.get(),
            found_queue=self.found_queue,
            discord=self.discord,
        )
        self.worker.start()
        self._set_status_running()
        log.info(f"เริ่มทำงานเฉพาะ {len(selected)} จอที่เลือก")

    # ------------------------------------------------------- log plumbing --
    def _poll_log_queue(self) -> None:
        try:
            while True:
                line = self.log_queue.get_nowait()
                self._append_log(line)
        except queue.Empty:
            pass
        self.after(200, self._poll_log_queue)

    def _append_log(self, line: str) -> None:
        self.log_lines.append(line)
        if len(self.log_lines) > 2000:   # ลดจาก 3000 เพื่อความเร็ว
            self.log_lines = self.log_lines[-2000:]
        
        if self._line_matches_filter(line):
            self._write_log_line(line)

    def _line_matches_filter(self, line: str) -> bool:
        """กรอง log ให้แสดงเฉพาะจอที่เลือก"""
        filt = self.current_log_filter.get()
        
        if filt == _ALL_SCREENS_LABEL:
            return True
        
        # กรองให้ตรงเป๊ะมากขึ้น
        return f"[{filt}]" in line or f"{filt} " in line or f"{filt}|" in line

    def _write_log_line(self, line: str) -> None:
        widget = self.log_text.text
        widget.configure(state="normal")
        widget.insert("end", line + "\n")
        widget.see("end")
        widget.configure(state="disabled")

    def _rerender_log(self) -> None:
        widget = self.log_text.text
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.configure(state="disabled")
        for line in self.log_lines:
            if self._line_matches_filter(line):
                self._write_log_line(line)

    def _refresh_log_filter_options(self) -> None:
        names = [inst.name for inst in self.instances]
        self.log_filter_combo.configure(values=[_ALL_SCREENS_LABEL, *names])
        
        # ตั้งค่าเริ่มต้นเป็น ALL
        if not self.current_log_filter.get() or self.current_log_filter.get() not in names:
            self.current_log_filter.set(_ALL_SCREENS_LABEL)

    def _on_clear_log(self) -> None:
        self.log_lines.clear()
        widget = self.log_text.text
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.configure(state="disabled")

    # -------------------------------------------------- found-ids plumbing --
    def _poll_found_queue(self) -> None:
        changed = False
        try:
            while True:
                item = self.found_queue.get_nowait()
                self.found_items.append(item)
                changed = True
        except queue.Empty:
            pass
        if changed:
            self.found_page_index = max(
                0, (len(self.found_items) - 1) // _FOUND_PAGE_SIZE
            )
            self._render_found_page()
        self.after(300, self._poll_found_queue)

    def _render_found_page(self) -> None:
        widget = self.found_text.text
        widget.configure(state="normal")
        widget.delete("1.0", "end")

        total = len(self.found_items)
        if total == 0:
            widget.insert("end", "ยังไม่มี — กำลังสุ่ม...")
            self.found_page_label.configure(text="0/0")
        else:
            total_pages = max(1, (total + _FOUND_PAGE_SIZE - 1) // _FOUND_PAGE_SIZE)
            self.found_page_index = min(self.found_page_index, total_pages - 1)
            start = self.found_page_index * _FOUND_PAGE_SIZE
            page_items = self.found_items[start : start + _FOUND_PAGE_SIZE]
            widget.insert("end", "\n".join(page_items))
            self.found_page_label.configure(
                text=f"{self.found_page_index + 1}/{total_pages}"
            )

        widget.configure(state="disabled")

    def _on_found_prev(self) -> None:
        if self.found_page_index > 0:
            self.found_page_index -= 1
            self._render_found_page()

    def _on_found_next(self) -> None:
        total_pages = max(
            1, (len(self.found_items) + _FOUND_PAGE_SIZE - 1) // _FOUND_PAGE_SIZE
        )
        if self.found_page_index < total_pages - 1:
            self.found_page_index += 1
            self._render_found_page()

    def _on_copy_found(self) -> None:
        if not self.found_items:
            messagebox.showinfo("แจ้งเตือน", "ยังไม่มีไอดีที่เจอให้คัดลอก")
            return
        self.clipboard_clear()
        self.clipboard_append("\n".join(self.found_items))
        messagebox.showinfo(
            "คัดลอกแล้ว", f"คัดลอกไอดีที่เจอทั้งหมด {len(self.found_items)} รายการแล้ว"
        )
    def _show_found_detail(self, account_id):
        # หาข้อมูลจาก self.found_items หรือ database
        data = next((item for item in self.found_items if account_id in item), None)
        if data:
            popup = FoundDetailPopup(self, {"account_id": account_id, "screenshot": "logs/xxx.png"})
            popup.grab_set()
    def _show_selected_detail(self):
        """แสดง Popup รายละเอียดไอดีที่เลือก"""
        try:
            # ดึงข้อมูลจาก found_text (หรือเก็บใน list)
            selected_text = self.found_text.text.get("sel.first", "sel.last")
            if not selected_text:
                messagebox.showinfo("แจ้งเตือน", "กรุณาเลือกไอดีที่ต้องการดูรายละเอียด")
                return

            account_id = selected_text.split("|")[2].strip() if "|" in selected_text else selected_text.strip()

            # สร้างข้อมูลตัวอย่าง (คุณสามารถดึงจาก database ได้)
            data = {
                "account_id": account_id,
                "timestamp": "2026-07-08 19:xx",
                "treasures": "Victor’s Feather Laurel Wreath, Jingle-jangle Coin Wallet",
                "pets": "Tater Trader",
                "screenshot": f"logs/found_pet_{account_id}.png"
            }

            popup = FoundDetailPopup(self, data)
            popup.grab_set()
        except:
            messagebox.showwarning("แจ้งเตือน", "ไม่สามารถแสดงรายละเอียดได้")

    # ------------------------------------------------------------ stats --
    def _poll_stats(self) -> None:
        started, success, failed, remaining = self.stats.snapshot()
        self.stat_vars["started"].set(str(started))
        self.stat_vars["success"].set(str(success))
        self.stat_vars["failed"].set(str(failed))
        self.stat_vars["remaining"].set(str(remaining))
        target = self.stats.target or 1
        self.progress_bar.configure(value=min(started / target * 100, 100))

        # โหมดรีไอดี: "สุ่มแล้ว"/"เจอแล้ว" ใช้ตัวนับเดียวกับ started/success ด้านบน
        # ส่วน + กระเป๋า/+ สัตว์/Premium/pet ยังเป็น placeholder (ดูหมายเหตุใน _build_reroll_right)
        self.reroll_stat_vars["rolled"].set(str(started))
        self.reroll_stat_vars["found"].set(str(success))

        self.after(500, self._poll_stats)

    # --------------------------------------------------------- scanning --
    def _on_scan(self) -> None:
        self.scan_button.configure(state="disabled", text="กำลังสแกน...")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        try:
            instances = emulator_scanner.scan(self.config_obj)
        except Exception:
            log.exception("สแกนหา MuMuPlayer ล้มเหลว")
            instances = []
        self.after(0, lambda: self._on_scan_done(instances))

    def _on_scan_done(self, instances) -> None:
        self.instances = instances
        for widget in self.instance_rows_frame.winfo_children():
            widget.destroy()
        self.instance_vars = {}

        for i, inst in enumerate(instances):
            var = tk.BooleanVar(value=True)
            self.instance_vars[i] = var
            self.instance_status[i] = "stopped"
            
            port = inst.adb_address.rsplit(":", 1)[-1]
            window = inst.window.title if getattr(inst, 'window', None) else "ไม่พบ"
            
            label = f"จอ {i} • {inst.name} • port {port}\n   └ {window} [{self.instance_status[i]}]"
            # ... pack
            self._themed_checkbutton(self.instance_rows_frame, label, var).pack(
                anchor=W, pady=2, fill=X
            )

        self._refresh_log_filter_options()
        
        self.instance_warning_label.configure(
            text="" if instances else "⚠ ไม่พบจอ — เปิด MuMu ก่อนแล้วสแกน"
        )
        self.scan_button.configure(state="normal", text="🔍 สแกนหาจอ")

    def _on_select_all(self) -> None:
        if not self.instance_vars:
            return
        all_checked = all(v.get() for v in self.instance_vars.values())
        for v in self.instance_vars.values():
            v.set(not all_checked)

    def _on_clear_selected_data(self) -> None:
        selected = self._checked_instances()
        if not selected:
            messagebox.showinfo("แจ้งเตือน", "กรุณาเลือกจอที่ต้องการลบข้อมูลเกมก่อน")
            return
        if not messagebox.askyesno(
            "ยืนยัน", f"ต้องการลบข้อมูลเกมของ {len(selected)} จอที่เลือกหรือไม่?"
        ):
            return
        threading.Thread(
            target=self._clear_data_worker, args=(selected,), daemon=True
        ).start()

    def _clear_data_worker(self, instances) -> None:
        adb_path = emulator_scanner.resolve_adb_path(self.config_obj)
        package_name = self.config_obj.get("game.package_name")
        for inst in instances:
            try:
                adb = AdbClient(adb_path=adb_path, address=inst.adb_address)
                adb.connect()
                adb.clear_app_data(package_name)
                log.info("[%s] ลบข้อมูลเกมสำเร็จ", inst.name)
            except Exception:
                log.exception("[%s] ลบข้อมูลเกมล้มเหลว", inst.name)

    # ---------------------------------------------------------- controls --
    def _checked_instances(self) -> list:
        return [self.instances[i] for i, v in self.instance_vars.items() if v.get()]

    def _selected_instances(self) -> list:
        checked = self._checked_instances()
        return checked if checked else list(self.instances)

    def _save_settings_to_config(self) -> None:
        cfg = self.config_obj
        cfg.set("referral.link", self.referral_link_var.get())
        cfg.set("referral.send_before_open", bool(self.send_referral_var.get()))
        cfg.set("run.target_account_count", int(self.target_count_var.get()))
        cfg.set("run.cleanup_method", self.cleanup_method_var.get())
        cfg.set(
            "run.create_new_account_each_cycle", bool(self.create_new_account_var.get())
        )
        cfg.set("reroll.rolls_per_round", int(self.rolls_per_round_var.get()))
        cfg.set("reroll.unlimited_rolls", bool(self.unlimited_rolls_var.get()))
        cfg.set("reroll.enable_treasure", bool(self.reroll_treasure_var.get()))
        cfg.set("reroll.enable_pet_luxury", bool(self.reroll_pet_var.get()))
        cfg.set("telegram.bot_token", self.telegram_bot_token_var.get())
        cfg.set("telegram.chat_id", self.telegram_chat_id_var.get())
        cfg.set("discord.found_webhook_url",self.discord_found_webhook_var.get())
        cfg.set("discord.status_webhook_url",self.discord_status_webhook_var.get())
        cfg.set("discord.error_webhook_url",self.discord_error_webhook_var.get())
        try:
            cfg.save()
        except Exception:
            log.exception(
                "บันทึกค่าคอนฟิกกลับไฟล์ config.yaml ไม่สำเร็จ (จะยังใช้ค่าปัจจุบันในโปรแกรมต่อไป)"
            )

    def _on_start(self) -> None:
        if not self.instances:
            messagebox.showwarning("แจ้งเตือน", "ยังไม่พบจอ MuMu กรุณาสแกนจอก่อนเริ่มทำงาน")
            return

        target_pet = self.config_obj.get("game.target_pet")
        if not target_pet or target_pet == "CHANGE_ME":
            messagebox.showwarning(
                "แจ้งเตือน",
                "กรุณาตั้งค่า game.target_pet ใน config/config.yaml ให้ตรงกับชื่อไฟล์ template "
                "ของสัตว์เลี้ยงที่ต้องการก่อนเริ่มทำงาน",
            )
            return

        mode = self.current_mode.get()
        selected = self._selected_instances()
        self._save_settings_to_config()

        self.stats.set_target(
            int(self.target_count_var.get()) if mode == "referral" else 0
        )
        self.control.reset()
        
        def _notify_finished():
            self.after(0, self._on_worker_finished)

        self.worker = AutomationWorker(
            config=self.config_obj,
            instances=self.instances,      # ← ทุกจอ
            stats=self.stats,
            control=self.control,
            recorder=self.recorder,
            on_finished=_notify_finished,
            mode=mode,
            found_queue=self.found_queue,
            discord=self.discord,
        )

        self.worker.start()
        self._set_status_running()

        log.info("เริ่มทำงานทุกจอ (%d จอ)", len(self.instances))

    def _notify_finished() -> None:
        self.after(0, self._on_worker_finished)

        self.worker = AutomationWorker(
            config=self.config_obj,
            instances=selected,
            stats=self.stats,
            control=self.control,
            recorder=self.recorder,
            on_finished=_notify_finished,
            mode=mode,
            found_queue=self.found_queue,
            discord=self.discord,
        )
        self.worker.start()
        self._set_status_running()

    def _on_pause(self) -> None:
        self.control.pause()
        self._set_status_paused()

    def _on_resume(self) -> None:
        self.control.resume()
        self._set_status_running()

    def _on_cancel(self) -> None:
        self.control.stop()
        self.control.resume()  # release any pause-wait loop so cancellation propagates immediately
        self._set_status("● กำลังยกเลิก...", "danger")
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="disabled")
        self.resume_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")

    def _on_worker_finished(self) -> None:
        self._set_status_idle()

    # ------------------------------------------------------------ status --
    def _set_status(self, text: str, style: str) -> None:
        self.status_label.configure(text=text, bootstyle=style)

    def _set_status_idle(self) -> None:
        self._set_status("● พร้อม", "secondary")
        self.start_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.resume_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")

    def _set_status_running(self) -> None:
        self._set_status("● กำลังทำงาน...", "success")
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.resume_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

    def _set_status_paused(self) -> None:
        self._set_status("● หยุดชั่วคราว", "warning")
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="disabled")
        self.resume_button.configure(state="normal")
        self.cancel_button.configure(state="normal")

    def _update_instance_status(self, index: int, status: str):
        self.instance_status[index] = status
        # Refresh UI (เรียกใหม่ทั้งหมดหรืออัพเดทเฉพาะ)
        self.after(0, self._on_scan)  # หรือ refresh เฉพาะ row


def main() -> None:
    app = BotApp()
    app.mainloop()


if __name__ == "__main__":
    main()
