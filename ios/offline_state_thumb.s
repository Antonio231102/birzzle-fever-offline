// iOS 6 ARMv7: original app account is never overwritten. Addresses are
// image-relative PC deltas filled and checked by patch_offline_state.py.
.syntax unified
.thumb
.text
.p2align 2
.globl _state_request
.thumb_func
_state_request:
    push.w {r0-r8, lr}
    mov r6, r2
    // Clear the exact-command slot on an ID reused for another API.
    cmp r6, #3
    blo .Lrequest_api
    cmp r6, #9
    bhi .Lrequest_api
    movw r3, #@REQ_CLEAR_LO@
    movt r3, #@REQ_CLEAR_HI@
.globl _pc_req_clear
_pc_req_clear:
    add r3, pc
    subs r2, r6, #1
    lsls r2, r2, #2
    movs r1, #0
    str r1, [r3, r2]
.Lrequest_api:
    ldr r5, [sp, #40]          // API NSString in original fifth argument
    cbz r5, .Lrequest_exit
    mov r0, r5
    movw r1, #@REQ_UTF8_LO@
    movt r1, #@REQ_UTF8_HI@
.globl _pc_req_utf8
_pc_req_utf8:
    add r1, pc
    ldr r1, [r1]
    movw r4, #@REQ_MSG_LO@
    movt r4, #@REQ_MSG_HI@
.globl _pc_req_msg
_pc_req_msg:
    add r4, pc
    blx r4
    cbz r0, .Lrequest_exit
    mov r8, r0
    bl _trace_menu
    @BACKEND_REQUEST_HOOK@
    mov r0, r8
    adr.w r1, _api_init
    bl _matches
    cbz r0, .Ltry_login
    movs r2, #0
    b .Lrecord_request
.Ltry_login:
    mov r0, r8
    adr.w r1, _api_login
    bl _matches
    cbz r0, .Ltry_inventory
    movs r2, #4
    b .Lrecord_request
.Ltry_inventory:
    mov r0, r8
    adr.w r1, _api_inventory
    bl _matches
    cbz r0, .Ltry_custom
    movs r2, #8
    b .Lrecord_request
.Ltry_custom:
    mov r0, r8
    adr.w r1, _api_custom_get
    bl _matches
    cbz r0, .Ltry_pocket
    movs r2, #12
    b .Lrecord_request
.Ltry_pocket:
    bl _request_pocket
    bl _request_menu
    b .Lrequest_exit
.Lrecord_request:
    movw r3, #@REQ_MAP_LO@
    movt r3, #@REQ_MAP_HI@
.globl _pc_req_map
_pc_req_map:
    add r3, pc
    str r6, [r3, r2]
.Lrequest_exit:
    pop.w {r0-r8, lr}
    push {r4-r7, lr}           // original method prologue
    add r7, sp, #0xc
    movw r12, #@REQ_RETURN_LO@
    movt r12, #@REQ_RETURN_HI@
.globl _pc_req_return
_pc_req_return:
    add r12, pc
    bx r12
_matches:
    ldrb r2, [r0], #1
    ldrb r3, [r1], #1
    cmp r2, r3
    bne .Ldifferent
    cmp r2, #0
    bne _matches
    movs r0, #1
    bx lr
.Ldifferent:
    movs r0, #0
    bx lr
.p2align 2
_api_init:
    .asciz "server.init.2"
_api_login:
    .asciz "pocket.login"
_api_inventory:
    .asciz "inventory.list"
_api_custom_get:
    .asciz "custom.get"
.p2align 2
.space 0x100 - (. - _state_request), 0

.globl _state_failure
.thumb_func
_state_failure:
    // Original parser BL; r0=queue, r1=-1, r2=handle, r3=error C text.
    push.w {r0-r3, r6, r8, lr}
    ldr r12, [r6, #8]
    @BACKEND_FAILURE_HOOK@
    cmp r12, #1
    beq .Lselect_init
    cmp r12, #2
    beq .Lselect_login
    cmp r12, #3
    beq .Lselect_inventory
    cmp r12, #4
    beq .Lselect_custom
    cmp r12, #5
    beq .Lselect_pocket
    cmp r12, #6
    beq .Lselect_global
    bl _failure_menu
    b .Loriginal_failure
.Lselect_pocket:
    bl _failure_pocket
    b .Loriginal_failure
.Lselect_global:
    bl _failure_global
    b .Loriginal_failure
.Lselect_init:
    movs r8, #0
    b .Lcheck_map
.Lselect_login:
    movs r8, #4
    b .Lcheck_map
.Lselect_inventory:
    movs r8, #8
    b .Lcheck_map
.Lselect_custom:
    movs r8, #12
.Lcheck_map:
    movw r3, #@FAIL_MAP_LO@
    movt r3, #@FAIL_MAP_HI@
.globl _pc_fail_map
_pc_fail_map:
    add r3, pc
    ldr r3, [r3, r8]
    cmp r12, r3
    bne .Loriginal_failure
    cmp r12, #1
    beq .Luse_init
    cmp r12, #2
    beq .Luse_login
    cmp r12, #3
    beq .Luse_inventory
    movw r3, #@CUSTOM_WIRE_LO@
    movt r3, #@CUSTOM_WIRE_HI@
.globl _pc_custom_wire
_pc_custom_wire:
    add r3, pc
    b .Luse_reply
.Luse_inventory:
    movw r3, #@INVENTORY_WIRE_LO@
    movt r3, #@INVENTORY_WIRE_HI@
.globl _pc_inventory_wire
_pc_inventory_wire:
    add r3, pc
    b .Luse_reply
.Luse_init:
    movw r3, #@INIT_WIRE_LO@
    movt r3, #@INIT_WIRE_HI@
.globl _pc_init_wire
_pc_init_wire:
    add r3, pc
    b .Luse_reply
.Luse_login:
    movw r3, #@LOGIN_WIRE_LO@
    movt r3, #@LOGIN_WIRE_HI@
.globl _pc_login_wire
_pc_login_wire:
    add r3, pc
.Luse_reply:
    str r3, [sp, #12]         // replace saved original r3 only
    str r12, [sp, #4]         // replace saved r1=-1 only
.Loriginal_failure:
    pop.w {r0-r3, r6, r8, lr}
    b.w _state_failure_tail
.p2align 2
.space 0x200 - (. - _state_request), 0

.globl _state_launch_options
.thumb_func
_state_launch_options:
    push.w {r0-r4, lr}
    bl _seed_saves
    cmp r0, #0
    beq .Llaunch_options_failed
    pop.w {r0-r4, lr}
    push {r4-r7, lr}
    add r7, sp, #0xc
    movw r12, #@OPTIONS_RETURN_LO@
    movt r12, #@OPTIONS_RETURN_HI@
.globl _pc_options_return
_pc_options_return:
    add r12, pc
    bx r12
.Llaunch_options_failed:
    pop.w {r0-r4, lr}
    movs r0, #0                // abort launch if historical save import failed
    bx lr
.p2align 2
.space 0x240 - (. - _state_request), 0
.globl _state_launch_legacy
.thumb_func
_state_launch_legacy:
    push.w {r0-r4, lr}
    bl _seed_saves
    cmp r0, #0
    beq .Llaunch_legacy_failed
    pop.w {r0-r4, lr}
    push {r4-r7, lr}
    add r7, sp, #0xc
    movw r12, #@LEGACY_RETURN_LO@
    movt r12, #@LEGACY_RETURN_HI@
.globl _pc_legacy_return
_pc_legacy_return:
    add r12, pc
    bx r12
.Llaunch_legacy_failed:
    pop.w {r0-r4, lr}
    movs r0, #0
    bx lr
.p2align 2

// Import only missing records into the new, isolated app Keychain account.
// A failed store aborts app launch; no original-account service is changed.
_seed_saves:
    push.w {r4-r8, r10, r11, lr} // iOS ABI treats r9 as caller-clobbered
    sub sp, #16
    movw r4, #@SEED_HELPER_LO@
    movt r4, #@SEED_HELPER_HI@
.globl _pc_seed_helper
_pc_seed_helper:
    add r4, pc
    ldr r4, [r4]
    movw r5, #@SEED_ACCOUNT_LO@
    movt r5, #@SEED_ACCOUNT_HI@
.globl _pc_seed_account
_pc_seed_account:
    add r5, pc
    movw r6, #@SEED_STRING_CLASS_LO@
    movt r6, #@SEED_STRING_CLASS_HI@
.globl _pc_seed_string_class
_pc_seed_string_class:
    add r6, pc
    ldr r6, [r6]
    movw r7, #@SEED_MSG_LO@
    movt r7, #@SEED_MSG_HI@
.globl _pc_seed_msg
_pc_seed_msg:
    add r7, pc
    adr.w r11, _save_table
    mov r8, r11
.Lsave_loop:
    ldr r2, [r8], #4
    cbz r2, .Lseed_ok
    add r2, r11
    ldr r10, [r8], #4
    add r10, r11
    mov r0, r6
    movw r1, #@SEED_STRING_SEL_LO@
    movt r1, #@SEED_STRING_SEL_HI@
.globl _pc_seed_string_sel
_pc_seed_string_sel:
    add r1, pc
    ldr r1, [r1]
    blx r7
    str r0, [sp, #12]          // service NSString (autoreleased, same pool)
    mov r0, r4
    movw r1, #@SEED_GET_SEL_LO@
    movt r1, #@SEED_GET_SEL_HI@
.globl _pc_seed_get_sel
_pc_seed_get_sel:
    add r1, pc
    ldr r1, [r1]
    mov r2, r5
    ldr r3, [sp, #12]
    movs r0, #0
    str r0, [sp]
    mov r0, r4
    blx r7
    cmp r0, #0
    bne .Lsave_loop
    mov r0, r6
    movw r1, #@SEED_PW_SEL_LO@
    movt r1, #@SEED_PW_SEL_HI@
.globl _pc_seed_pw_sel
_pc_seed_pw_sel:
    add r1, pc
    ldr r1, [r1]
    mov r2, r10
    blx r7
    mov r3, r0
    movw r1, #@SEED_STORE_SEL_LO@
    movt r1, #@SEED_STORE_SEL_HI@
.globl _pc_seed_store_sel
_pc_seed_store_sel:
    add r1, pc
    ldr r1, [r1]
    mov r2, r5
    mov r0, r4
    ldr r10, [sp, #12]
    str r10, [sp]
    movs r10, #0
    str r10, [sp, #4]         // updateExisting: NO
    str r10, [sp, #8]         // NSError** (unused)
    blx r7
    cmp r0, #0
    bne .Lsave_loop
    movs r0, #0
    b .Lseed_done
.Lseed_ok:
    movs r0, #1
.Lseed_done:
    add sp, #16
    pop.w {r4-r8, r10, r11, pc}
.p2align 2
.space 0x400 - (. - _state_request), 0
.globl _state_decode_stage
.thumb_func
_state_decode_stage:
    // Replace only the original objc_msgSend for runDecrypt:. Preserve its
    // return value; emit numeric stage 100 (nil) or 101 (non-nil).
    push.w {r4-r6, lr}
    movw r12, #@STAGE_MSG_LO@
    movt r12, #@STAGE_MSG_HI@
.globl _pc_stage_msg
_pc_stage_msg:
    add r12, pc
    blx r12
    mov r4, r0
    movs r2, #100
    cmp r4, #0
    it ne
    movne r2, #101
    bl _log_parser_stage
    mov r0, r4
    pop.w {r4-r6, lr}
    movw r12, #@DECODE_RETURN_LO@
    movt r12, #@DECODE_RETURN_HI@
.globl _pc_decode_return
_pc_decode_return:
    add r12, pc
    bx r12
.p2align 2
.space 0x480 - (. - _state_request), 0
.globl _state_json_stage
.thumb_func
_state_json_stage:
    // Replace only objectWithUTF8String:length:'s objc_msgSend. Stage 200
    // means JSON object nil; stage 201 means non-nil.
    push.w {r4-r6, lr}
    movw r12, #@STAGE_JSON_MSG_LO@
    movt r12, #@STAGE_JSON_MSG_HI@
.globl _pc_stage_json_msg
_pc_stage_json_msg:
    add r12, pc
    blx r12
    mov r4, r0
    movs r2, #200
    cmp r4, #0
    it ne
    movne r2, #201
    bl _log_parser_stage
    mov r0, r4
    pop.w {r4-r6, lr}
    movw r12, #@JSON_RETURN_LO@
    movt r12, #@JSON_RETURN_HI@
.globl _pc_json_return
_pc_json_return:
    add r12, pc
    bx r12
.p2align 2
.space 0x500 - (. - _state_request), 0
.globl _state_dispatch_stage
.thumb_func
_state_dispatch_stage:
    // The command ID matched and the original result callback is about to run.
    push.w {r0-r3, r6, lr}
    movw r2, #301
    bl _log_parser_stage
    pop.w {r0-r3, r6, lr}
    asrs r2, r1, #0x1f
    blx r6
    movw r12, #@DISPATCH_RETURN_LO@
    movt r12, #@DISPATCH_RETURN_HI@
.globl _pc_dispatch_return
_pc_dispatch_return:
    add r12, pc
    bx r12
.p2align 2
_log_parser_stage:
    push {r4, lr}
    movw r0, #@STAGE_FORMAT_LO@
    movt r0, #@STAGE_FORMAT_HI@
.globl _pc_stage_format
_pc_stage_format:
    add r0, pc
    movw r1, #@STAGE_LABEL_LO@
    movt r1, #@STAGE_LABEL_HI@
.globl _pc_stage_label
_pc_stage_label:
    add r1, pc
    movw r4, #@STAGE_NSL_LO@
    movt r4, #@STAGE_NSL_HI@
.globl _pc_stage_nsl
_pc_stage_nsl:
    add r4, pc
    blx r4
    pop {r4, pc}
.p2align 2
.space 0x580 - (. - _state_request), 0
.globl _state_token_compare
.thumb_func
_state_token_compare:
    // Original _strcmp still runs. Only selected embedded replies compare
    // against the authenticated token before or after the historical login.
    push.w {r4-r8, r10, lr}
    sub sp, #4
    mov r4, r0
    mov r5, r1
    mov r8, sl
    movs r10, #0
    movw r6, #@TOKEN_STRCMP_LO@
    movt r6, #@TOKEN_STRCMP_HI@
.globl _pc_token_strcmp
_pc_token_strcmp:
    add r6, pc
    blx r6
    mov r7, r0
    movw r0, #@TOKEN_INIT_LO@
    movt r0, #@TOKEN_INIT_HI@
.globl _pc_token_init
_pc_token_init:
    add r0, pc
    cmp r8, r0
    beq .Lcompare_history
    movw r0, #@TOKEN_LOGIN_LO@
    movt r0, #@TOKEN_LOGIN_HI@
.globl _pc_token_login
_pc_token_login:
    add r0, pc
    cmp r8, r0
    beq .Lcompare_history
.Lcheck_inventory:
    movw r0, #@TOKEN_INVENTORY_LO@
    movt r0, #@TOKEN_INVENTORY_HI@
.globl _pc_token_inventory
_pc_token_inventory:
    add r0, pc
    cmp r8, r0
    @BACKEND_TOKEN_HOOK@
    movs r10, #1
.Lcompare_history:
    movs r2, #210
    cmp r7, #0
    it eq
    moveq r2, #211
    bl _log_parser_stage
    mov r0, r4
    cmp r10, #0
    bne .Lselect_next_token
    movw r1, #@TOKEN_ARCHIVE_LO@
    movt r1, #@TOKEN_ARCHIVE_HI@
.globl _pc_token_archive
_pc_token_archive:
    add r1, pc
    b .Ldo_token_compare
.Lselect_next_token:
    movw r1, #@TOKEN_NEXT_LO@
    movt r1, #@TOKEN_NEXT_HI@
.globl _pc_token_next
_pc_token_next:
    add r1, pc
.Ldo_token_compare:
    blx r6
    mov r7, r0
    movs r2, #220
    cmp r7, #0
    it eq
    moveq r2, #221
    bl _log_parser_stage
.Ltoken_done:
    mov r0, r7
    add sp, #4
    pop.w {r4-r8, r10, lr}
    movw r12, #@TOKEN_RETURN_LO@
    movt r12, #@TOKEN_RETURN_HI@
.globl _pc_token_return
_pc_token_return:
    add r12, pc
    bx r12
.p2align 2
.space 0x680 - (. - _state_request), 0
.globl _state_id_check
.thumb_func
_state_id_check:
    // Compare the parsed JSON command ID with the original queued ID.
    // Log only 230 (mismatch) or 231 (match), then replay both instructions
    // and leave their flags intact for the original conditional branch.
    push.w {r0-r4, lr}
    ldr.w r0, [sp, #0x84]
    movs r2, #230
    cmp r4, r0
    it eq
    moveq r2, #231
    bl _log_parser_stage
    pop.w {r0-r4, lr}
    ldr r0, [sp, #0x6c]
    cmp r4, r0
    movw r12, #@ID_RETURN_LO@
    movt r12, #@ID_RETURN_HI@
.globl _pc_id_return
_pc_id_return:
    add r12, pc
    bx r12
.p2align 2
.space 0x700 - (. - _state_request), 0
.globl _request_pocket
.thumb_func
_request_pocket:
    push {r4, lr}
    cmp r6, #5
    beq .Lpocket_request
    cmp r6, #6
    bne .Lpocket_request_done
.Lglobal_request:
    mov r0, r8
    adr.w r1, _api_global_name
    bl _matches
    cbz r0, .Lpocket_request_done
    movw r4, #@GLOBAL_REQ_MAP_LO@
    movt r4, #@GLOBAL_REQ_MAP_HI@
.globl _pc_global_req_map
_pc_global_req_map:
    add r4, pc
    str r6, [r4, #20]
    b .Lpocket_request_done
.Lpocket_request:
    mov r0, r8
    adr.w r1, _api_pocket
    bl _matches
    cbz r0, .Lpocket_request_done
    movw r4, #@POCKET_REQ_MAP_LO@
    movt r4, #@POCKET_REQ_MAP_HI@
.globl _pc_pocket_req_map
_pc_pocket_req_map:
    add r4, pc
    str r6, [r4, #16]
.Lpocket_request_done:
    pop {r4, pc}
_api_pocket:
    .asciz "pocket.get"
_api_global_name:
    .asciz "global.get.name"
.p2align 2
.globl _failure_pocket
.thumb_func
_failure_pocket:
    // r12 is the queued ID; failure-hook saved r1/r3 remain on this stack.
    movw r3, #@POCKET_FAIL_MAP_LO@
    movt r3, #@POCKET_FAIL_MAP_HI@
.globl _pc_pocket_fail_map
_pc_pocket_fail_map:
    add r3, pc
    ldr r3, [r3, #16]
    cmp r12, r3
    bne .Lpocket_failure_done
    movw r3, #@POCKET_WIRE_LO@
    movt r3, #@POCKET_WIRE_HI@
.globl _pc_pocket_wire
_pc_pocket_wire:
    add r3, pc
    str r3, [sp, #12]
    str r12, [sp, #4]
.Lpocket_failure_done:
    bx lr
.p2align 2
.globl _failure_global
.thumb_func
_failure_global:
    movw r3, #@GLOBAL_FAIL_MAP_LO@
    movt r3, #@GLOBAL_FAIL_MAP_HI@
.globl _pc_global_fail_map
_pc_global_fail_map:
    add r3, pc
    ldr r3, [r3, #20]
    cmp r12, r3
    bne .Lglobal_failure_done
    movw r3, #@GLOBAL_WIRE_LO@
    movt r3, #@GLOBAL_WIRE_HI@
.globl _pc_global_wire
_pc_global_wire:
    add r3, pc
    str r3, [sp, #12]
    str r12, [sp, #4]
.Lglobal_failure_done:
    bx lr
.p2align 2
.space 0x800 - (. - _state_request), 0
.globl _trace_menu
.thumb_func
_trace_menu:
    // Only bounded queued IDs 3-63; emit allowlist indexes, never API bytes.
    push {r4-r7, lr}
    sub sp, #4
    cmp r6, #3
    blo .Lmenu_done
    cmp r6, #63
    bhi .Lmenu_done
    mov r4, r8
    mov r7, r6
    adr.w r5, _menu_table
    movs r6, #0
.Lmenu_next:
    ldr.w r0, [r5, r6, lsl #2]
    cbz r0, .Lmenu_unknown
    add r1, r5, r0
    mov r0, r4
    bl _matches
    cmp r0, #0
    bne .Lmenu_match
    adds r6, #1
    b .Lmenu_next
.Lmenu_unknown:
    movs r6, #99
.Lmenu_match:
    movs r2, #100
    mul r2, r7, r2
    add r2, r6
    bl _log_parser_stage
.Lmenu_done:
    add sp, #4
    pop {r4-r7, pc}
.p2align 2
.globl _menu_table
_menu_table:
    @MENU_TABLE@
.p2align 2
.space 0x900 - (. - _state_request), 0
.globl _request_menu
.thumb_func
_request_menu:
    // Request IDs are counters, not APIs. Every selection checks exact bytes
    // and preserves the original failure for an unrelated API at the same ID.
    push {r4, lr}
    cmp r6, #7
    beq .Lmenu_pocket_request
    cmp r6, #8
    beq .Lmenu_gift_request
    cmp r6, #9
    bne .Lmenu_request_done
    adr.w r1, _api_ranking
    b .Lmenu_compare
.Lmenu_pocket_request:
    adr.w r1, _api_menu_pocket
    b .Lmenu_compare
.Lmenu_gift_request:
    adr.w r1, _api_gift_count
.Lmenu_compare:
    mov r0, r8
    bl _matches
    cbz r0, .Lmenu_request_done
    movw r4, #@MENU_REQ_MAP_LO@
    movt r4, #@MENU_REQ_MAP_HI@
.globl _pc_menu_req_map
_pc_menu_req_map:
    add r4, pc
    subs r2, r6, #1
    lsls r2, r2, #2
    str r6, [r4, r2]
.Lmenu_request_done:
    pop {r4, pc}
_api_menu_pocket:
    .asciz "pocket.get"
_api_gift_count:
    .asciz "gift.get.count"
_api_ranking:
    .asciz "score.ranking"
.p2align 2
.globl _failure_menu
.thumb_func
_failure_menu:
    cmp r12, #7
    blo .Lmenu_failure_done
    cmp r12, #9
    bhi .Lmenu_failure_done
    movw r3, #@MENU_FAIL_MAP_LO@
    movt r3, #@MENU_FAIL_MAP_HI@
.globl _pc_menu_fail_map
_pc_menu_fail_map:
    add r3, pc
    subs r2, r12, #1
    lsls r2, r2, #2
    ldr r3, [r3, r2]
    cmp r12, r3
    bne .Lmenu_failure_done
    cmp r12, #7
    beq .Lmenu_pocket_wire
    cmp r12, #8
    beq .Lmenu_gift_wire
    movw r3, #@RANKING_WIRE_LO@
    movt r3, #@RANKING_WIRE_HI@
.globl _pc_ranking_wire
_pc_ranking_wire:
    add r3, pc
    b .Lmenu_reply_selected
.Lmenu_pocket_wire:
    movw r3, #@POCKET_MENU_WIRE_LO@
    movt r3, #@POCKET_MENU_WIRE_HI@
.globl _pc_pocket_menu_wire
_pc_pocket_menu_wire:
    add r3, pc
    b .Lmenu_reply_selected
.Lmenu_gift_wire:
    movw r3, #@GIFT_WIRE_LO@
    movt r3, #@GIFT_WIRE_HI@
.globl _pc_gift_wire
_pc_gift_wire:
    add r3, pc
.Lmenu_reply_selected:
    str r3, [sp, #12]
    str r12, [sp, #4]
.Lmenu_failure_done:
    bx lr
.p2align 2
.globl _state_failure_tail
_state_failure_tail:
    // These labels indicate offline reply selection versus original failure,
    // not raw API names. Log only numeric request IDs.
    push.w {r0-r4, lr}
    cmp.w r1, #-1
    beq .Llog_unhandled
    movw r1, #@LOG_SELECTED_LO@
    movt r1, #@LOG_SELECTED_HI@
.globl _pc_log_selected
_pc_log_selected:
    add r1, pc
    b .Llog_call
.Llog_unhandled:
    movw r1, #@LOG_UNHANDLED_LO@
    movt r1, #@LOG_UNHANDLED_HI@
.globl _pc_log_unhandled
_pc_log_unhandled:
    add r1, pc
.Llog_call:
    movw r0, #@LOG_FORMAT_LO@
    movt r0, #@LOG_FORMAT_HI@
.globl _pc_log_format
_pc_log_format:
    add r0, pc
    ldr r2, [r6, #8]
    movw r4, #@LOG_NSL_LO@
    movt r4, #@LOG_NSL_HI@
.globl _pc_log_nsl
_pc_log_nsl:
    add r4, pc
    blx r4
    pop.w {r0-r4, lr}
    movw r12, #@CALLBACK_LO@
    movt r12, #@CALLBACK_HI@
.globl _pc_callback
_pc_callback:
    add r12, pc
    blx r12
    movw r12, #@FAIL_RETURN_LO@
    movt r12, #@FAIL_RETURN_HI@
.globl _pc_fail_return
_pc_fail_return:
    add r12, pc
    bx r12
@BACKEND_BRIDGES@
.space 0xb00 - (. - _state_request), 0
.p2align 2
_save_table:
    @SAVE_TABLE@
.p2align 2
.globl _init_wire
_init_wire:
    // C++ receiver at 0x206dde skips one leading nonnegative byte before
    // constructing the NSString passed to runDecrypt:. Without this frame
    // byte, the AES/Base64 reply loses its first character.
    .asciz "0@SERVER_INIT_WIRE@"
.globl _login_wire
_login_wire:
    .asciz "0@POCKET_LOGIN_WIRE@"
.globl _inventory_wire
_inventory_wire:
    .asciz "0@INVENTORY_LIST_WIRE@"
.globl _custom_wire
_custom_wire:
    .asciz "0@CUSTOM_GET_WIRE@"
.globl _pocket_wire
_pocket_wire:
    .asciz "0@POCKET_GET_WIRE@"
.globl _global_wire
_global_wire:
    .asciz "0@GLOBAL_NAME_WIRE@"
.globl _pocket_menu_wire
_pocket_menu_wire:
    .asciz "0@POCKET_MENU_WIRE@"
.globl _gift_wire
_gift_wire:
    .asciz "0@GIFT_COUNT_WIRE@"
.globl _ranking_wire
_ranking_wire:
    .asciz "0@RANKING_WIRE@"
@SAVE_ASSETS@
@MENU_NAMES@
.globl _historical_reply_token
_historical_reply_token:
    @ACCESS_TOKEN_BYTES@
.globl _historical_next_token
_historical_next_token:
    @NEXT_ACCESS_TOKEN_BYTES@
