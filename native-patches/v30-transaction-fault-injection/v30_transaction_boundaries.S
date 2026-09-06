.syntax unified
.thumb
.section .text
.align 2

.extern fopen_plt
.extern fwrite_plt
.extern fclose_plt
.extern fflush_plt
.extern compat_open_temp
.extern compat_rename_index
.extern compat_open_directory
.extern compat_unlink_temp
.extern android_log_print

/*
 * Operation IDs emitted after each completed boundary:
 *   1 response-record fopen       7 temporary-index fd open
 *   2 response-record fwrite      8 temporary-index fsync
 *   3 response-record fclose      9 authoritative-index rename
 *   4 temporary-index fopen      10 parent-directory fd open
 *   5 temporary-index fwrite     11 parent-directory fsync
 *   6 temporary-index fflush     12 abandoned-temp unlink
 *
 * Every boundary pauses for 750 ms after logging. The host controller can
 * deterministically force-stop the process inside that window and snapshot
 * private state through run-as. Return values and application behavior are
 * unchanged unless the host deliberately terminates the process.
 */

.macro libc_wrapper name, target, operation
.global \name
.thumb_func
\name:
    push    {r4-r7, lr}
    sub     sp, #4
    blx     \target
    mov     r4, r0
    movs    r1, #\operation
    b       log_delay_return
.endm

.macro compat_wrapper name, target, operation
.global \name
.thumb_func
\name:
    push    {r4-r7, lr}
    sub     sp, #4
    bl      \target
    mov     r4, r0
    movs    r1, #\operation
    b       log_delay_return
.endm

libc_wrapper diagnostic_record_fopen, fopen_plt, 1
libc_wrapper diagnostic_record_fwrite, fwrite_plt, 2
libc_wrapper diagnostic_record_fclose, fclose_plt, 3
libc_wrapper diagnostic_index_fopen, fopen_plt, 4
libc_wrapper diagnostic_index_fwrite, fwrite_plt, 5
libc_wrapper diagnostic_index_fflush, fflush_plt, 6
compat_wrapper diagnostic_open_temp, compat_open_temp, 7

.global diagnostic_fsync_temp
.thumb_func
diagnostic_fsync_temp:
    push    {r4-r7, lr}
    sub     sp, #4
    movs    r7, #118
    svc     #0
    mov     r4, r0
    movs    r1, #8
    b       log_delay_return

compat_wrapper diagnostic_rename_index, compat_rename_index, 9
compat_wrapper diagnostic_open_directory, compat_open_directory, 10

.global diagnostic_fsync_directory
.thumb_func
diagnostic_fsync_directory:
    push    {r4-r7, lr}
    sub     sp, #4
    movs    r7, #118
    svc     #0
    mov     r4, r0
    movs    r1, #11
    b       log_delay_return

compat_wrapper diagnostic_unlink_temp, compat_unlink_temp, 12

.thumb_func
log_delay_return:
    sub     sp, #8
    str     r4, [sp]
    mov     r3, r1
    adr     r2, log_format
    adr     r1, log_tag
    movs    r0, #4
    blx     android_log_print
    add     sp, #8

    sub     sp, #8
    movs    r0, #0
    str     r0, [sp]
    movw    r0, #0x1780
    movt    r0, #0x2cb4
    str     r0, [sp, #4]
    mov     r0, sp
    movs    r1, #0
    movs    r7, #162
    svc     #0
    add     sp, #8

    mov     r0, r4
    add     sp, #4
    pop     {r4-r7, pc}

.align 2
log_tag:
    .asciz  "B30"
log_format:
    .asciz  "o=%d r=%d"
