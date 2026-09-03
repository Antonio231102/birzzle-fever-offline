.syntax unified
.thumb
.section .text
.align 2

.extern request_highwater
.extern string_copy_ctor
.extern file_worker_instance
.extern read_content
.extern node_deallocate
.extern operator_delete
.extern access_plt
.extern strcmp_plt
.extern usleep_plt
.extern fopen_plt
.extern fwrite_plt
.extern fflush_plt
.extern fclose_plt
.extern suite_nonempty_return
.extern suite_empty_return
.extern suite_compare_return
.extern all_nonempty_return
.extern all_empty_return
.extern all_valid_return
.extern set_nonempty_return
.extern set_empty_return
.extern set_compute_return
.extern mtime_accept_return
.extern mtime_reject_return
.extern write_return

.macro release_string object
    ldr     r0, [\object, #0x14]
    cmp     r0, \object
    beq     2f
    cmp     r0, #0
    beq     2f
    ldr     r1, [\object]
    subs    r1, r1, r0
    cmp     r1, #0x80
    bhi     1f
    blx     node_deallocate
    b       2f
1:
    bl      operator_delete
2:
.endm

.thumb_func
get_highwater:
    push    {r0}
    nop
.Lhighwater_pc:
    mov     r0, pc
    ldr     r12, .Lhighwater_delta
    add     r12, r0
    pop     {r0}
    bx      lr
.align 2
.Lhighwater_delta:
    .word   request_highwater - (.Lhighwater_pc + 4)

/* Return 1 when a failed index read belongs to a known mature pool. */
.thumb_func
should_retry_mature:
    push    {lr}
    bl      get_highwater
    ldr     r0, [r12]
    cmp     r0, #0
    bne     1f
    adr.w   r0, request_zero_path
    movs    r1, #0
    blx     access_plt
    cmp     r0, #0
    bne     2f
1:
    movs    r0, #1
    pop     {pc}
2:
    movs    r0, #0
    pop     {pc}

/* Preserve the original call-site registers while checking maturity. */
.macro maturity_decision empty_label
    push    {r0-r7}
    bl      should_retry_mature
    mov     r12, r0
    pop     {r0-r7}
    cmp     r12, #0
    beq     \empty_label
.endm

.macro retry_pause
    movw    r0, #50000
    blx     usleep_plt
.endm

.global suite_retry_guard
.thumb_func
suite_retry_guard:
    cmp     r3, r0
    bne     suite_nonempty
    maturity_decision suite_empty
    push    {r0-r7}
    ldr     r4, [sp, #0x78]
    ldr     r5, [sp, #0x7c]
    add.w   r6, sp, #0x18c
    mov     r0, r6
    mov     r1, r4
    bl      string_copy_ctor
suite_retry_read:
    retry_pause
    bl      file_worker_instance
    mov     r1, r0
    mov     r0, r5
    mov     r2, r6
    bl      read_content
    ldr     r0, [r5, #0x10]
    ldr     r3, [r5, #0x14]
    cmp     r3, r0
    beq     suite_retry_read
    release_string r6
    pop     {r0-r7}
suite_nonempty:
    b.w     suite_nonempty_return
suite_empty:
    b.w     suite_empty_return

.global suite_capture_guard
.thumb_func
suite_capture_guard:
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

.global all_retry_guard
.thumb_func
all_retry_guard:
    cmp     r2, r3
    bne     all_nonempty
    maturity_decision all_empty
    push    {r0-r7}
    ldr     r4, [sp, #0x74]
    ldr     r5, [sp, #0x78]
    add.w   r6, sp, #0x174
    mov     r0, r6
    mov     r1, r4
    bl      string_copy_ctor
all_retry_read:
    retry_pause
    bl      file_worker_instance
    mov     r1, r0
    mov     r0, r5
    mov     r2, r6
    bl      read_content
    ldr     r2, [r5, #0x14]
    ldr     r3, [r5, #0x10]
    cmp     r2, r3
    beq     all_retry_read
    release_string r6
    pop     {r0-r7}
all_nonempty:
    b.w     all_nonempty_return
all_empty:
    b.w     all_empty_return

.global all_capture_guard
.thumb_func
all_capture_guard:
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

.global set_retry_guard
.thumb_func
set_retry_guard:
    cmp     r2, r3
    bne     set_nonempty
    maturity_decision set_empty
    push    {r0-r7}
    mov     r4, r9
    mov     r5, r5
    add.w   r6, sp, #0x15c
    mov     r0, r6
    mov     r1, r4
    bl      string_copy_ctor
set_retry_read:
    retry_pause
    bl      file_worker_instance
    mov     r1, r0
    mov     r0, r5
    mov     r2, r6
    bl      read_content
    ldr     r2, [r5, #0x14]
    ldr     r3, [r5, #0x10]
    cmp     r2, r3
    beq     set_retry_read
    release_string r6
    pop     {r0-r7}
set_nonempty:
    b.w     set_nonempty_return
set_empty:
    b.w     set_empty_return

.global set_highwater_update
.thumb_func
set_highwater_update:
    bl      get_highwater
    adds    r0, r4, #2
    str     r0, [r12]
    adds    r3, r4, #1
    mvns    r2, r3
    b.w     set_compute_return

/* Accept a cryptographically valid response index despite mtime skew. */
.global mtime_guard
.thumb_func
mtime_guard:
    cmp     r0, #10
    ble     mtime_accept
    mov     r3, sp
    push    {r1-r3, lr}
    add.w   r0, r3, #0x100      /* stack path + 44-byte directory prefix */
    adr.w   r1, index_name
    blx     strcmp_plt
    cmp     r0, #0
    pop     {r1-r3, lr}
    beq     mtime_accept
    b.w     mtime_reject_return
mtime_accept:
    b.w     mtime_accept_return

/*
 * Preserve normal writes, but commit REQUESTPOOLINDEX through a sibling
 * temporary file and atomic rename. Linux ARM EABI syscalls are used for
 * fsync/rename because this 2014 binary has no PLT entries for them.
 */
.global write_dispatch
.thumb_func
write_dispatch:
    push    {r4-r7, lr}
    ldr     r0, [r11, #0x14]
    adr.w   r1, index_name
    blx     strcmp_plt
    cmp     r0, #0
    beq     write_index_atomic

write_normal:
    mov     r0, r10
    adr.w   r1, mode_write
    blx     fopen_plt
    mov     r4, r0
    cmp     r4, #0
    beq     write_done
    ldr     r0, [r6, #0x14]
    ldr     r2, [r6, #0x10]
    subs    r2, r2, r0
    movs    r1, #1
    mov     r3, r4
    blx     fwrite_plt
    mov     r0, r4
    blx     fclose_plt
    b       write_done

write_index_atomic:
    adr.w   r0, index_temp_path
    adr.w   r1, mode_write
    blx     fopen_plt
    mov     r4, r0
    cmp     r4, #0
    beq     index_cleanup

    ldr     r0, [r6, #0x14]
    ldr     r2, [r6, #0x10]
    subs    r5, r2, r0
    movs    r1, #1
    mov     r2, r5
    mov     r3, r4
    blx     fwrite_plt
    cmp     r0, r5
    bne     index_close_failure

    mov     r0, r4
    blx     fflush_plt
    cmp     r0, #0
    bne     index_close_failure

    adr.w   r0, index_temp_path
    movs    r1, #0
    movs    r7, #5              /* open */
    svc     #0
    cmp     r0, #0
    blt     index_close_failure
    mov     r5, r0
    movs    r7, #118            /* fsync */
    svc     #0
    mov     r6, r0
    mov     r0, r5
    movs    r7, #6              /* close */
    svc     #0
    cmp     r6, #0
    bne     index_close_failure

    mov     r0, r4
    blx     fclose_plt
    movs    r4, #0
    cmp     r0, #0
    bne     index_cleanup

    adr.w   r0, index_temp_path
    mov     r1, r10
    movs    r7, #38             /* rename */
    svc     #0
    cmp     r0, #0
    bne     index_cleanup

    adr.w   r0, files_directory
    movw    r1, #0x4000         /* O_DIRECTORY */
    movs    r7, #5              /* open */
    svc     #0
    cmp     r0, #0
    blt     write_done
    mov     r5, r0
    movs    r7, #118            /* fsync */
    svc     #0
    mov     r0, r5
    movs    r7, #6              /* close */
    svc     #0
    b       write_done

index_close_failure:
    mov     r0, r4
    blx     fclose_plt
    movs    r4, #0
index_cleanup:
    cmp     r4, #0
    beq     1f
    mov     r0, r4
    blx     fclose_plt
1:
    adr.w   r0, index_temp_path
    movs    r7, #10             /* unlink */
    svc     #0

write_done:
    pop     {r4-r7, lr}
    b.w     write_return

.align 2
mode_write:
    .asciz  "w"
index_name:
    .asciz  "5f7d50ff681a65b10550a631e11a2ded"
files_directory:
    .asciz  "/data/data/com.halfbrick.birzzlefever/files"
index_temp_path:
    .asciz  "/data/data/com.halfbrick.birzzlefever/files/5f7d50ff681a65b10550a631e11a2ded.tmp"
request_zero_path:
    .asciz  "/data/data/com.halfbrick.birzzlefever/files/3ec79b0f1529e3fda4242b59a97d2123"
