.syntax unified
.thumb
.section .text
.align 2

.extern android_log_print
.extern profile_read_return

.global profile_read_diagnostic
.thumb_func
profile_read_diagnostic:
    push    {r0-r7, lr}
    sub     sp, #20
    ldr     r4, [sp, #28]
    cmp     r4, #0
    beq     no_key
    ldr     r5, [r4]
    ldr     r6, [r4, #4]
    ldr     r7, [r4, #8]
    ldr     r4, [r4, #12]
    b       have_key
no_key:
    movs    r5, #0
    movs    r6, #0
    movs    r7, #0
    movs    r4, #0
have_key:
    str     r5, [sp]
    str     r6, [sp, #4]
    str     r7, [sp, #8]
    str     r4, [sp, #12]
    ldr     r3, [sp, #32]
    movs    r0, #6
    adr     r1, diagnostic_tag
    adr     r2, diagnostic_message
    blx     android_log_print
    add     sp, #20
    pop     {r0-r7, lr}
    push    {r4, r5, lr}
    mov     r4, r1
    b.w     profile_read_return

.align 2
diagnostic_tag:
    .asciz "BirzzleProfile"
diagnostic_message:
    .asciz "READ len=%d key=%08x%08x%08x%08x"
