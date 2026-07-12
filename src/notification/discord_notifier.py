"""Discord Notifier สำหรับแจ้งเมื่อเจอของดี"""

from __future__ import annotations

import requests
from pathlib import Path

from src.core.logger import get_logger

log = get_logger(__name__)


class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip()
        self.enabled = bool(webhook_url and webhook_url.startswith("https://discord.com/api/webhooks"))

    def send_found_account(self, account_id: str, target_item: str, screenshot_path: str | None = None):
        """ส่งแจ้งเตือนเมื่อเจอทั้งสมบัติ + สัตว์เลี้ยง"""
        if not self.enabled:
            return

        embed = {
            "title": "🎉 เจอของเป้าหมายแล้ว!",
            "description": f"**Account ID**: `{account_id}`\n**ของที่ได้**: {target_item}",
            "color": 0x00ff00,  # สีเขียว
            "timestamp": "now"
        }

        data = {
            "username": "Nongku BOT",
            "embeds": [embed]
        }

        files = {}
        if screenshot_path and Path(screenshot_path).exists():
            try:
                files = {"file": open(screenshot_path, "rb")}
                data["content"] = f"เจอ {target_item} จาก {account_id}"
            except Exception as e:
                log.warning(f"ไม่สามารถแนบรูปภาพ: {e}")

        try:
            response = requests.post(self.webhook_url, data=data, files=files if files else None, timeout=10)
            if response.status_code in (200, 204):
                log.info("ส่งแจ้งเตือน Discord สำเร็จ")
            else:
                log.warning(f"ส่ง Discord ไม่สำเร็จ: {response.status_code} {response.text}")
        except Exception as e:
            log.error(f"เชื่อมต่อ Discord ล้มเหลว: {e}")
        finally:
            if files and "file" in files:
                files["file"].close()