.syntax unified
.thumb
.section .text
.align 2

.extern strcpy_plt
.extern strlen_plt
.extern strrchr_plt
.extern strcmp_plt
.extern mtime_accept_return
.extern mtime_reject_return

/* Linux ARM EABI values. These calls predate Android 4.4's kernel. */
.equ AT_FDCWD_ABS, 100
.equ __NR_openat, 322
.equ __NR_unlinkat, 328
.equ __NR_renameat, 329
.equ O_DIRECTORY, 0x4000

.macro load_at_fdcwd reg
    movs    \reg, #AT_FDCWD_ABS
    rsbs    \reg, \reg, #0
.endm

/* Build "<authoritative index path>.tmp" from the path already in r10. */
.thumb_func
make_temp_path:
    push    {r4, lr}
    mov     r4, r0
    mov     r1, r10
    blx     strcpy_plt
    mov     r0, r4
    blx     strlen_plt
    add     r2, r4, r0
    ldr     r1, tmp_suffix
    str     r1, [r2]
    movs    r1, #0
    strb    r1, [r2, #4]
    mov     r0, r4
    pop     {r4, pc}

/* Open the sibling temporary index for the existing fsync sequence. */
.global compat_open_temp
.thumb_func
compat_open_temp:
    push    {r4-r6, lr}
    sub     sp, #96
    mov     r0, sp
    bl      make_temp_path
    mov     r1, r0
    load_at_fdcwd r0
    movs    r2, #0
    movw    r7, #__NR_openat
    svc     #0
    mov     r4, r0
    add     sp, #96
    mov     r0, r4
    pop     {r4-r6, pc}

/* Atomically replace the actual authoritative path, preserving its mount. */
.global compat_rename_index
.thumb_func
compat_rename_index:
    push    {r4-r6, lr}
    sub     sp, #96
    mov     r0, sp
    bl      make_temp_path
    mov     r1, r0
    mov     r3, r10
    load_at_fdcwd r0
    mov     r2, r0
    movw    r7, #__NR_renameat
    svc     #0
    mov     r4, r0
    add     sp, #96
    mov     r0, r4
    pop     {r4-r6, pc}

/* Open the authoritative index's actual parent directory for fsync. */
.global compat_open_directory
.thumb_func
compat_open_directory:
    push    {r4-r6, lr}
    sub     sp, #96
    mov     r0, sp
    mov     r1, r10
    blx     strcpy_plt
    mov     r4, r0
    movs    r1, #47
    blx     strrchr_plt
    movs    r1, #0
    strb    r1, [r0]
    mov     r1, r4
    load_at_fdcwd r0
    movw    r2, #O_DIRECTORY
    movw    r7, #__NR_openat
    svc     #0
    mov     r4, r0
    add     sp, #96
    mov     r0, r4
    pop     {r4-r6, pc}

/* Remove an abandoned sibling temporary index. */
.global compat_unlink_temp
.thumb_func
compat_unlink_temp:
    push    {r4-r6, lr}
    sub     sp, #96
    mov     r0, sp
    bl      make_temp_path
    mov     r1, r0
    load_at_fdcwd r0
    movs    r2, #0
    movw    r7, #__NR_unlinkat
    svc     #0
    mov     r4, r0
    add     sp, #96
    mov     r0, r4
    pop     {r4-r6, pc}

/* Accept only the authenticated response index, independent of data-dir length. */
.global compat_mtime_guard
.thumb_func
compat_mtime_guard:
    cmp     r0, #10
    ble     mtime_accept
    mov     r3, sp
    push    {r1-r3, lr}
    add.w   r0, r3, #0xd4
    movs    r1, #47
    blx     strrchr_plt
    cmp     r0, #0
    beq     mtime_reject
    adds    r0, #1
    adr     r1, index_name
    blx     strcmp_plt
    cmp     r0, #0
    pop     {r1-r3, lr}
    beq     mtime_accept
    b.w     mtime_reject_return
mtime_reject:
    pop     {r1-r3, lr}
    b.w     mtime_reject_return
mtime_accept:
    b.w     mtime_accept_return

.align 2
tmp_suffix:
    .word   0x706d742e
index_name:
    .asciz  "5f7d50ff681a65b10550a631e11a2ded"
