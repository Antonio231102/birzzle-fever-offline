# Birzzle Fever v7 level-8 Titanium checkpoint

Pulled from the Galaxy S4 on 2026-08-23 after interactive validation of v7.

## Tested state

- Multiple games and main-menu returns completed without ranking crashes or
  loading-animation softlocks.
- The v6 unlimited-lives behavior remained functional.
- Save progress was at level 8 when the game was closed and this backup was
  created.
- One transient post-game rollback from level 8 to the preceding level-7 state
  was observed; another game advanced the save to level 8 again.

## Files and SHA-256

- `com.halfbrick.birzzlefever-20260823-200708.properties`
  `effd1f50557d1fa4341edf3b408cee35babe529074c91d236b62308d21515264`
- `com.halfbrick.birzzlefever-20260823-200708.tar.gz`
  `ebba082dc8c316df00a859687ef3dfed3cb771fa648fd6b63076e4403c3919ad`
- `com.halfbrick.birzzlefever-ca286850d1b1afb7e3bee1b743bb841e.apk.gz`
  `9ce38272c544ebd6ec422b1952cf41c22e7be7a1a6190e8e2f159accdc5c0452`

The compressed APK expands to 37,919,980 bytes with SHA-256
`6d388c578094d85959661d192c3968195e1ac013f82d2fd9a6ceb99bfb15e6d5`,
an exact match for the signed v7 APK.
