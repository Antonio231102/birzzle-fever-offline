# TitaniumBackup Automated Android Testing Framework (Package: com.halfbrick.birzzlefever)

## Token Preservation & Context Management
- **Aggressive Token Shaking:** To maintain maximum cache efficiency and prevent credit drain, you MUST strictly limit verbal descriptions, introductory remarks, and formatting explanations. Provide raw diagnostics or direct architectural code immediately.
- **Log Sanitation Rule:** Analyze ADB logcat dumps by focusing exclusively on the `com.halfbrick.birzzlefever` process boundary, stack traces, Android Runtime (ART) exceptions, and severe runtime failures (`*:E`). Filter out system-level backgrounds (e.g., scan loops, system garbage collection) before token analysis.
- **Context Preservation:** Only suggest, remind, or request the `/shake` command at the absolute end of the entire multi-step workflow, once all scripts have finished executing and final diagnostic results are fully displayed to the user. Do not inject this reminder during intermediate tool executions.

## Manual Test Orchestration Protocol
- **Synchronization Anchor:** You are strictly forbidden from acting on hypothetical bug assumptions or scanning files blindly during testing phases. You must operate as a gatekeeper for the physical testing loop.
- **Pre-Flight Notification (Step 1):** Before any log capture or analysis takes place, you must print a clean, clear visual alert to the terminal stating exactly what component is being tested and what behavioral signals to watch for on the screen.
- **Explicit Gating (Step 2):** You MUST stop execution entirely and output the verbatim prompt: `"Please prepare the Android device. Let me know when you are ready to begin the manual test."` Do not execute any tool calls, compile scripts, or trigger background actions until the user inputs an explicit confirmation phrase (e.g., "ready", "go", "start").

## Automation Tooling Execution
- **Automated Bootstrap Sequence (Step 3):** Once the user explicitly signals they are ready, you must immediately and automatically fire the local automated script to launch the targeted application state with clean debugging logs.
- **Tool Trigger:** You must execute the following PowerShell command in the terminal to clear old buffers and launch the specific package workspace:
  ```powershell
  adb logcat -c; adb logcat -b crash -c; adb shell monkey -p com.halfbrick.birzzlefever -c android.intent.category.LAUNCHER 1
  ```
- **Post-Execution Capture:** After triggering the application launch, instruct the user to replicate the manual bug step empirically on the device, wait for the runtime failure, and let you know when the process crashes or concludes so you can read the compiled `.\.omp\current_test_log.txt` buffer.