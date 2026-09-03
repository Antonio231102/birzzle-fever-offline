.syntax unified
.thumb
.section .text
.extern ccash_get
.extern safe_get
.extern get_pocket_guard
.global get_pocket_fault_injector
.thumb_func
get_pocket_fault_injector:
    bl      ccash_get
    adds    r0, #0x40
    bl      safe_get
    cmp     r0, #0
    beq     1f
    movs    r0, #0
    str     r0, [r6, #0x2c]
    str     r0, [r6, #0x30]
    str     r0, [r6, #0x34]
1:
    b.w     get_pocket_guard
