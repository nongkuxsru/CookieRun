# แนวทางการตั้งชื่อไฟล์ Template

ไฟล์ในโฟลเดอร์นี้คือรูปภาพอ้างอิง (template) ที่ระบบใช้เทียบกับภาพหน้าจอจริง
ผ่าน OpenCV template matching (`src/core/image_matcher.py`) เพื่อยืนยันว่าตอนนี้
อยู่หน้าจอไหน ก่อนจะกดปุ่มหรือทำ action ต่อไป

## วิธีสร้างไฟล์ template

ใช้เครื่องมือ `tools/calibrate.py` (ดูวิธีใช้ใน README.md หลัก) ซึ่งจะถ่ายภาพหน้าจอ
จริงจาก MuMuPlayer แล้วให้ลากกรอบเลือกปุ่ม/องค์ประกอบที่ต้องการ ตัดและบันทึกเป็นไฟล์
`.png` ให้อัตโนมัติ

## โครงสร้างโฟลเดอร์

- `login/` - รูปที่ใช้ในขั้นตอนเปิดเกม/ล็อกอินโหมด Dev
  - `splash_skip_button.png`, `dev_mode_button.png`, `dev_mode_confirm_button.png`,
    `lobby_marker.png` (ดูชื่อที่อ้างอิงจริงใน `src/automation/game_flow.py`)
- `pet_reroll/` - รูปที่ใช้ในขั้นตอนสุ่มสัตว์เลี้ยง
  - `hatch.png`, `skip_hatch.png`, `close_popup_newpet.png` (ปิดหน้าต่างสัตว์เลี้ยงใหม่ก่อนสุ่มต่อ),
    `close_hatch_popup.png`, `close_bag_pet.png`, `Crystals_left.png`, `Crystals_left_close.png`
  - รูปสัตว์เลี้ยงเป้าหมาย: ชื่อไฟล์ต้องตรงกับค่า `game.target_pet` ใน config.yaml
    เช่นถ้าตั้ง `target_pet: "white_lily"` ต้องมีไฟล์ `pet_reroll/white_lily.png`
- `treasure_reroll/` - รูปที่ใช้ในขั้นตอนสุ่มสมบัติ
  - `draw_treasure.png`, `click_free_treasure.png`, `skip_treasure.png`,
    `close_popup_newtreasure.png` (ปิดหน้าต่างสมบัติใหม่ก่อนสุ่มต่อ),
    `close_treasure_draw.png`, `close_treasure_bag.png`
  - รูปสมบัติเป้าหมาย: ชื่อไฟล์ต้องตรงกับค่า `game.target_treasure` ใน config.yaml

## เคล็ดลับให้แม่นยำ

- ตัดกรอบให้แน่น เฉพาะส่วนที่มีลักษณะเฉพาะ (ไอคอน/ข้อความ) หลีกเลี่ยงพื้นที่ที่มีสี
  พื้นเดียวกว้าง ๆ เพราะจะจับคู่มั่ว
- ถ้าหน้าจอมีข้อความที่เปลี่ยนได้ (เช่นตัวเลขเพชร) ให้ตัดกรอบเฉพาะกรอบ/ไอคอนที่ "คงที่"
  รอบข้อความนั้น ไม่ใช่ตัวเลขเอง
- ถ้าจับคู่ไม่แม่นยำ ให้ปรับ `templates.match_threshold` ใน config.yaml
  (ค่าเริ่มต้น 0.85, ลดลงถ้าจับไม่ติด, เพิ่มขึ้นถ้าจับผิดตัว)
- เก็บภาพ error ที่ระบบบันทึกอัตโนมัติไว้ที่ `logs/errors/` มาช่วยตรวจสอบว่าทำไม step
  ไม่ผ่าน
