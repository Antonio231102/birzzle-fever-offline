"""Build guarded iOS 6 historical startup and exact read-only responses.

The archive embeds private account data and remains ignored under ios/*.ipa.
Original iPad Keychain account and Android backup are never changed.
Historical read replies are not a mutable offline gameplay backend.
"""

import argparse
from pathlib import Path
import json
import struct
import subprocess
import tempfile
import zipfile

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

import patch_startup_probe as base
import patch_offline_startup as startup
import prepare_offline_history as history
import trace_request_ids as trace

ROOT = Path(__file__).resolve().parent
ASSEMBLY = ROOT / "offline_state_thumb.s"
CAVE_VM = 0x5600
CAVE_OFFSET = CAVE_VM - base.IMAGE_BASE
ACCOUNT_VM = 0x38F097
OLD_ACCOUNT = b"BirzzleFeverUser"
OFFLINE_ACCOUNT = b"BirzzleOffline01"
BSS_REQUESTS = 0x494D00
BOOT_OPTIONS = (0xA644, b"\xf0\xb5\x03\xaf", CAVE_VM + 0x200)
BOOT_LEGACY = (0xA2C8, b"\xf0\xb5\x03\xaf", CAVE_VM + 0x240)
REQUEST = (0x1D5E70, b"\xf0\xb5\x03\xaf", CAVE_VM)
FAILURE = (0x1D6126, bytes.fromhex("30f09bfd"), CAVE_VM + 0x100)
DECODE_STAGE = (0x206E1C, bytes.fromhex("6df1eee8"), CAVE_VM + 0x400)
JSON_STAGE = (0x206F9E, bytes.fromhex("6df12ee8"), CAVE_VM + 0x480)
DISPATCH_STAGE = (0x20710A, bytes.fromhex("ca17b047"), CAVE_VM + 0x500)
TOKEN_COMPARE = (0x20703C, bytes.fromhex("6df116ef"), CAVE_VM + 0x580)
ID_CHECK = (0x206FF2, bytes.fromhex("1b988442"), CAVE_VM + 0x680)
HOOKS = (BOOT_OPTIONS, BOOT_LEGACY, REQUEST, FAILURE,
         DECODE_STAGE, JSON_STAGE, DISPATCH_STAGE, TOKEN_COMPARE, ID_CHECK)
