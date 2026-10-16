// Birzzle Fever iOS 1.0.4, image-relative callsite trampolines only.
// All four routines preserve incoming arguments; no account data logged.
// Every external address is computed from PC: the main image is ASLR-slid.
.syntax unified
.thumb
.text
.p2align 2

.globl _trace_command
.thumb_func
_trace_command:
    // Replaces the 32-bit objc_msgSend BLX at 0x206a2c. At this point the
    // function has incremented its numeric command/request counter and put it
    // at [sp, #0x20]; the HTTP commandId is formatted from that same value.
    push.w {r0-r4, lr}
    ldr r2, [sp, #0x38]         // original [sp, #0x20] after 24-byte push
    movw r0, #0xaa3e           // 0x480050 - (PC at add r0,pc)
    movt r0, #0x0047
    add r0, pc
    movw r1, #0x2164           // 0x477780 - (PC at add r1,pc)
    movt r1, #0x0047
    add r1, pc
    movw r4, #0xe786           // 0x373dac - (PC at add r4,pc)
    movt r4, #0x0036
    add r4, pc
    blx r4
    pop.w {r0-r4, lr}
    // Preserve original variadic arguments at the original stack pointer.
    movw r12, #0xe9c6          // 0x373ffc - (PC at add r12,pc)
    movt r12, #0x0036
    add r12, pc
    blx r12
    movw r12, #0x13ef          // 0x206a31 - (PC at add r12,pc)
    movt r12, #0x0020
    add r12, pc
    bx r12

    // Reserve the following aligned location for the second four-byte hook.
    .space 128 - (. - _trace_command), 0

.globl _trace_fail
.thumb_func
_trace_fail:
    // Replaces the original first four bytes at 0x1d60c8. m_requestId is
    // the 32-bit int ivar at self+8 in the inspected ConnectorProxy class.
    push.w {r0-r4, lr}
    ldr r2, [r0, #8]
    movw r0, #0xa9be           // 0x480050 - (PC at add r0,pc)
    movt r0, #0x0047
    add r0, pc
    movw r1, #0xa124           // 0x47f7c0 - (PC at add r1,pc)
    movt r1, #0x0047
    add r1, pc
    movw r4, #0xe706           // 0x373dac - (PC at add r4,pc)
    movt r4, #0x0036
    add r4, pc
    blx r4
    pop.w {r0-r4, lr}
    push {r4-r7, lr}           // replay the original four-byte prologue
    add r7, sp, #0xc
    movw r12, #0x0a13          // 0x1d60cd - (PC at add r12,pc)
    movt r12, #0x001d
    add r12, pc
    bx r12

    // Keep the third hook at a separate, aligned executable cave address.
    .space 256 - (. - _trace_command), 0

.globl _trace_transport_error
.thumb_func
_trace_transport_error:
    // Replaces the first four bytes of RankingCore
    // -connection:didFailWithError: at 0x1d56c8. r3 is NSError *.
    // Log only the NSError domain identifier and numeric code.
    push.w {r0-r6, lr}
    mov r5, r3
    mov r0, r5
    movw r1, #0x50a0           // 0x46a7b4 @selector(code), PC-relative
    movt r1, #0x0046
    add r1, pc
    ldr r1, [r1]
    movw r4, #0xe8dc           // 0x373ffc _objc_msgSend, PC-relative
    movt r4, #0x0036
    add r4, pc
    blx r4
    mov r6, r0
    mov r0, r5
    movw r1, #0x6fbc           // 0x46c6ec @selector(domain), PC-relative
    movt r1, #0x0046
    add r1, pc
    ldr r1, [r1]
    blx r4
    mov r1, r0
    mov r2, r6
    movw r0, #0xa90e           // 0x480050 @"%@:%d", PC-relative
    movt r0, #0x0047
    add r0, pc
    movw r4, #0xe660           // 0x373dac _NSLog, PC-relative
    movt r4, #0x0036
    add r4, pc
    blx r4
    pop.w {r0-r6, lr}
    push {r4-r7, lr}           // replay original RankingCore prologue
    add r7, sp, #0xc
    movw r12, #0xff6d          // 0x1d56cd original return, PC-relative
    movt r12, #0x001c
    add r12, pc
    bx r12

    // The next hook gets its own padding region; older diagnostic binaries
    // remain separate rollback artifacts and are never overwritten.
    .space 512 - (. - _trace_command), 0

.globl _trace_api_host
.thumb_func
_trace_api_host:
    // ConnectorProxy -request:handler:api:params: at 0x1d5e70.
    // r2 is the numeric request ID; [sp] is the API NSString at entry.
    // Only uppercase dotted API identifiers and URL.host are logged.
    push.w {r0-r8, lr}
    mov r6, r2
    ldr r5, [sp, #40]
    cmp r5, #0
    beq.w .Lunknown_api
    movw r1, #0x4c42             // 0x46a45c @selector(UTF8String)
    movt r1, #0x0046
    add r1, pc
    ldr r1, [r1]
    movw r4, #0xe7d6             // 0x373ffc _objc_msgSend
    movt r4, #0x0036
    add r4, pc
    mov r0, r5
    blx r4
    mov r8, r0
    cmp r8, #0
    beq.w .Lunknown_api
    movs r7, #0
    movs r3, #0
.Lapi_check:
    ldrb r0, [r8, r7]
    cbz r0, .Lapi_checked
    cmp r7, #31
    bhs.w .Lunknown_api
    cmp r0, #'.'
    beq .Lapi_dot
    cmp r0, #'A'
    blo.w .Lunknown_api
    cmp r0, #'Z'
    bhi.w .Lknown_api           // Lowercase input is logged only on exact binary literal match.
    adds r7, #1
    b .Lapi_check
.Lapi_dot:
    movs r3, #1
    adds r7, #1
    b .Lapi_check
.Lapi_checked:
    cbz r7, .Lunknown_api
    cmp r3, #0
    beq.w .Lunknown_api
    mov r1, r5
    b .Lapi_log
.Lunknown_api:
    movw r1, #0x1f0c             // 0x477780 @"request"
    movt r1, #0x0047
    add r1, pc
.Lapi_log:
    mov r2, r6
    movw r0, #0xa7d0             // 0x480050 @"%@:%d"
    movt r0, #0x0047
    add r0, pc
    movw r4, #0xe522             // 0x373dac _NSLog
    movt r4, #0x0036
    add r4, pc
    blx r4

    // Convert only the app's runtime server string, then print NSURL.host.
    movw r0, #0x9de2             // 0x46f678 NSString class reference
    movt r0, #0x0046
    add r0, pc
    ldr r0, [r0]
    movw r1, #0x4a06             // 0x46a2a8 @selector(stringWithUTF8String:)
    movt r1, #0x0046
    add r1, pc
    ldr r1, [r1]
    movw r2, #0xde32             // 0x4936e0 runtime server C string
    movt r2, #0x0048
    add r2, pc
    movw r4, #0xe744             // 0x373ffc _objc_msgSend
    movt r4, #0x0036
    add r4, pc
    blx r4
    mov r2, r0
    movw r0, #0x9dbe             // 0x46f684 NSURL class reference
    movt r0, #0x0046
    add r0, pc
    ldr r0, [r0]
    movw r1, #0x6392             // 0x46bc64 @selector(URLWithString:relativeToURL:)
    movt r1, #0x0046
    add r1, pc
    ldr r1, [r1]
    movs r3, #0
    blx r4
    movw r1, #0x50a2             // 0x46a984 @selector(host)
    movt r1, #0x0046
    add r1, pc
    ldr r1, [r1]
    blx r4
    mov r1, r0
    mov r2, r6
    movw r0, #0xa75c             // 0x480050 @"%@:%d"
    movt r0, #0x0047
    add r0, pc
    movw r4, #0xe4ae             // 0x373dac _NSLog
    movt r4, #0x0036
    add r4, pc
    blx r4
    pop.w {r0-r8, lr}
    push {r4-r7, lr}             // replay original four-byte prologue
    add r7, sp, #0xc
    movw r12, #0x0563           // 0x1d5e75 original return
    movt r12, #0x001d
    add r12, pc
    bx r12

    // Keep the preceding three hooks and all existing PC-relative operands
    // byte-for-byte stable. This path is reached only for lowercase/mixed API
    // strings that fail the uppercase-dotted check.
.Lknown_api:
    adr.w r1, _trace_api_table
.globl _trace_api_base
_trace_api_base:
    mov r3, pc                   // 0x591a + image slide; checked by the builder.
.Lnext_api:
    ldr r0, [r1], #4
    cmp r0, #0
    beq.w .Lunknown_api
    add r0, r3
    mov r2, r8
.Lcompare_api:
    ldrb r7, [r2], #1
    ldrb r4, [r0], #1
    cmp r7, r4
    bne .Lnext_api
    cmp r7, #0
    bne .Lcompare_api
    mov r1, r5
    b.w .Lapi_log

    // These are complete, NUL-terminated API literals in the clean IPA.
    // Only an exact match may be printed; unknown strings stay "request".
    .p2align 2
.globl _trace_api_table
_trace_api_table:
    // The PC constant is the checked instruction at _trace_api_base + 4.
    // Absolute arithmetic avoids Mach-O SUBTRACTOR relocations in the cave.
    .long 0x38c847 - 0x591a // pocket.login
    .long 0x38cb72 - 0x591a // pocket.get
    .long 0x38cbe9 - 0x591a // pocket.set
    .long 0x38cc33 - 0x591a // pocket.sync
    .long 0x38ce48 - 0x591a // inventory.list
    .long 0x38ce83 - 0x591a // inventory.use
    .long 0x38ce91 - 0x591a // inventory.update
    .long 0x38ce62 - 0x591a // inventory.buy
    .long 0x38ce74 - 0x591a // inventory.sell
    .long 0x38d282 - 0x591a // custom.get
    .long 0x38ca81 - 0x591a // custom.post
    .long 0x38cd85 - 0x591a // global.get.name
    .long 0x38cd95 - 0x591a // global.update.name
    .long 0x38d218 - 0x591a // gift.get.count
    .long 0x38d227 - 0x591a // gift.get.list
    .long 0x38d20e - 0x591a // gift.send
    .long 0x38d26a - 0x591a // gift.take
    .long 0x38cc5f - 0x591a // score.ranking
    .long 0x38cd2e - 0x591a // score.globalranking
    .long 0x38cce7 - 0x591a // score.post
    .long 0x38ceaf - 0x591a // profile.regist.platform
    .long 0x38cfda - 0x591a // profile.merge.platform
    .long 0x38d122 - 0x591a // profile.reset.friend
    .long 0x38d0a5 - 0x591a // profile.update
    .long 0x38d0dc - 0x591a // profile.logout.platform
    .long 0x38d029 - 0x591a // friend.find
    .long 0x38cd0c - 0x591a // friend.message
    .long 0x38d297 - 0x591a // quest.update.status
    .long 0x38ce01 - 0x591a // purchase.validate
    .long 0x38c658 - 0x591a // server.init.2 (versioned startup API)
    .long 0
