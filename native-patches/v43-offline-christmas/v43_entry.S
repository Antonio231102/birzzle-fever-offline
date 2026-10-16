.syntax unified
.thumb
.section .text
.p2align 2
.global original_show_dialog
.type original_show_dialog, %function
.thumb_func
original_show_dialog:
    /* Relocate exactly the two overwritten instructions, neither PC-relative. */
    push {r4, r5, r6, r7, lr}
    mov r7, r11
    b.w show_dialog_continue
.size original_show_dialog, .-original_show_dialog

.p2align 2
.global original_show_banner
.type original_show_banner, %function
.thumb_func
original_show_banner:
    push {r4, r5, r6, r7, lr}
    mov r7, r11
    b.w show_banner_continue
.size original_show_banner, .-original_show_banner

.p2align 2
.global original_load_background
.type original_load_background, %function
.thumb_func
original_load_background:
    push {r4, r5, r6, r7, lr}
    mov r7, r11
    b.w load_background_continue
.size original_load_background, .-original_load_background

.p2align 2
.global original_receive_present
.type original_receive_present, %function
.thumb_func
original_receive_present:
    push {r4, r5, r6, r7, lr}
    mov r7, r11
    b.w receive_present_continue
.size original_receive_present, .-original_receive_present

.p2align 2
.global eve_clock
.type eve_clock, %function
.thumb_func
eve_clock:
    /* ARM EABI clock_gettime(CLOCK_BOOTTIME, timespec32*).
     * Unlike legacy time/open syscalls, 263 is in Android's ARM app allowlist. */
    push {r7, lr}
    mov r1, r0
    movs r0, #7
    movw r7, #263
    svc #0
    pop {r7, pc}
.size eve_clock, .-eve_clock
.section .note.GNU-stack,"",%progbits
