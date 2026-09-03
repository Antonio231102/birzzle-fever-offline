.syntax unified
.thumb
.section .text
.align 2

.extern ccash_get
.extern safe_get
.extern exp_get
.extern chsp_get
.extern pocket_return
.extern get_pocket_return
.extern pet_get
.extern pet_count
.extern table_rows
.extern inventory_return
.extern inventory_reject_return
.extern log_print

.global pocket_guard
.thumb_func
pocket_guard:
    ldr     r0, [r5, #0x18]
    cmp     r0, #0
    beq     pocket_normal
    ldrb    r1, [r0]
    cmp     r1, #'G'
    beq     check_pocket
    cmp     r1, #'U'
    bne     pocket_normal
    ldrb    r1, [r0, #2]
    cmp     r1, #'d'
    beq     check_pocket
    cmp     r1, #'l'
    bne     pocket_normal

check_pocket:
    mov     r0, r5
    bl      clamp_pocket

pocket_normal:
    bl      chsp_get
    b.w     pocket_return

.global get_pocket_guard
.thumb_func
get_pocket_guard:
    mov     r0, r6
    bl      clamp_pocket
    bl      chsp_get
    b.w     get_pocket_return

clamp_pocket:
    push    {r4, r5, lr}
    mov     r5, r0
    bl      ccash_get
    mov     r4, r0

    adds    r0, #0x40
    bl      safe_get
    ldr     r1, [r5, #0x2c]
    cmp     r1, r0
    bge     1f
    str     r0, [r5, #0x2c]
    mov     r2, r0
    mov     r3, r1
    bl      log_pocket_clamp
1:
    mov     r0, r4
    adds    r0, #0x60
    bl      safe_get
    ldr     r1, [r5, #0x30]
    cmp     r1, r0
    bge     2f
    str     r0, [r5, #0x30]
    mov     r2, r0
    mov     r3, r1
    bl      log_pocket_clamp
2:
    bl      exp_get
    bl      safe_get
    ldr     r1, [r5, #0x34]
    cmp     r1, r0
    bge     3f
    str     r0, [r5, #0x34]
    mov     r2, r0
    mov     r3, r1
    bl      log_pocket_clamp
3:
    pop     {r4, r5, pc}

log_pocket_clamp:
    push    {r3, lr}
    mov     r3, r2
    movs    r0, #6
    adr     r1, guard_tag
    adr     r2, pocket_message
    blx     log_print
    pop     {r3, pc}

.align 2
guard_tag:
    .asciz "BirzzleGuard"
pocket_message:
    .asciz "POCKET CLAMP %d %d"
inventory_message:
    .asciz "INVENTORY REJECT %d %d"

.align 2
.global inventory_guard
.thumb_func
inventory_guard:
    bl      pet_get
    mov     r4, r0
    bl      pet_count
    cmp     r0, #0
    ble     inventory_normal

    push    {r0}
    mov     r0, r10
    bl      table_rows
    subs    r0, #1
    pop     {r1}
    cmp     r0, r1
    bge     inventory_normal

    mov     r2, r1
    mov     r3, r0
    push    {r3}
    mov     r3, r2
    movs    r0, #6
    adr     r1, guard_tag
    adr     r2, inventory_message
    blx     log_print
    add     sp, #4
    b       inventory_reject

inventory_normal:
    mov     r0, r4
    b.w     inventory_return

inventory_reject:
    b.w     inventory_reject_return
