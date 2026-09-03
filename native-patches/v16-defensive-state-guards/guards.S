.syntax unified
.thumb
.section .text
.align 2

.extern ccash_get
.extern safe_get
.extern exp_get
.extern chsp_get
.extern pocket_return
.extern pocket_reject_return
.extern pet_get
.extern pet_count
.extern table_rows
.extern inventory_return
.extern inventory_reject_return

.global pocket_guard
.thumb_func
pocket_guard:
    ldr     r0, [r5, #0x18]
    adr     r1, game_start
    bl      string_equal
    cmp     r0, #0
    bne     check_pocket

    ldr     r0, [r5, #0x18]
    adr     r1, update_pet
    bl      string_equal
    cmp     r0, #0
    bne     check_pocket

    ldr     r0, [r5, #0x18]
    adr     r1, upload_pocket
    bl      string_equal
    cmp     r0, #0
    beq     pocket_normal

check_pocket:
    bl      ccash_get
    adds    r0, #0x40
    bl      safe_get
    ldr     r1, [r5, #0x2c]
    cmp     r1, r0
    blt     pocket_reject

    bl      exp_get
    bl      safe_get
    ldr     r1, [r5, #0x34]
    cmp     r1, r0
    blt     pocket_reject

pocket_normal:
    bl      chsp_get
    b.w     pocket_return

pocket_reject:
    b.w     pocket_reject_return

string_equal:
1:
    ldrb    r2, [r0]
    adds    r0, #1
    ldrb    r3, [r1]
    adds    r1, #1
    cmp     r2, r3
    bne     2f
    cmp     r2, #0
    bne     1b
    movs    r0, #1
    bx      lr
2:
    movs    r0, #0
    bx      lr

.align 2
game_start:
    .asciz "GameStart"
update_pet:
    .asciz "UpdatePet"
upload_pocket:
    .asciz "UploadPocket"

.align 2
.global inventory_guard
.thumb_func
inventory_guard:
    bl      pet_get
    mov     r4, r0
    bl      pet_count
    cmp     r0, #0
    ble     inventory_normal

    mov     r0, r10
    bl      table_rows
    cmp     r0, #1
    ble     inventory_reject

inventory_normal:
    mov     r0, r4
    b.w     inventory_return

inventory_reject:
    b.w     inventory_reject_return
