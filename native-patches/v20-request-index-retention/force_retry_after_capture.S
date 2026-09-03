.syntax unified
.thumb
.section .text
.align 2

.extern get_highwater
.extern set_retry_guard

.global force_retry_after_capture
.thumb_func
force_retry_after_capture:
    bl      get_highwater
    ldr     r0, [r12]
    cmp     r0, #0
    beq     actual_index_state
    mov     r2, r3
actual_index_state:
    b.w     set_retry_guard
