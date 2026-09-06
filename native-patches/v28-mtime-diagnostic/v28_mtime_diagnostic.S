.syntax unified
.thumb
.section .text
.align 2

.extern strrchr_plt
.extern strcmp_plt
.extern android_log_print
.extern mtime_accept_return
.extern mtime_reject_return

.global diagnostic_mtime_guard
.thumb_func
diagnostic_mtime_guard:
    cmp     r0, #10
    ble     mtime_accept
    mov     r3, sp
    push    {r1-r7, lr}
    mov     r4, r0
    add.w   r0, r3, #0xd4
    movs    r1, #47
    blx     strrchr_plt
    cmp     r0, #0
    beq     no_slash
    adds    r6, r0, #1
    mov     r0, r6
    adr     r1, index_name
    blx     strcmp_plt
    mov     r7, r0
    b       log_result
no_slash:
    adr     r6, missing_slash
    movs    r7, #127
log_result:
    sub     sp, #8
    str     r6, [sp]
    str     r7, [sp, #4]
    mov     r3, r4
    adr     r2, log_format
    adr     r1, log_tag
    movs    r0, #4
    blx     android_log_print
    add     sp, #8
    cmp     r7, #0
    pop     {r1-r7, lr}
    beq     mtime_accept
    b.w     mtime_reject_return
mtime_accept:
    b.w     mtime_accept_return

.align 2
log_tag:
    .asciz  "BirzzleV28"
log_format:
    .asciz  "mtime diff=%d base=%s cmp=%d"
missing_slash:
    .asciz  "<no-slash>"
index_name:
    .asciz  "5f7d50ff681a65b10550a631e11a2ded"
