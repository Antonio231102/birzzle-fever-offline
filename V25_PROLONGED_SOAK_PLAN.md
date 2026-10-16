# V25 Compact Cumulative Public-Release Qualification

> Historical V25 protocol. Current V42 functional results and their empirical evidence limits are recorded in [docs/TESTING.md](docs/TESTING.md). The current unlimited-hearts patch prevents the visible counter from decreasing, so this historical plan's displayed-zero-life condition is not applicable to V42. Do not infer this plan's action counts or checkpoint artifacts from the later manual reports.

## Purpose and cumulative evidence

This is a focused manual qualification of the exact V25 candidate, not a repetition of accepted matrices. The release decision combines this run with the existing exact-candidate evidence:

| Accepted evidence | Coverage credited to the release decision |
| --- | --- |
| Exact V25 fresh APK-only launch | Sanitized embedded save self-seeded without backup, root repair, Xposed, or a pre-existing ranking cache. |
| Exact V25 three-game fresh progression | Tutorial, level/reward, mission, bonus, pet upgrade, score, and pool growth worked together. |
| Exact V25 fresh-state cold restart | Ranking and progressed state survived process death. |
| Exact V25 mature-state launches | All 10 of 10 cold launches retained the mature pocket, inventory, pets, ranking, request zero, and consistent pool without fatal markers. |
| Exact V25 first-read fault matrix | All 9 of 9 accepted cases either loaded directly or entered the non-destructive controlled-wait path and recovered to the exact mature state after repair and cold launch. |

Those results remain release evidence and must be cited with this run. Do not uninstall, clear data, reconstruct a virgin state, inject faults, or repeat those accepted matrices here. This plan adds ordinary offline and connected gameplay, return-transition, mutation, unlimited-life, and final durability coverage.

The action counts below are operator-chosen focused regression coverage. No historical source is claimed to mandate them.

## Absolute user/orchestrator boundary

- **User only:** wake and unlock Android; enable or disable airplane mode; enable Wi-Fi; make every tap, swipe, Back press, menu choice, game action, power-up cancellation, reward claim, pet/booster selection or spend, leaderboard visit, and visual judgment.
- **Orchestrator only:** use ADB for connection and package metadata, log collection, Activity Manager launch, process inspection, force-stop, read-only snapshots, checkpoint capture, and comparison.
- The orchestrator never touches the physical display and never uses `adb shell input`, Monkey, UI Automator, accessibility automation, coordinates, key events, or text injection.
- The orchestrator never changes a network setting with ADB and never writes, restores, renames, changes ownership or mode of, or deletes app data. The capture script may remove only its own uniquely named remote temporary tar after a successful pull.
- Normal save mutations caused by the user's game actions are intended. They do not authorize orchestrator-side mutation.
- The user says **“hands off”** before any ADB operation during or after a user turn. The orchestrator says **“UI released”** after launch commands finish and then issues no ADB command until the user again says **“hands off.”**

A **successful game start** is counted only when an active playable board appears. Opening the app, visiting menus, canceling power-up selection, and the final inspection are not game starts.

## Qualification shape and labels

There are two gameplay process lifetimes followed by one non-gameplay cold restart:

| Label | Quiesced point |
| --- | --- |
| `00_baseline` | Before either gameplay session |
| `01_offline_session` | After the airplane-mode session |
| `02_connected_session` | After the Wi-Fi session |
| `03_final_cold_restart` | After final inspection, with no game or mutation in that process |

Each checkpoint must contain its schema-version-1 manifest, full app-data tar, pool report, profile report, generic-save report, and bounded log. Each comparison must be between adjacent labels. Evidence is immutable after capture.

## Preparation

Before the baseline, the orchestrator confirms:

1. `capture_v25_soak_checkpoint.py`, `compare_v25_soak_checkpoints.py`, `analyze_birzzle_save.py`, their invoked analyzers, the exact candidate `native-patches/v25-ranking-template/BirzzleFever-1.1.2-v25-ranking-template.apk`, and the selected `adb.exe` exist.
2. The local candidate and installed base APK both have SHA-256 `66006ed20a308d52660bea5154a513a64d07f4d7f8d725bd5f02077c70168b05`; record package version metadata and the corresponding accepted-evidence manifest. A mismatch stops the run.
3. `ADB_SERIAL` identifies the authorized device, the package is installed, root is available to the capture tool, power is stable, and local plus `/data/local/tmp` space is sufficient for four full checkpoints.
4. No backup, restore, cleaner, sync, package update, app-data tool, or other test runner will operate during this run.
5. The user can control airplane mode and Wi-Fi and understands every handoff and stop condition.
6. A new evidence root is used once and is never overwritten.