PC_TARGETS = {
    "REQ_UTF8": ("_pc_req_utf8", 0x46A45C),
    "REQ_MSG": ("_pc_req_msg", 0x373FFC),
    "REQ_CLEAR": ("_pc_req_clear", BSS_REQUESTS),
    "REQ_MAP": ("_pc_req_map", BSS_REQUESTS),
    "REQ_RETURN": ("_pc_req_return", REQUEST[0] + 5),
    "FAIL_MAP": ("_pc_fail_map", BSS_REQUESTS),
    "INIT_WIRE": ("_pc_init_wire", "_init_wire"),
    "LOGIN_WIRE": ("_pc_login_wire", "_login_wire"),
    "INVENTORY_WIRE": ("_pc_inventory_wire", "_inventory_wire"),
    "CUSTOM_WIRE": ("_pc_custom_wire", "_custom_wire"),
    "POCKET_REQ_MAP": ("_pc_pocket_req_map", BSS_REQUESTS),
    "POCKET_FAIL_MAP": ("_pc_pocket_fail_map", BSS_REQUESTS),
    "POCKET_WIRE": ("_pc_pocket_wire", "_pocket_wire"),
    "GLOBAL_REQ_MAP": ("_pc_global_req_map", BSS_REQUESTS),
    "GLOBAL_FAIL_MAP": ("_pc_global_fail_map", BSS_REQUESTS),
    "GLOBAL_WIRE": ("_pc_global_wire", "_global_wire"),
    "MENU_REQ_MAP": ("_pc_menu_req_map", BSS_REQUESTS),
    "MENU_FAIL_MAP": ("_pc_menu_fail_map", BSS_REQUESTS),
    "POCKET_MENU_WIRE": ("_pc_pocket_menu_wire", "_pocket_menu_wire"),
    "GIFT_WIRE": ("_pc_gift_wire", "_gift_wire"),
    "RANKING_WIRE": ("_pc_ranking_wire", "_ranking_wire"),
    "LOG_SELECTED": ("_pc_log_selected", 0x477780),
    "LOG_UNHANDLED": ("_pc_log_unhandled", 0x47F7C0),
    "LOG_FORMAT": ("_pc_log_format", 0x480050),
    "LOG_NSL": ("_pc_log_nsl", 0x373DAC),
    "CALLBACK": ("_pc_callback", 0x206C61),
    "FAIL_RETURN": ("_pc_fail_return", FAILURE[0] + 5),
    "OPTIONS_RETURN": ("_pc_options_return", BOOT_OPTIONS[0] + 5),
    "LEGACY_RETURN": ("_pc_legacy_return", BOOT_LEGACY[0] + 5),
    "SEED_HELPER": ("_pc_seed_helper", 0x46F7D4),
    "SEED_ACCOUNT": ("_pc_seed_account", 0x476510),
    "SEED_STRING_CLASS": ("_pc_seed_string_class", 0x46F678),
    "SEED_MSG": ("_pc_seed_msg", 0x373FFC),
    "SEED_STRING_SEL": ("_pc_seed_string_sel", 0x46A2A8),
    "SEED_GET_SEL": ("_pc_seed_get_sel", 0x46AB44),
    "SEED_PW_SEL": ("_pc_seed_pw_sel", 0x46A2A8),
    "SEED_STORE_SEL": ("_pc_seed_store_sel", 0x46AD30),
    "STAGE_MSG": ("_pc_stage_msg", 0x373FFC),
    "STAGE_JSON_MSG": ("_pc_stage_json_msg", 0x373FFC),
    "DECODE_RETURN": ("_pc_decode_return", DECODE_STAGE[0] + 5),
    "JSON_RETURN": ("_pc_json_return", JSON_STAGE[0] + 5),
    "DISPATCH_RETURN": ("_pc_dispatch_return", DISPATCH_STAGE[0] + 5),
    "STAGE_FORMAT": ("_pc_stage_format", 0x480050),
    "STAGE_LABEL": ("_pc_stage_label", 0x477780),
    "STAGE_NSL": ("_pc_stage_nsl", 0x373DAC),
    "TOKEN_STRCMP": ("_pc_token_strcmp", 0x374E6C),
    "TOKEN_INIT": ("_pc_token_init", "_init_wire"),
    "TOKEN_LOGIN": ("_pc_token_login", "_login_wire"),
    "TOKEN_INVENTORY": ("_pc_token_inventory", "_inventory_wire"),
    "TOKEN_NEXT": ("_pc_token_next", "_historical_next_token"),
    "TOKEN_ARCHIVE": ("_pc_token_archive", "_historical_reply_token"),
    "TOKEN_RETURN": ("_pc_token_return", TOKEN_COMPARE[0] + 5),
    "ID_RETURN": ("_pc_id_return", ID_CHECK[0] + 5),
}
FIXED_LABELS = {"_state_request": 0, "_state_failure": 0x100,
                "_state_launch_options": 0x200, "_state_launch_legacy": 0x240,
                "_state_decode_stage": 0x400, "_state_json_stage": 0x480,
                "_state_dispatch_stage": 0x500, "_state_token_compare": 0x580,
                "_state_id_check": 0x680, "_request_pocket": 0x700,
                "_trace_menu": 0x800, "_menu_table": None,
                "_request_menu": 0x900, "_failure_menu": None,
                "_failure_pocket": None, "_failure_global": None,
                "_historical_reply_token": None, "_historical_next_token": None,
                "_save_table": None, "_init_wire": None, "_login_wire": None,
                "_inventory_wire": None, "_custom_wire": None, "_pocket_wire": None,
                "_global_wire": None, "_pocket_menu_wire": None, "_gift_wire": None,
                "_ranking_wire": None}
ALL_LABELS = set(FIXED_LABELS) | {label for label, _ in PC_TARGETS.values()}


def private_package(image: bytes) -> dict:
    private = ROOT / "captures/offline-history.json"
    if not private.is_file():
        raise ValueError("Generate ios/captures/offline-history.json first")
    supplied = json.loads(private.read_text(encoding="utf-8"))
    expected = history.prepare(ROOT.parent / "com.halfbrick.birzzlefever-20160501-111000.tar.gz", image)
    if supplied != expected:
        raise ValueError("Private history data differs from authenticated source")
    if len(OLD_ACCOUNT) != len(OFFLINE_ACCOUNT):
        raise ValueError("Offline Keychain account length changed")
    return expected


