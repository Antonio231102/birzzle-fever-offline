.p2align 2
.globl _bf_request_bridge
.thumb_func
_bf_request_bridge:
    // Called inside _state_request after its original ten-register save.
    // Original fifth/sixth arguments: API NSString at [sp+40], params at [sp+44].
    push.w {r4-r8, lr}
    bl _trace_menu
    ldr r3, [sp, #68]
    movw r4, #@BF_SELECTOR_LO@
    movt r4, #@BF_SELECTOR_HI@
.globl _pc_bf_selector
_pc_bf_selector:
    add r4, pc
    ldr r4, [r4]
    sub sp, #8
    str r4, [sp]
    movw r0, #@BF_REQUEST_CTX_LO@
    movt r0, #@BF_REQUEST_CTX_HI@
.globl _pc_bf_request_ctx
_pc_bf_request_ctx:
    add r0, pc
    mov r1, r6
    mov r2, r8
    movw r4, #@BF_REQUEST_FN_LO@
    movt r4, #@BF_REQUEST_FN_HI@
.globl _pc_bf_request_fn
_pc_bf_request_fn:
    add r4, pc
    orr.w r4, r4, #1
    blx r4
    add sp, #8
    pop.w {r4-r8, pc}

.p2align 2
.globl _bf_failure_bridge
.thumb_func
_bf_failure_bridge:
    // The outer hook saved r0-r3,r6,r8,lr (28 bytes). Keep the C call
    // eight-byte aligned, then edit only saved original r1 and r3.
    push {r4-r7, lr}
    movw r0, #@BF_FAILURE_CTX_LO@
    movt r0, #@BF_FAILURE_CTX_HI@
.globl _pc_bf_failure_ctx
_pc_bf_failure_ctx:
    add r0, pc
    mov r1, r12
    movw r4, #@BF_FAILURE_FN_LO@
    movt r4, #@BF_FAILURE_FN_HI@
.globl _pc_bf_failure_fn
_pc_bf_failure_fn:
    add r4, pc
    orr.w r4, r4, #1
    blx r4
    ldr r12, [r6, #8]
    cbz r0, .Lbf_no_reply
    str r0, [sp, #32]
    str r12, [sp, #24]
    movs r12, #0             // bypass only legacy static response dispatch
    pop {r4-r7, pc}
.Lbf_no_reply:
    pop {r4-r7, pc}

.p2align 2
.globl _bf_token_bridge
.thumb_func
_bf_token_bridge:
    // Only pointer identity against one of our queued frames can select the
    // authenticated archive token. All other responses retain original strcmp.
    push.w {r4-r8, lr}
    movw r0, #@BF_TOKEN_CTX_LO@
    movt r0, #@BF_TOKEN_CTX_HI@
.globl _pc_bf_token_ctx
_pc_bf_token_ctx:
    add r0, pc
    mov r1, r8
    movw r4, #@BF_TOKEN_FN_LO@
    movt r4, #@BF_TOKEN_FN_HI@
.globl _pc_bf_token_fn
_pc_bf_token_fn:
    add r4, pc
    orr.w r4, r4, #1
    blx r4
    pop.w {r4-r8, pc}