From the repository root in PowerShell:

```powershell
$Serial = $env:ADB_SERIAL
if (-not $Serial) { throw "Set ADB_SERIAL to the authorized test device." }
$Package = "com.halfbrick.birzzlefever"
$Adb = (Resolve-Path ".\platform-tools-latest-windows\platform-tools\adb.exe").Path
$RunId = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$EvidenceRoot = Join-Path (Resolve-Path ".").Path ("v25-soak-evidence\" + $RunId)
if (Test-Path $EvidenceRoot) { throw "Evidence root already exists; stop." }
New-Item -ItemType Directory -Path $EvidenceRoot | Out-Null
New-Item -ItemType Directory -Path "$EvidenceRoot\raw-logs" | Out-Null
New-Item -ItemType Directory -Path "$EvidenceRoot\comparisons" | Out-Null
New-Item -ItemType Directory -Path "$EvidenceRoot\operator-output" | Out-Null
$HistoricalUid = python -c "from analyze_birzzle_save import HISTORICAL_UID; print(HISTORICAL_UID)"
if ($LASTEXITCODE -ne 0 -or -not $HistoricalUid) { throw "Cannot import HISTORICAL_UID; stop." }
$ExpectedApkHash = "66006ed20a308d52660bea5154a513a64d07f4d7f8d725bd5f02077c70168b05"
$CandidateApk = (Resolve-Path ".\native-patches\v25-ranking-template\BirzzleFever-1.1.2-v25-ranking-template.apk").Path
$CandidateApkHash = (Get-FileHash -Algorithm SHA256 $CandidateApk).Hash.ToLowerInvariant()
if ($CandidateApkHash -ne $ExpectedApkHash) { throw "Local V25 candidate hash mismatch; stop." }

& $Adb -s $Serial get-state
$ApkPathLine = (& $Adb -s $Serial shell pm path $Package | Select-Object -First 1)
if (-not $ApkPathLine -or $ApkPathLine -notlike "package:*") { throw "Installed package path unavailable; stop." }
$InstalledApkPath = ($ApkPathLine -replace "^package:", "").Trim()
$InstalledApkSnapshot = "$EvidenceRoot\operator-output\installed-base.apk"
& $Adb -s $Serial pull $InstalledApkPath $InstalledApkSnapshot
if ($LASTEXITCODE -ne 0) { throw "Installed APK snapshot failed; stop." }
$InstalledApkHash = (Get-FileHash -Algorithm SHA256 $InstalledApkSnapshot).Hash.ToLowerInvariant()
if ($InstalledApkHash -ne $ExpectedApkHash) { throw "Installed V25 APK hash mismatch; stop." }
& $Adb -s $Serial shell dumpsys package $Package
& $Adb -s $Serial shell cmd package list packages -U $Package
& $Adb -s $Serial shell su -c id
& $Adb -s $Serial shell df /data/local/tmp
```

Retain preflight output in `operator-output`. Every command is a hard gate. The live Linux package UID is metadata and may differ from the historical response-filename UID. The scripts must continue importing `analyze_birzzle_save.HISTORICAL_UID`; never substitute the live UID or rewrite evidence to make the values agree.

## Universal gates

### Launch and handoff

With the user hands-off, the orchestrator runs:

```powershell
& $Adb -s $Serial logcat -c
& $Adb -s $Serial shell am start -W -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p $Package
if ($LASTEXITCODE -ne 0) { throw "Launch failed; stop." }
$Pid = (& $Adb -s $Serial shell pidof $Package).Trim()
if (-not $Pid) { throw "No package process; stop." }
```

A successful Activity Manager result and package PID are required. The orchestrator then says **“UI released”** and performs no ADB work during the user turn.

### Return observation

After every completed game, mid-game quit, or canceled power-up flow, the user verifies and records:

- the expected scene returned without a crash, ANR, freeze, softlock, stuck loading overlay, corrupt rendering, or unexpected first-run/tutorial reset;
- the main menu is responsive;
- displayed lives, coins, gems, EXP, level, current/high score, pet/booster selection, and quest/mission state;
- whether each value is unchanged or changed in the expected direction from the preceding observation;
- the leaderboard result when the turn requires it, including loading clearing, one own-score row, displayed own score, and normal return to the menu.

