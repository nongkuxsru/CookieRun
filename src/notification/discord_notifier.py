"""Discord Notifier สำหรับแจ้งเมื่อเจอของดี และจบ instance"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.core.logger import get_logger

log = get_logger(__name__)


class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip()
        self.enabled = bool(webhook_url and webhook_url.startswith("https://discord.com/api/webhooks"))

    def send_found_account(
        self,
        account_id: str,
        target_item: str,
        screenshot_path: str | None = None,
    ):
        """แจ้งเมื่อเจอของดี"""
        if not self.enabled:
            return

        embed = {
            "title": "🎉 เจอของเป้าหมายแล้ว!",
            "description": (
                f"**Account ID**: `{account_id}`\n"
                f"**ของที่ได้**: {target_item}"
            ),
            "color": 0x00FF00,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        payload = {
            "username": "Nongku BOT",
            "embeds": [embed],
        }

        files = None

        if screenshot_path and Path(screenshot_path).exists():
            files = {
                "file": open(screenshot_path, "rb")
            }
            payload["content"] = f"เจอ {target_item}\nAccount: {account_id}"

        try:
            if files:
                response = requests.post(
                    self.webhook_url,
                    data={"payload_json": json.dumps(payload)},
                    files=files,
                    timeout=10,
                )
            else:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10,
                )

            if response.status_code in (200, 204):
                log.info("ส่งแจ้งเตือน Discord สำเร็จ")
            else:
                log.warning(
                    "ส่ง Discord ไม่สำเร็จ: %s %s",
                    response.status_code,
                    response.text,
                )

        except Exception:
            log.exception("เชื่อมต่อ Discord ล้มเหลว")

        finally:
            if files:
                files["file"].close()

    def send_message(self, message: str):
        """ส่งข้อความธรรมดา (เช่น จบ instance)"""
        if not self.enabled:
            return

        payload = {
            "username": "Nongku BOT",
            "content": message
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )

            if response.status_code in (200, 204):
                log.info("ส่งข้อความ Discord สำเร็จ")
            else:
                log.warning(
                    "ส่ง Discord ไม่สำเร็จ: %s %s",
                    response.status_code,
                    response.text,
                )
        except Exception:
            log.exception("เชื่อมต่อ Discord ล้มเหลว")