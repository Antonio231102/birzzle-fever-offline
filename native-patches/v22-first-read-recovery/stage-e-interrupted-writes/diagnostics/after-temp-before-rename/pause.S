.syntax unified
.thumb
.section .text
.global pause_stub
.thumb_func
pause_stub:
    b       pause_stub
