.syntax unified
.thumb
.section .text
.extern pocket_guard
.global pocket_fault_injector
.thumb_func
pocket_fault_injector:
    movs    r0, #0
    str     r0, [r5, #0x2c]
    str     r0, [r5, #0x30]
    str     r0, [r5, #0x34]
    b.w     pocket_guard
