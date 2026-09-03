.syntax unified
.thumb
.section .text
.align 2

.extern get_highwater
.extern set_nonempty_return
.extern set_empty_return
.extern set_compute_guard

.global forced_empty_after_capture
.thumb_func
forced_empty_after_capture:
    bl      get_highwater
    ldr     r4, [r12]
    cmp     r4, #0
    beq     actual_index_state
    subs    r4, #1
    movs    r2, #0
    subs    r2, #1
    mov     r8, r2
    b.w     set_compute_guard
actual_index_state:
    cmp     r2, r3
    bne     set_nonempty
    b.w     set_empty_return
set_nonempty:
    b.w     set_nonempty_return
