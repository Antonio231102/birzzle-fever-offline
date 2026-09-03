.syntax unified
.thumb
.section .text
.align 2

.extern request_highwater
.extern suite_nonempty_return
.extern suite_empty_return
.extern suite_compare_return
.extern all_nonempty_return
.extern all_empty_return
.extern all_valid_return
.extern set_nonempty_return
.extern set_empty_return
.extern set_compute_return

.thumb_func
get_highwater:
    push    {r0}
    nop
.Lpc:
    mov     r0, pc
    ldr     r12, .Ldelta
    add     r12, r0
    pop     {r0}
    bx      lr
.align 2
.Ldelta:
    .word   request_highwater - (.Lpc + 4)

.global suite_empty_guard
.thumb_func
suite_empty_guard:
    cmp     r3, r0
    bne     suite_nonempty
    bl      get_highwater
    ldr     r2, [r12]
    cmp     r2, #0
    beq     suite_empty
    movs    r3, #0
    subs    r3, #1
    str     r3, [sp, #0x14]
    subs    r0, r2, #1
    str     r0, [sp, #0x34]
    b       suite_valid_guard
suite_nonempty:
    b.w     suite_nonempty_return
suite_empty:
    b.w     suite_empty_return

.global suite_valid_guard
.thumb_func
suite_valid_guard:
    ldr     r3, [sp, #0x14]
    ldr     r0, [sp, #0x34]
    cmp     r0, #0
    blt     1f
    bl      get_highwater
    adds    r2, r0, #1
    str     r2, [r12]
1:
    cmp     r3, r0
    b.w     suite_compare_return

.global all_empty_guard
.thumb_func
all_empty_guard:
    cmp     r2, r3
    bne     all_nonempty
    bl      get_highwater
    ldr     r0, [r12]
    cmp     r0, #0
    beq     all_empty
    movs    r3, #0
    subs    r3, #1
    str     r3, [sp, #0x0c]
    subs    r0, #1
    str     r0, [sp, #0x28]
    b       all_valid_guard
all_nonempty:
    b.w     all_nonempty_return
all_empty:
    b.w     all_empty_return

.global all_valid_guard
.thumb_func
all_valid_guard:
    ldr     r0, [sp, #0x28]
    cmp     r0, #0
    blt     1f
    bl      get_highwater
    adds    r2, r0, #1
    str     r2, [r12]
1:
    ldr     r1, [sp, #0x20]
    movs    r3, #0
    b.w     all_valid_return

.global set_empty_guard
.thumb_func
set_empty_guard:
    cmp     r2, r3
    bne     set_nonempty
    bl      get_highwater
    ldr     r4, [r12]
    cmp     r4, #0
    beq     set_empty
    subs    r4, #1
    movs    r2, #0
    subs    r2, #1
    mov     r8, r2
    b       set_compute_guard
set_nonempty:
    b.w     set_nonempty_return
set_empty:
    b.w     set_empty_return

.global set_compute_guard
.thumb_func
set_compute_guard:
    bl      get_highwater
    adds    r0, r4, #2
    str     r0, [r12]
    adds    r3, r4, #1
    mvns    r2, r3
    b.w     set_compute_return
