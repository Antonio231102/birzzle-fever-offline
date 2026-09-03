# Birzzle Identity Spoof

Minimal Xposed module for Birzzle Fever 1.1.2. It hooks every method named
`GetUniqueDeviceID` on `com.halfbrick.birzzlefever.BirzzleFever` and returns the
identity inferred from the restored tutorial filename:

`3c8bb7308c3fcb60c439224bd595c794d8f31501`

It does not request permissions, expose an activity, change the system Android
ID, or affect any other package.

Version 2 also makes the game's built-in connectivity layer report offline by
replacing `Network_IsReachable()` with `false` and `Network_GetState()` with
`0`. The hooks are scoped to the Birzzle Fever process.

After installing the APK, enable **Birzzle Identity Spoof** in Xposed Installer,
reboot, restore the sanitized Birzzle Fever Titanium Backup, and only then
launch the game.