def archived_access_token(image: bytes, package: dict) -> bytes:
    """Match two independently authenticated cached replies, never print the token."""
    key = history.incoming_key(image)
    result = None
    for command, request_id in (("SERVER.INIT", "1"), ("POCKET.LOGIN", "2")):
        body = history.decode_incoming_reply(package["incoming_replies"][command], key)
        reply = json.loads(body)
        value = reply.get("accesstoken")
        if reply.get("commandid") != request_id or not isinstance(value, str):
            raise ValueError("Missing authenticated response command ID or access token")
        encoded = value.encode("ascii")
        if not 0 < len(encoded) <= 128 or any(not 32 <= byte < 127 for byte in encoded):
            raise ValueError("Historical response access token is not a bounded C string")
        if result is not None and result != encoded:
            raise ValueError("Historical startup/login access tokens differ")
        result = encoded
    return result


def post_login_access_token(image: bytes, package: dict) -> bytes:
    """Bind authenticated post-login read replies to the login transition."""
    key = history.incoming_key(image)
    login = json.loads(history.decode_incoming_reply(package["incoming_replies"]["POCKET.LOGIN"], key))
    inventory = json.loads(history.decode_incoming_reply(package["incoming_replies"]["INVENTORY.LIST"], key))
    custom = json.loads(history.decode_incoming_reply(package["incoming_replies"]["CUSTOM.GET"], key))
    pocket = json.loads(history.decode_incoming_reply(package["incoming_replies"]["POCKET.GET"], key))
    global_name = json.loads(history.decode_incoming_reply(package["incoming_replies"]["GLOBAL.GET.NAME"], key))
    gift = json.loads(history.decode_incoming_reply(package["incoming_replies"]["GIFT.GET.COUNT"], key))
    ranking = json.loads(history.decode_incoming_reply(package["incoming_replies"]["SCORE.RANKING"], key))
    value = login.get("newaccesstoken")
    if (login.get("commandid") != "2" or inventory.get("commandid") != "3"
            or custom.get("commandid") != "4" or pocket.get("commandid") != "7"
            or global_name.get("commandid") != "6" or gift.get("commandid") != "8"
            or ranking.get("commandid") != "9" or not isinstance(value, str)
            or value == login.get("accesstoken")
            or any(value != row.get("accesstoken") for row in
                   (inventory, custom, pocket, global_name, gift, ranking))):
        raise ValueError("Historical read reply tokens are not authenticated post-login tokens")
    encoded = value.encode("ascii")
    if not 0 < len(encoded) <= 128 or any(not 32 <= byte < 127 for byte in encoded):
        raise ValueError("Post-login token is not a bounded C string")
    return encoded


