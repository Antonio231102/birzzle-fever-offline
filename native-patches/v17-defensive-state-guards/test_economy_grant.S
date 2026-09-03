.syntax unified
.thumb
.section .text
.extern safe_set
.extern coin_return
.extern gem_return

.global test_coin_grant
.thumb_func
test_coin_grant:
    movw    r1, #0x86a0
    movt    r1, #1
    bl      safe_set
    b.w     coin_return

.global test_gem_grant
.thumb_func
test_gem_grant:
    movw    r1, #10000
    bl      safe_set
    b.w     gem_return
