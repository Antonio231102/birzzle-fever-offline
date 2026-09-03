.syntax unified
.thumb
.section .text
.extern safe_set
.extern coin_return
.extern gem_return

.global test_coin_grant
.thumb_func
test_coin_grant:
    movw    r1, #0x1b30
    movt    r1, #0x000f
    bl      safe_set
    b.w     coin_return

.global test_gem_grant
.thumb_func
test_gem_grant:
    movw    r1, #0x863c
    movt    r1, #0x0001
    bl      safe_set
    b.w     gem_return
