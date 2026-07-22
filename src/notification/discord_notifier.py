"""Discord Notifier สำหรับแจ้งเมื่อเจอของดี และจบ instance"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.core.logger import get_logger
from src.models.account_info import AccountInfo

log = get_logger(__name__)


class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip()
        self.enabled = bool(webhook_url and webhook_url.startswith("https://discord.com/api/webhooks"))

    def send_found_account(
        self,
        account: AccountInfo,
    ):
        """แจ้งเมื่อเจอของดี"""
        if not self.enabled:
            return

        treasure_text = (
            "\n".join(f"• {t}" for t in account.treasures)
            if account.treasures
            else "-"
        )

        embed = {
            "title": "🎉 Found Target Account",
            "color": 0x2ECC71,
            "timestamp": account.found_time.astimezone(timezone.utc).isoformat(),
            "fields": [
                {
                    "name": "📧 Email",
                    "value": f"`{account.email}`",
                    "inline": False,
                },
                {
                    "name": "🔑 Password",
                    "value": f"`{account.password}`",
                    "inline": False,
                },
                {
                    "name": "🐾 Pet",
                    "value": account.pet_name or "-",
                    "inline": True,
                },
                {
                    "name": "💎 Treasure",
                    "value": treasure_text,
                    "inline": True,
                },
            ],
        }

        payload = {
            "username": "Nongku BOT",
            "embeds": [embed],
        }

        files = None

        if account.pet_image_path and Path(account.pet_image_path).exists():
            files = {
                "file": open(account.pet_image_path, "rb")
            }
            embed["image"] = {
                "url": "attachment://file"
            }
            payload["content"] = (
                f"🎉 {account.email}\n"
                f"🐾 {account.pet_name}"
            )

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

    def send_embed(
        self,
        title: str,
        outcome: str,
        error: str | None = None,
    ):
        """
        ส่ง Discord Embed สำหรับแจ้งสถานะ instance
        """

        if not self.enabled:
            return


        # สี Embed
        if error:
            color = 0xE74C3C   # แดง
            status_icon = "❌ ERROR"
        else:
            color = 0x2ECC71   # เขียว
            status_icon = "✅ SUCCESS"


        fields = [
            {
                "name": "📌 Status",
                "value": status_icon,
                "inline": True,
            },
            {
                "name": "📋 Outcome",
                "value": str(outcome),
                "inline": True,
            },
            {
                "name": "🕒 Time",
                "value": datetime.now(
                    timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "inline": False,
            },
        ]


        if error:
            # กัน Discord limit
            if len(error) > 1000:
                error = error[-1000:]

            fields.append(
                {
                    "name": "🔥 Error Detail",
                    "value": f"```python\n{error}\n```",
                    "inline": False,
                }
            )


        payload = {
            "username": "Nongku BOT",

            "embeds": [
                {
                    "title": title,

                    "color": color,

                    "fields": fields,

                    "footer": {
                        "text": "CookieRun Automation System"
                    },

                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
            ],
        }


        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )

            if response.status_code in (200, 204):
                log.info(
                    "ส่ง Discord Embed สำเร็จ"
                )

            else:
                log.warning(
                    "ส่ง Discord ไม่สำเร็จ: %s %s",
                    response.status_code,
                    response.text,
                )

        except Exception:
            log.exception(
                "เชื่อมต่อ Discord ล้มเหลว"
            )