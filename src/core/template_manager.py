"""
Central registry for template assets.

ทุก Controller ควรอ้างอิง Template จากไฟล์นี้
แทนการใช้ string path โดยตรง
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateAsset:
    """ข้อมูลของ Template หนึ่งไฟล์"""

    path: str
    threshold: float = 0.85


# ==========================================================
# Login
# ==========================================================

class LoginTemplates:
    DEV_MODE = TemplateAsset("login/dev_mode_button.png")
    EMAIL_BUTTON = TemplateAsset("login/login_email_button.png")
    EMAIL_BOX = TemplateAsset("login/email_box.png")
    PASSWORD_BOX_1 = TemplateAsset("login/password_box_1st.png")
    PASSWORD_BOX_2 = TemplateAsset("login/password_box_2nd.png")
    SUBMIT_PASSWORD = TemplateAsset("login/submit_password.png")
    ERROR_40212 = TemplateAsset("login/error_40212.png")
    LOBBY = TemplateAsset("login/lobby_marker.png")


# ==========================================================
# Treasure
# ==========================================================

class TreasureTemplates:
    ENTER = TemplateAsset("treasure_reroll/enter_treasure.png")
    DRAW = TemplateAsset("treasure_reroll/draw_treasure.png")
    FREE = TemplateAsset("treasure_reroll/click_free_treasure.png")
    SKIP = TemplateAsset("treasure_reroll/skip_treasure.png")

    CLOSE_DRAW = TemplateAsset("treasure_reroll/close_treasure_draw.png")
    CLOSE_BAG = TemplateAsset("treasure_reroll/close_treasure_bag.png")
    CLOSE_NEW = TemplateAsset("treasure_reroll/close_popup_newtreasure.png")

    ENTER_CABINET = TemplateAsset("treasure_reroll/enter_treasure_cabinet.png")
    CLOSE_CABINET = TemplateAsset("treasure_reroll/close_treasure_cabinet.png")

    TICKET_EMPTY = TemplateAsset("treasure_reroll/ticket_left.png")

    VICTOR = TemplateAsset(
        "treasure_reroll/Victor_Feather_Laurel_Wreath.png"
    )

    BANANA = TemplateAsset(
        "treasure_reroll/Dropped_Banana_Peel.png"
    )

    COIN = TemplateAsset(
        "treasure_reroll/coin_wallet.png"
    )

    TARGETS = {
        "Victor_Feather_Laurel_Wreath": VICTOR,
        "Dropped_Banana_Peel": BANANA,
        "coin_wallet": COIN,
    }


# ==========================================================
# Popup
# ==========================================================

class PopupTemplates:
    CLOSE_01 = TemplateAsset("popup/close_popup_01.png")
    CLOSE_02 = TemplateAsset("popup/close_popup_02.png")
    CLOSE_03 = TemplateAsset("popup/close_popup_03.png")

    ALL = (
        CLOSE_01,
        CLOSE_02,
        CLOSE_03,
    )


# ==========================================================
# Daily Checkin
# ==========================================================

class DailyCheckinTemplates:
    CONFIRM_01 = TemplateAsset("daily_checkin_popup/confirm_01.png")
    CONFIRM_02 = TemplateAsset("daily_checkin_popup/confirm_02.png")
    CONFIRM_03 = TemplateAsset("daily_checkin_popup/confirm_03.png")
    CLOSE = TemplateAsset("daily_checkin_popup/confirm_close.png")


# ==========================================================
# Free Item
# ==========================================================

class FreeItemTemplates:
    CONFIRM_01 = TemplateAsset("free_item/confirm_01.png")
    CONFIRM_02 = TemplateAsset("free_item/confirm_02.png")
    CONFIRM_03 = TemplateAsset("free_item/confirm_03.png")
    CONFIRM_04 = TemplateAsset("free_item/confirm_04.png")
    CONFIRM_05 = TemplateAsset("free_item/confirm_05.png")
    CONFIRM_06 = TemplateAsset("free_item/confirm_06.png")


# ==========================================================
# Pet
# ==========================================================

class PetTemplates:
    """
    จะย้าย Template ของ Pet มาไว้ที่นี่
    ใน Phase ถัดไป
    """
    pass


# ==========================================================
# Root
# ==========================================================

class Templates:
    LOGIN = LoginTemplates
    TREASURE = TreasureTemplates
    POPUP = PopupTemplates
    DAILY = DailyCheckinTemplates
    FREE_ITEM = FreeItemTemplates
    PET = PetTemplates