def ios_offline_wire(image: bytes, package: dict, command: str, request_id: str | None = None) -> str:
    """Adapt authenticated Android fields for exact, guarded iOS commands."""
    contracts = {"SERVER.INIT": ("1", ("1",)), "POCKET.LOGIN": ("2", ("2",)),
                 "INVENTORY.LIST": ("3", ("3",)), "CUSTOM.GET": ("4", ("4",)),
                 "POCKET.GET": ("7", ("5", "7")), "GLOBAL.GET.NAME": ("6", ("6",)),
                 "GIFT.GET.COUNT": ("8", ("8",)), "SCORE.RANKING": ("9", ("9",))}
    if command not in contracts:
        raise ValueError("No guarded iOS response contract for this historical command")
    historical_id, valid_ids = contracts[command]
    request_id = valid_ids[0] if request_id is None else request_id
    if request_id not in valid_ids:
        raise ValueError("Unobserved queued iOS ID for authenticated historical command")
    key = history.incoming_key(image)
    original = json.loads(history.decode_incoming_reply(package["incoming_replies"][command], key))
    timeout = original.get("timeout")
    if (original.get("commandid") != historical_id or not isinstance(timeout, str)
            or not timeout.isdecimal() or not 0 < int(timeout) <= 3600
            or (command == "SERVER.INIT" and timeout != "1")):
        raise ValueError("Historical reply no longer matches guarded iOS timeout adaptation")
    adapted = dict(original)
    # Original iOS passes nonzero timeouts to async cleanup as pointers.
    # Its offline no-timeout branch avoids that cross-platform type mismatch.
    adapted["timeout"] = "0"
    changed = {"timeout"}
    if historical_id != request_id:
        adapted["commandid"] = request_id
        changed.add("commandid")
    if command == "SERVER.INIT":
        version = b"2.0.17.HBI"
        if (image.count(version) != 1
                or not isinstance(original.get("requestversion"), str)
                or original["requestversion"] == version.decode("ascii")):
            raise ValueError("Historical startup version no longer needs iOS adaptation")
        adapted["requestversion"] = version.decode("ascii")
        changed.add("requestversion")
    if command == "SCORE.RANKING":
        ranking = original.get("ranking")
        if (not isinstance(ranking, list) or len(ranking) != 2
                or any(not isinstance(row, dict) for row in ranking)
                or not isinstance(ranking[0].get("uid"), str)
                or not ranking[0]["uid"] or ranking[0]["uid"] != ranking[1].get("uid")
                or any(row.get(field) != "0" for row in ranking
                       for field in ("scorecurrent", "scorehighest"))):
            raise ValueError("Archived ranking no longer matches proven V25 duplicate-score sentinel case")
        # Original Android V25 established this distinct two-slot score template:
        # preserve the historical identity and writable second slot, never the
        # archived equal-zero pair that crashed the original leaderboard.
        adapted["ranking"] = [dict(ranking[0], scorecurrent="-1", scorehighest="-1"),
                              ranking[1]]
        changed.add("ranking")
    if any(original[name] != adapted[name] for name in original if name not in changed):
        raise ValueError("Historical reply state changed outside iOS compatibility fields")
    body = json.dumps(adapted, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    wire = history.encode_incoming_reply(body, key)
    if json.loads(history.decode_incoming_reply(wire, key)) != adapted:
        raise ValueError("Adapted iOS wire roundtrip failed")
    return wire


def object_text(blob: bytes, asset_labels: set[str],
                extra_labels: set[str] | None = None):
    if struct.unpack_from("<IIII", blob) != (0xFEEDFACE, 12, 9, 1):
        raise ValueError("Not an ARMv7 Mach-O object")
    text = None
    symtab = None
    cursor = 28
    for _ in range(struct.unpack_from("<I", blob, 16)[0]):
        command, size = struct.unpack_from("<II", blob, cursor)
        if command == 1:
            for j in range(struct.unpack_from("<I", blob, cursor + 48)[0]):
                section = struct.unpack_from("<16s16sIIIIIIIII", blob, cursor + 56 + 68 * j)
                if section[0].split(b"\0", 1)[0] == b"__text":
                    if section[7]:
                        raise ValueError("Unresolved native relocation")
                    text = blob[section[4]:section[4] + section[3]]
        elif command == 2:
            symtab = struct.unpack_from("<IIII", blob, cursor + 8)
        cursor += size
    if text is None or symtab is None:
        raise ValueError("Missing native code or symbol list")
    symoff, count, stroff, _ = symtab
    labels = {}
    for j in range(count):
        offset = symoff + 12 * j
        string_index = struct.unpack_from("<I", blob, offset)[0]
        if string_index:
            name = blob[stroff + string_index:].split(b"\0", 1)[0].decode("ascii", "replace")
            if name in ALL_LABELS | asset_labels | (extra_labels or set()):
                labels[name] = struct.unpack_from("<I", blob, offset + 8)[0]
    if labels.keys() != ALL_LABELS | asset_labels | (extra_labels or set()):
        raise ValueError("Offline method or asset labels differ from pinned image sites")
    for name, address in FIXED_LABELS.items():
        if address is not None and labels[name] != address:
            raise ValueError("Native method entrypoint moved")
    return text, labels


def assemble(image: bytes, package: dict, *, backend_vm: int | None = None,
             backend_exports: dict[str, int] | None = None) -> bytes:
    template = ASSEMBLY.read_text(encoding="utf-8")
    targets = dict(PC_TARGETS)
    bridge_labels = set()
    if backend_vm is not None:
        if backend_exports is None or not {
            "_bf_ios_request", "_bf_ios_reply", "_bf_ios_token_kind"
        } <= backend_exports.keys():
            raise ValueError("Missing validated iOS native backend entrypoints")
        targets.update(
            BF_SELECTOR=("_pc_bf_selector", 0x46A45C),
            BF_REQUEST_CTX=("_pc_bf_request_ctx", BSS_REQUESTS + 0x80),
            BF_FAILURE_CTX=("_pc_bf_failure_ctx", BSS_REQUESTS + 0x80),
            BF_REQUEST_FN=("_pc_bf_request_fn", backend_vm + backend_exports["_bf_ios_request"]),
            BF_FAILURE_FN=("_pc_bf_failure_fn", backend_vm + backend_exports["_bf_ios_reply"]),
            BF_TOKEN_CTX=("_pc_bf_token_ctx", BSS_REQUESTS + 0x80),
            BF_TOKEN_FN=("_pc_bf_token_fn", backend_vm + backend_exports["_bf_ios_token_kind"]),
        )
        bridge_labels = {"_bf_request_bridge", "_bf_failure_bridge", "_bf_token_bridge"}
        template = template.replace("    bl _trace_menu\n", "    bl _bf_request_bridge\n", 1)
        template = template.replace("@BACKEND_REQUEST_HOOK@", "")
        template = template.replace("@BACKEND_FAILURE_HOOK@", "bl _bf_failure_bridge")
        template = template.replace(
            "@BACKEND_TOKEN_HOOK@",
            "beq .Lbf_post_login\n"
            "    bl _bf_token_bridge\n"
            "    cmp r0, #0\n"
            "    beq .Ltoken_done\n"
            "    cmp r0, #1\n"
            "    beq .Lcompare_history\n"
            ".Lbf_post_login:",
        )
        template = template.replace("@BACKEND_BRIDGES@",
                                    (ROOT / "offline_bridge_thumb.s").read_text(encoding="utf-8"))
    else:
        for marker in ("@BACKEND_REQUEST_HOOK@", "@BACKEND_FAILURE_HOOK@",
                       "@BACKEND_BRIDGES@"):
            template = template.replace(marker, "")
        template = template.replace("@BACKEND_TOKEN_HOOK@", "bne .Ltoken_done")
    records = [package["keychain_records"][key] for key in sorted(package["keychain_records"])]
    token = archived_access_token(image, package)
    next_token = post_login_access_token(image, package)
    asset_labels = {f"_save_{kind}_{j}" for j in range(len(records)) for kind in ("service", "password")}
    assets = []
    for j, record in enumerate(records):
        service, password = record["service"], record["password"]
        if len(service) != 32 or not service.isascii() or not password.isascii():
            raise ValueError("Invalid native save service/password string")
        assets.extend((f".globl _save_service_{j}", f"_save_service_{j}:", f'    .asciz "{service}"',
                       f".globl _save_password_{j}", f"_save_password_{j}:", f'    .asciz "{password}"'))
    menu_names = trace.ALLOWED_API_NAMES
    if (len(menu_names) != 30 or len(set(menu_names)) != len(menu_names)
            or any(image.count(name.encode("ascii") + b"\0") != 1 for name in menu_names)):
        raise ValueError("Menu-request exact API list differs from verified original iOS constants")
    menu_assets = [line for j, name in enumerate(menu_names)
                   for line in (f".globl _menu_name_{j}", f"_menu_name_{j}:",
                                f'    .asciz "{name}"')]
    asset_labels |= {f"_menu_name_{j}" for j in range(len(menu_names))}
    substitutions = {key + part: "0" for key in targets for part in ("_LO", "_HI")}
    substitutions.update(SAVE_TABLE="\n".join("    .word 0" for _ in range(2 * len(records) + 1)),
                         SAVE_ASSETS="\n".join(assets),
                         MENU_TABLE="\n".join("    .word 0" for _ in range(len(menu_names) + 1)),
                         MENU_NAMES="\n".join(menu_assets),
                         ACCESS_TOKEN_BYTES="    .byte " + ", ".join(str(byte) for byte in token + b"\0"),
                         NEXT_ACCESS_TOKEN_BYTES="    .byte " + ", ".join(str(byte) for byte in next_token + b"\0"),
                         SERVER_INIT_WIRE=ios_offline_wire(image, package, "SERVER.INIT"),
                         POCKET_LOGIN_WIRE=ios_offline_wire(image, package, "POCKET.LOGIN"),
                         INVENTORY_LIST_WIRE=ios_offline_wire(image, package, "INVENTORY.LIST"),
                         CUSTOM_GET_WIRE=ios_offline_wire(image, package, "CUSTOM.GET"),
                         POCKET_GET_WIRE=ios_offline_wire(image, package, "POCKET.GET"),
                         GLOBAL_NAME_WIRE=ios_offline_wire(image, package, "GLOBAL.GET.NAME"),
                         POCKET_MENU_WIRE=ios_offline_wire(image, package, "POCKET.GET", "7"),
                         GIFT_COUNT_WIRE=ios_offline_wire(image, package, "GIFT.GET.COUNT"),
                         RANKING_WIRE=ios_offline_wire(image, package, "SCORE.RANKING"))
    with tempfile.TemporaryDirectory(prefix="ios-state-arm-", dir=ROOT / "captures") as temp:
        source = Path(temp) / "offline.s"
        dest = Path(temp) / "offline.o"
        def build_once():
            code = template
            for name, value in substitutions.items():
                code = code.replace("@" + name + "@", value)
            if "@" in code:
                raise ValueError("Unfilled native assembly field")
            source.write_text(code, encoding="ascii")
            try:
                subprocess.run((str(trace.CLANG), "-target", "armv7-apple-ios6.0", "-c",
                                str(source), "-o", str(dest)),
                               check=True, capture_output=True, timeout=30)
            except subprocess.CalledProcessError as exc:
                # Do not expose generated assembly; it embeds private saved credentials.
                diagnostics = [
                    line.partition("error:")[0].split("offline.s:")[-1].strip()
                    + ": " + line.partition("error:")[2].strip()
                    for line in exc.stderr.decode("utf-8", "replace").splitlines()
                    if "error:" in line
                ]
                raise ValueError("ARM assembler errors: " + "; ".join(diagnostics)) from exc
            return object_text(dest.read_bytes(), asset_labels, bridge_labels | {
                label for label, _ in targets.values() if label not in ALL_LABELS
            })
        _, first = build_once()
        table = []
        for j in range(len(records)):
            for kind in ("service", "password"):
                offset = first[f"_save_{kind}_{j}"] - first["_save_table"]
                if offset <= 0:
                    raise ValueError("Save asset precedes native table")
                table.append(f"    .word {offset}")
        table.append("    .word 0")
        substitutions["SAVE_TABLE"] = "\n".join(table)
        menu_offsets = [first[f"_menu_name_{j}"] - first["_menu_table"]
                        for j in range(len(menu_names))]
        if any(offset <= 0 for offset in menu_offsets):
            raise ValueError("Menu API literal precedes numeric-only dispatch table")
        substitutions["MENU_TABLE"] = "\n".join(f"    .word {offset}" for offset in menu_offsets) + "\n    .word 0"
        for key, (label, target) in targets.items():
            if isinstance(target, str):
                target = CAVE_VM + first[target]
            delta = (target - CAVE_VM - first[label] - 4) & 0xFFFFFFFF
            substitutions[key + "_LO"] = str(delta & 0xFFFF)
            substitutions[key + "_HI"] = str(delta >> 16)
        text, labels = build_once()
    if labels != first or len(text) > 0x4800 or labels["_save_table"] >= len(text):
        raise ValueError("Native header padding overflow or unstable assembly labels")
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    instructions = list(decoder.disasm(text[:labels["_save_table"]], CAVE_VM))
    for label, target in targets.values():
        desired = target if isinstance(target, int) else CAVE_VM + labels[target]
        address = CAVE_VM + labels[label]
        prior = [item for item in instructions if item.address < address][-2:]
        insn = next((item for item in instructions if item.address == address), None)
        if insn is None or insn.mnemonic != "add" or not insn.op_str.endswith(", pc"):
            raise ValueError("Missing ASLR-safe native operand")
        reg = insn.op_str.split(",", 1)[0]
        if [item.mnemonic for item in prior] != ["movw", "movt"] or any(not item.op_str.startswith(reg + ", #") for item in prior):
            raise ValueError("Unverified native address operand")
        delta = int(prior[0].op_str.split("#", 1)[1], 0) | int(prior[1].op_str.split("#", 1)[1], 0) << 16
        if (delta + address + 4) & 0xFFFFFFFF != desired:
            raise ValueError("Native address fails ASLR rebasing")
    for command, label in (("SERVER.INIT", "_init_wire"), ("POCKET.LOGIN", "_login_wire"),
                           ("INVENTORY.LIST", "_inventory_wire"), ("CUSTOM.GET", "_custom_wire"),
                           ("POCKET.GET", "_pocket_wire"), ("GLOBAL.GET.NAME", "_global_wire")):
        wire = ios_offline_wire(image, package, command)
        # The original C++ receiver drops one leading ASCII frame byte before
        # passing the remainder to the Objective-C Base64/AES decryptor.
        payload = b"0" + wire.encode("ascii") + b"\0"
        if text[labels[label]:labels[label] + len(payload)] != payload:
            raise ValueError("Framed authenticated historical reply changed in native image")
    pointer = labels["_historical_reply_token"]
    if text[pointer:pointer + len(token) + 1] != token + b"\0":
        raise ValueError("Historical token literal differs from authenticated replies")
    pointer = labels["_historical_next_token"]
    if text[pointer:pointer + len(next_token) + 1] != next_token + b"\0":
        raise ValueError("Post-login token literal differs from authenticated login/inventory transition")
    for j, record in enumerate(records):
        for k, (kind, value) in enumerate((("service", record["service"]), ("password", record["password"]))):
            pointer = labels[f"_save_{kind}_{j}"]
            if struct.unpack_from("<I", text, labels["_save_table"] + 8 * j + 4 * k)[0] != pointer - labels["_save_table"]:
                raise ValueError("Historical Keychain asset offset mismatch")
            encoded = value.encode("ascii") + b"\0"
            if text[pointer:pointer + len(encoded)] != encoded:
                raise ValueError("Historical Keychain asset changed in native image")
    for j, name in enumerate(menu_names):
        pointer = labels[f"_menu_name_{j}"]
        if (struct.unpack_from("<I", text, labels["_menu_table"] + 4 * j)[0]
                != pointer - labels["_menu_table"] or
                text[pointer:pointer + len(name) + 1] != name.encode("ascii") + b"\0"):
            raise ValueError("Numeric-only menu API table changed")
    if struct.unpack_from("<I", text, labels["_menu_table"] + 4 * len(menu_names))[0] != 0:
        raise ValueError("Menu API table has no terminator")
    return text


def expected_executable(image: bytes, text: bytes) -> bytes:
    if image[ACCOUNT_VM - base.IMAGE_BASE:ACCOUNT_VM - base.IMAGE_BASE + len(OLD_ACCOUNT)] != OLD_ACCOUNT:
        raise ValueError("Unknown original iOS Keychain account")
    if any(image[CAVE_OFFSET:CAVE_OFFSET + 0x4800]):
        raise ValueError("Original Mach-O header padding is not empty")
    changed = bytearray(base.patched_executable(image))
    changed[ACCOUNT_VM - base.IMAGE_BASE:ACCOUNT_VM - base.IMAGE_BASE + len(OLD_ACCOUNT)] = OFFLINE_ACCOUNT
    changed[CAVE_OFFSET:CAVE_OFFSET + len(text)] = text
    for source, old, target in HOOKS:
        offset = source - base.IMAGE_BASE
        if image[offset:offset + 4] != old:
            raise ValueError("Original hook instruction differs")
        changed[offset:offset + 4] = trace.thumb_branch(source, target)
    return bytes(changed)


def verify(path: Path, binary: bytes):
    with zipfile.ZipFile(base.ORIGINAL) as original, zipfile.ZipFile(path) as candidate:
        if original.namelist() != candidate.namelist():
            raise ValueError("IPA members changed")
        for member in original.namelist():
            expected = binary if member == base.EXECUTABLE else original.read(member)
            if candidate.read(member) != expected:
                raise ValueError("IPA member differs from guarded offline build")
    print("Verified isolated historical Keychain + exact guarded read-only replies (not full offline gameplay):", path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    original = base.original_executable()
    package = private_package(original)
    text = assemble(original, package)
    binary = expected_executable(original, text)
    if args.verify:
        verify(args.verify, binary)
    else:
        with zipfile.ZipFile(base.ORIGINAL) as source, zipfile.ZipFile(args.build.open("xb"), "w") as dest:
            dest.comment = source.comment
            for member in source.infolist():
                dest.writestr(member, binary if member.filename == base.EXECUTABLE else source.read(member))
        verify(args.build, binary)


if __name__ == "__main__":
    main()
