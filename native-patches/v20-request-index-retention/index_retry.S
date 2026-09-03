.syntax unified
.thumb
.section .text
.align 2

.extern get_highwater
.extern file_worker_instance
.extern string_copy_ctor
.extern read_content
.extern node_deallocate
.extern operator_delete
.extern suite_nonempty_return
.extern suite_empty_return
.extern all_nonempty_return
.extern all_empty_return
.extern set_nonempty_return
.extern set_empty_return

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

.global suite_retry_guard
.thumb_func
suite_retry_guard:
    cmp     r3, r0
    bne     suite_nonempty
    bl      get_highwater
    ldr     r2, [r12]
    cmp     r2, #0
    beq     suite_empty
    push    {r0-r7}
    ldr     r4, [sp, #0x78]
    ldr     r5, [sp, #0x7c]
    add.w   r6, sp, #0x18c
    mov     r0, r6
    mov     r1, r4
    bl      string_copy_ctor
suite_retry_read:
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

.global all_retry_guard
.thumb_func
all_retry_guard:
    cmp     r2, r3
    bne     all_nonempty
    bl      get_highwater
    ldr     r0, [r12]
    cmp     r0, #0
    beq     all_empty
    push    {r0-r7}
    ldr     r4, [sp, #0x74]
    ldr     r5, [sp, #0x78]
    add.w   r6, sp, #0x174
    mov     r0, r6
    mov     r1, r4
    bl      string_copy_ctor
all_retry_read:
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

.global set_retry_guard
.thumb_func
set_retry_guard:
    cmp     r2, r3
    bne     set_nonempty
    bl      get_highwater
    ldr     r0, [r12]
    cmp     r0, #0
    beq     set_empty
    push    {r0-r7}
    mov     r4, r9
    mov     r5, r5
    add.w   r6, sp, #0x15c
    mov     r0, r6
    mov     r1, r4
    bl      string_copy_ctor
set_retry_read:
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
