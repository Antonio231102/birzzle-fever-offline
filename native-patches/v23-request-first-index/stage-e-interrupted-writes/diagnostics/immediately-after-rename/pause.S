.syntax unified
.thumb
.section .text
.global pause_stub
.thumb_func
pause_stub:
    movs    r7, #29
    svc     #0
    b       pause_stub