Any unexplained regression or duplicate/missing own-score presentation is a failure; numeric workload totals never override it.

### Quiesced checkpoint and adjacent comparison

At a session end:

1. User reaches the normal menu, records visible state, releases the device, and says **“hands off.”**
2. Orchestrator force-stops and checks that `pidof` is empty. If needed, force-stop once more; a remaining PID fails the run.
3. Orchestrator writes bounded logcat to the session's fixed `$LogFile`.
4. Orchestrator invokes the fixed-label capture command. The capture tool force-stops again immediately before its root tar.
5. Capture must exit zero. All artifacts and hashes must validate; analyzers must pass; the pool must be consistent, valid, monotonic, contiguous, and warning-free; fatal markers must be empty.
6. Orchestrator compares the immediately preceding manifest to the new manifest. It must exit zero and report `schema_version: 1`, `passed: true`, and empty `failures`.
7. No next launch or user action occurs until the comparison passes.

Every comparison must reconstruct or read checkpoint artifacts rather than trust summaries, verify checkpoint-relative artifact paths and hashes, preserve request zero and all pre-existing numbered records byte-for-byte, permit only contiguous valid additions, and independently confirm index and pool summary fields.

## Baseline checkpoint

No game launch precedes this capture:

```powershell
& $Adb -s $Serial logcat -c
& $Adb -s $Serial shell am force-stop $Package
& $Adb -s $Serial shell pidof $Package
$LogFile = "$EvidenceRoot\raw-logs\00_baseline.log"
& $Adb -s $Serial logcat -d -v threadtime | Set-Content -Encoding utf8 $LogFile
python .\capture_v25_soak_checkpoint.py --label 00_baseline --output-root "$EvidenceRoot" --serial "$Serial" --log-source "$LogFile"
if ($LASTEXITCODE -ne 0) { throw "Baseline capture failed; stop." }
$LastGoodLabel = "00_baseline"
```

The baseline must satisfy the universal capture requirements before the user changes network state.

## Session 1 — offline focused regression

### User setup

While the app remains stopped, the user enables airplane mode and confirms Wi-Fi is off, releases the device, and says **“hands off.”** The orchestrator does not toggle or certify network state with ADB; the user's recorded observation is authoritative. Launch through the universal gate.

### Turn-by-turn checklist

For each cancellation, the user opens the normal power-up-select flow, cancels or backs out, confirms the prior scene returns normally without starting a board, and records a cancellation return. For a completion, play through the result and return normally. For the quit, make at least one valid board action and use the game's own Back/quit/confirmation path.

| Turn | User action | Required checks after return |
| --- | --- | --- |
| O1 | Cancel power-up selection; then start and complete game 1. | Verify cancellation return, menu fields, responsive menu, leaderboard loads or shows a stable offline result, and normal leaderboard-to-menu return. |
| O2 | Cancel power-up selection; then start and complete game 2. | Repeat all menu and leaderboard checks; record own score and any expected score increase. |
| O3 | Cancel power-up selection; then start and complete game 3. | Repeat all menu and leaderboard checks; record progression changes without claiming or spending solely to create coverage. |
| O4 | Start game 4, make a valid action, then quit mid-game through the normal game flow. | Verify menu fields and refund/life behavior are coherent; open the leaderboard, record own score, and return normally. |

After O4, the offline ledger must show three successful completions, one mid-game quit, three distinct cancellation returns, and menu plus leaderboard verification after every gameplay return. It must also show local identity/profile continuity, no network-error lock, no startup or mid-tutorial reinitialization, no changed identity, and no reset/self-seed repetition.

The user then returns to the menu, records the session-end state, says **“hands off,”** and the orchestrator runs:

