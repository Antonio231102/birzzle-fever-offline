.syntax unified
.thumb
.text
.global inventory_select_entry
.type inventory_select_entry, %function
.thumb_func
inventory_select_entry:
    ldr r0, [sp, #8]
    ldr r1, [sp, #12]
    bl inventory_select
    b.w inventory_use_continue

.global inventory_request_entry
.type inventory_request_entry, %function
.thumb_func
inventory_request_entry:
    /* Keep the request object, not its narrowed numeric transaction ID. */
    ldr r0, [sp, #8]
    str r0, [sp, #20]
    b.w inventory_count_continue

.global inventory_compare_entry
.type inventory_compare_entry, %function
.thumb_func
inventory_compare_entry:
    mov r0, r6
    ldr r1, [sp, #20]
    bl inventory_same_tid
    cmp r0, #0
    beq.w inventory_no_match
    b.w inventory_match
