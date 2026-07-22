from __future__ import annotations

import customtkinter as ctk

from src.models.account_info import AccountInfo


class FoundAccountDialog(ctk.CTkToplevel):
    def __init__(self, master, account: AccountInfo):
        super().__init__(master)

        self.title("Target Found")
        self.geometry("650x520")

        self.account = account

        self._build_ui()