```powershell
& $Adb -s $Serial shell am force-stop $Package
& $Adb -s $Serial shell pidof $Package
$LogFile = "$EvidenceRoot\raw-logs\01_offline_session.log"
& $Adb -s $Serial logcat -d -v threadtime | Set-Content -Encoding utf8 $LogFile
python .\capture_v25_soak_checkpoint.py --label 01_offline_session --output-root "$EvidenceRoot" --serial "$Serial" --log-source "$LogFile"
if ($LASTEXITCODE -ne 0) { throw "Offline checkpoint failed; stop." }
python .\compare_v25_soak_checkpoints.py "$EvidenceRoot\00_baseline\manifest.json" "$EvidenceRoot\01_offline_session\manifest.json" --output "$EvidenceRoot\comparisons\00_baseline_to_01_offline_session.json"
if ($LASTEXITCODE -ne 0) { throw "Offline comparison failed; stop." }
$LastGoodLabel = "01_offline_session"
```

## Session 2 — connected focused regression

### User setup

Only after the offline comparison passes, the user disables airplane mode, enables Wi-Fi, waits until Android visibly reports the intended connection, releases the device, and says **“hands off.”** The orchestrator does not toggle network state. Launch through the universal gate.

### Rules throughout the session

- After every return, record the common menu fields and verify no regression.
- Open the leaderboard after every return, wait for loading to clear or a stable explicit network result, verify exactly one own-score presentation, record that score, and return normally. A later own score may increase but must not inexplicably decrease or disappear.
- Claim any enabled, earned level, quest, or mission reward encountered during these turns. Never buy with real money and never force an unavailable control.
- At the first safely available opportunity, perform and record one normal pet/booster/select/spend action using an already unlocked control and only earned in-game resources. A free selection counts. Do not make a risky purchase merely to satisfy the ledger.
- If a bonus game or Mystery Box is reached naturally, observe its entry, reward/result, return, and durable menu effect. Do not spend real money or add games to force either event. Record `not_naturally_reached` if absent.
- Record displayed lives after every return and immediately before every next start. Once zero is displayed, the next three scheduled starts must each reach an active playable board while the pre-start display remains zero. Keep their scheduled outcome. A blocked start, fewer than three remaining scheduled starts, or fewer than three successful post-zero starts fails qualification; do not add unscheduled games to hide the miss. If zero is never displayed, record all observed values and `zero_not_reached`; the conditional post-zero requirement is not triggered.

### Turn-by-turn checklist

| Turn | User action | Additional required observation |
| --- | --- | --- |
| C1 | Cancel power-up selection; then start and complete game 1. | Connected startup and first leaderboard/own-score return are normal. |
| C2 | Start and complete game 2. | Perform the first safely available pet/booster/select/spend action if available; otherwise inspect again after each later completion until one is safely available. |
| C3 | Cancel power-up selection; then start and complete game 3. | Claim any enabled earned level/quest/mission reward; record category and before/after values. |
| C4 | Start and complete game 4. | Verify prior reward/action state remains reflected in the menu and leaderboard return remains normal. |
| C5 | Start and complete game 5. | Inspect and claim any newly enabled earned level/quest/mission reward. |
| C6 | Start and complete game 6. | Verify coins, gems, EXP, level, score, pet/booster, quest, and mission values remain coherent. |
| C7 | Start and complete game 7. | Complete the final reward/action availability check and record any natural bonus/Mystery Box result. |
| C8 | Start game 8, make a valid action, then quit mid-game through the normal game flow. | Verify coherent refund/life behavior, final own-score leaderboard check, and normal menu return. |

After C8, the connected ledger must show seven successful completions, one mid-game quit, two distinct cancellation returns, repeated own-score leaderboard checks, every available earned level/quest/mission reward claimed, and one safely available pet/booster/select/spend action. If no such action was safely available despite checking after each completion, record every disabled/locked/unsafe state; missing required action coverage makes the run inconclusive rather than a pass.

The user returns to the menu, records all final connected values, says **“hands off,”** and the orchestrator runs:

```powershell
& $Adb -s $Serial shell am force-stop $Package
& $Adb -s $Serial shell pidof $Package
$LogFile = "$EvidenceRoot\raw-logs\02_connected_session.log"
& $Adb -s $Serial logcat -d -v threadtime | Set-Content -Encoding utf8 $LogFile
python .\capture_v25_soak_checkpoint.py --label 02_connected_session --output-root "$EvidenceRoot" --serial "$Serial" --log-source "$LogFile"
if ($LASTEXITCODE -ne 0) { throw "Connected checkpoint failed; stop." }
python .\compare_v25_soak_checkpoints.py "$EvidenceRoot\01_offline_session\manifest.json" "$EvidenceRoot\02_connected_session\manifest.json" --output "$EvidenceRoot\comparisons\01_offline_session_to_02_connected_session.json"
if ($LASTEXITCODE -ne 0) { throw "Connected comparison failed; stop." }
$LastGoodLabel = "02_connected_session"
```

