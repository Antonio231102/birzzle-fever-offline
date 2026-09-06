.syntax unified
.thumb
.section .text
.align 2

.extern compat_open_temp
.extern compat_rename_index
.extern compat_open_directory
.extern compat_unlink_temp
.extern android_log_print

/*
 * Operation IDs emitted as: "fs op=<id> ret=<raw syscall result>"
 *   1 open temporary index
 *   2 fsync temporary index
 *   3 rename temporary index over authoritative index
 *   4 open authoritative index parent directory
 *   5 fsync parent directory
 *   6 unlink abandoned temporary index
 * Direct ARM syscalls return -errno on failure, so no libc errno lookup is
 * required and the response-pool transaction is not otherwise modified.
 */

.macro diagnostic_wrapper name, target, operation
.global \name
.thumb_func
\name:
    push    {r4-r6, lr}
    bl      \target
    movs    r1, #\operation
    b       log_return
.endm

diagnostic_wrapper diagnostic_open_temp, compat_open_temp, 1

.global diagnostic_fsync_temp
.thumb_func
diagnostic_fsync_temp:
    push    {r4-r6, lr}
    movs    r7, #118
    svc     #0
    movs    r1, #2
    b       log_return

diagnostic_wrapper diagnostic_rename_index, compat_rename_index, 3
diagnostic_wrapper diagnostic_open_directory, compat_open_directory, 4

.global diagnostic_fsync_directory
.thumb_func
diagnostic_fsync_directory:
    push    {r4-r6, lr}
    movs    r7, #118
    svc     #0
    movs    r1, #5
    b       log_return

diagnostic_wrapper diagnostic_unlink_temp, compat_unlink_temp, 6

.thumb_func
log_return:
    mov     r4, r0
    sub     sp, #8
    str     r4, [sp]
    mov     r3, r1
    adr     r2, log_format
    adr     r1, log_tag
    movs    r0, #4
    blx     android_log_print
    add     sp, #8
    mov     r0, r4
    pop     {r4-r6, pc}

.align 2
log_tag:
    .asciz  "BirzzleV29"
log_format:
    .asciz  "fs op=%d ret=%d"