## Final non-gameplay cold restart

Only after the connected comparison passes:

1. Orchestrator clears logcat, launches through the universal gate, and releases the UI.
2. User waits for loading to clear and verifies a normal, responsive menu with no crash, ANR, softlock, corrupt rendering, first-run flow, or tutorial reset.
3. User compares retained coins, gems, EXP, level, current/high score, pet/booster selection, and quest/mission state directly with the recorded connected-session end values.
4. User opens the leaderboard, waits for loading to clear or a stable explicit network result, verifies the expected single own-score presentation and score, returns normally, and samples each relevant menu for responsiveness.
5. User starts no game and claims, selects, upgrades, buys, or spends nothing. After returning to the menu, user records final values and says **“hands off.”**

The orchestrator then runs:

```powershell
& $Adb -s $Serial shell am force-stop $Package
& $Adb -s $Serial shell pidof $Package
$LogFile = "$EvidenceRoot\raw-logs\03_final_cold_restart.log"
& $Adb -s $Serial logcat -d -v threadtime | Set-Content -Encoding utf8 $LogFile
python .\capture_v25_soak_checkpoint.py --label 03_final_cold_restart --output-root "$EvidenceRoot" --serial "$Serial" --log-source "$LogFile"
if ($LASTEXITCODE -ne 0) { throw "Final checkpoint failed; stop." }
python .\compare_v25_soak_checkpoints.py "$EvidenceRoot\02_connected_session\manifest.json" "$EvidenceRoot\03_final_cold_restart\manifest.json" --output "$EvidenceRoot\comparisons\02_connected_session_to_03_final_cold_restart.json"
if ($LASTEXITCODE -ne 0) { throw "Final comparison failed; stop." }
$LastGoodLabel = "03_final_cold_restart"
```

Because the final process made no gameplay mutation, the final adjacent comparison must show no unexpected pool or profile change in addition to its normal invariant checks.

## Workload ledger

Record observed values, not assumptions. Use one row for every cancellation, successful start, return, leaderboard visit, reward/action, checkpoint, and comparison.

### Run and environment fields

- `run_id`, `evidence_root`, `started_at_utc`, `finished_at_utc`
- public test-device label/model/Android version (raw local manifest may retain the serial); package name/version/code; exact-candidate APK hash evidence
- ADB and Python versions; root identity; live package UID; imported historical response-filename UID
- prior evidence references for fresh self-seed, three-game progression, fresh cold restart, mature launches, and first-read faults

### Per-action fields

- `session`, `turn`, `action_sequence`, `started_at_utc`, `returned_at_utc`
- network state as reported by user; user/orchestrator handoff times
- cancellation attempted/returned; active board seen; outcome planned/actual; completion or normal quit confirmed
- lives before and after; whether zero was displayed; post-zero successful-start ordinal or blocking state
- coins, gems, EXP, level, current score, high score, pet/booster selection, quest state, mission state before and after
- reward/action type, enabled state, resource cost, and observed durable effect
- bonus/Mystery Box natural reachability and result
- leaderboard loading result, own-row count, own score, and return-to-menu result
- menu responsiveness, loading-cleared result, anomaly, factual user note, and pass/fail

### Checkpoint and comparison fields

- label, manifest path and SHA-256, capture time/exit, schema, artifact paths and SHA-256 values
- pool classification, index text/hash, last index, record counts, valid/contiguous/highest-valid values, request-zero hash, tail hash, semantic warnings
- profile/generic-save analyzer status, fatal markers, raw-log path, and retained console output
- adjacent before/after labels, comparison path/hash/exit, schema, `passed`, named checks, summaries, and failures

## Stop conditions and failure evidence

Stop on the first crash, native fatal signal, ANR, freeze, softlock, loading lock, corrupt display, unexpected first-run/reset state, changed identity, progression regression, pool inconsistency, or artifact hash change. Also stop on:

- unauthorized/wrong device, lost ADB/root, missing package, candidate mismatch, or a process that cannot be stopped;
- launch, log, tar, pull, capture, analyzer, or comparison failure;
- missing artifact, wrong schema, non-relative manifest artifact path, invalid hash, fatal marker, or semantic warning;
- invalid/noncontiguous record, index disagreement, changed request zero, changed/missing prior record, or non-monotonic pool;
- duplicate/missing own-score presentation, unexplained own-score regression, blocked required return, or required observation that cannot be made reliably;
- inability to finish the fixed action ledger or conditional zero-life starts without adding unscheduled work.

On a visible failure, the user immediately stops touching the device, says **“hands off—failure,”** and records the last visible scene and symptom. The orchestrator does not relaunch, retry gameplay, repair, restore, or resume. It performs one evidence-only attempt:

```powershell
& $Adb -s $Serial shell am force-stop $Package
& $Adb -s $Serial shell pidof $Package
$LogFile = "$EvidenceRoot\raw-logs\failure_state.log"
& $Adb -s $Serial logcat -d -v threadtime | Set-Content -Encoding utf8 $LogFile
python .\capture_v25_soak_checkpoint.py --label failure_state --output-root "$EvidenceRoot" --serial "$Serial" --log-source "$LogFile"
```

Retain the failure command output and record `$LASTEXITCODE`. If capture succeeds and a `$LastGoodLabel` manifest exists, run an evidence-only comparison without treating a pass as recovery:

```powershell
python .\compare_v25_soak_checkpoints.py "$EvidenceRoot\$LastGoodLabel\manifest.json" "$EvidenceRoot\failure_state\manifest.json" --output "$EvidenceRoot\comparisons\${LastGoodLabel}_to_failure_state.json"
```

If either evidence command fails, retain all output and the raw log; never mutate app data to improve the evidence. The qualification remains failed.

## Acceptance by patch area

| Patch area | This run must show | Cumulative evidence used instead of repetition |
| --- | --- | --- |
| Offline identity and self-seed route | Airplane-mode launch and all offline turns retain identity/profile, use coherent local state, avoid network-error/loading locks, and never repeat initialization or reset. | Exact V25 virgin APK-only self-seeding and three-game tutorial/progression already establish extraction and fresh initialization. |
| Ranking crash/softlock and return transitions | Every cancel, completion, quit, leaderboard visit, and menu return clears loading, stays responsive, presents one own-score row, and has no crash/ANR/softlock. | Exact fresh ranking cold restart and accepted mature launches establish cold-load behavior. |
| Progress durability and index integrity | Earned progress, reward claims, and the pet/booster/select/spend action survive returns and final cold restart; all adjacent comparisons preserve request zero/prior records and prove valid monotonic contiguous pool growth with matching hashes. | Accepted first-read and write/restart evidence covers destructive-reset triggers; this run adds ordinary cumulative mutations. |
| Unlimited lives | If zero appears, at least three subsequent scheduled starts reach playable boards while zero is displayed; none is heart-gated. If zero never appears, ledger proves it was checked before every start and the conditional criterion remains untriggered. | Existing unlimited-life patch composition is retained, but this run supplies the focused user-visible regression check when reachable. |
| Connected-network behavior | Wi-Fi session starts, progresses, ranks, returns, and saves without routing regression, duplicate callbacks, or loading lock; final connected cold restart remains healthy. | Offline exact-candidate evidence already proves defunct-server independence; the connected session checks that an available interface does not break the local route. |

## Final release decision

Mark this compact manual qualification `passed: true` only when:

1. both gameplay sessions complete their exact listed actions and observations;
2. every triggered zero-life requirement is met;
3. all four checkpoints pass capture/analyzer gates and all three adjacent comparisons pass with empty failures;
4. no crash, ANR, softlock, loading lock, identity change, progression regression, pool inconsistency, warning, fatal marker, or hash change occurred;
5. the final no-mutation cold restart retains coins, gems, EXP, level, score, pet/booster state, quests/missions, one own-score leaderboard presentation, and responsive menus; and
6. the accepted exact-V25 self-seed, fresh progression, ranking restart, mature-launch, and first-read-fault evidence remains applicable to the exact APK under decision.

The release record must state three independent dispositions: `prior_automated_evidence`, `compact_manual_qualification`, and `combined_release_decision`, each with evidence paths and factual failure reasons. The combined technical release qualification passes only when the prior evidence and this run both pass. A manual failure or inconclusive required action cannot be outvoted by earlier matrices, and numeric completion cannot override an integrity failure. Signing, legal-distribution, second-device, or other separately declared release gates remain independent and are not silently waived by this protocol.
