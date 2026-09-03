# Mystery Box reward mechanics

## Observed test event

During the 11-game unclamped control, the first collected Mystery Box awarded **Booster Box**. The following game began with the additional booster-box effect, matching the game's English description:

> In your next game, start with a Booster Box already in play.

The reward is unrelated to the separately purchased 300-coin Booster Box power-up except that both influence the next game's booster-box setup.

## Reward IDs

`CMysteryBox::SelectRandomMysteryBoxBonus()` at `libbirzzle.so` virtual address `0x0F845C` returns one of 13 IDs. `CMysteryBoxOpenDialog::ActionOpenMysteryBox()` maps them to these localization keys and amounts:

| ID | Reward | Amount/effect |
|---:|---|---|
| 0 | Extra Time | Next game receives 10 additional seconds |
| 1 | Booster Box | Next game starts with an additional Booster Box in play |
| 2 | Super Bombs | Super Bombs appear regularly during the next game |
| 3 | Paint Bombs | Paint Bombs appear regularly during the next game |
| 4 | Bonus Bombs | Pairs of bombs appear regularly during the next game |
| 5 | Gems | Immediate +3 gems |
| 6 | Gems | Immediate +5 gems |
| 7 | Coins | Immediate +200 coins |
| 8 | Coins | Immediate +400 coins |
| 9 | Coins | Immediate +800 coins |
| 10 | Coins | Immediate +2,000 coins |
| 11 | XP multiplier | 5× XP in the next game |
| 12 | XP multiplier | 10× XP in the next game |

Sources:

- native selection function `0x0F845C`;
- dialog reward switch `0x085964`;
- `assets/Strings/Localization.plist`.

## Normal collected-box selection

For the ordinary in-game/story path, with no mutually exclusive pending reward, the outer weighted groups are:

| Group | Weight |
|---|---:|
| Bomb type: IDs 2–4 | 25 |
| Extra Time: ID 0 | 25 |
| Booster Box: ID 1 | 20 |
| Coins/gems: IDs 5–10 | `clamp(level - 10, 0, 10)` |
| XP multiplier: IDs 11–12 | 20 |

The denominator is the sum of currently eligible weights. The bomb, Extra Time, and Booster Box group is assigned zero weight if the corresponding one-game effect is already pending, preventing those effects from being selected twice before consumption.

At the control's starting level 7, the currency weight is zero. With no pending reward, the denominator is therefore 90 and the observed Booster Box reward has probability:

```text
20 / 90 = 2 / 9 ≈ 22.22%
```

Within the normal bomb group:

- Super Bombs: 2/7;
- Paint Bombs: 2/7;
- paired Bonus Bombs: 3/7.

Within the normal XP group:

- 5× XP: 3/4;
- 10× XP: 1/4.

When the currency group becomes eligible, its internal 20-way table is:

| Payout | Slots | Conditional probability |
|---|---:|---:|
| 200 coins | 10 | 50% |
| 400 coins | 5 | 25% |
| 800 coins | 2 | 10% |
| 2,000 coins | 1 | 5% |
| 3 gems | 1 | 5% |
| 5 gems | 1 | 5% |

These percentages are conditional on the currency group being selected; the group's outer probability is at most 10/(90+10) under the ordinary no-pending state.

## Shop selection mode

One shop-purchase call path invokes a second selection mode. With no pending effects, its outer weights are 25 bomb, 25 time, 5 booster, 5 currency, and 1 XP. Its bomb group chooses Super or Paint Bombs equally and does not choose paired Bonus Bombs. Its conditional currency table is:

- 200 coins: 7/20;
- 400 coins: 6/20;
- 800 coins: 3/20;
- 2,000 coins: 1/20;
- 3 gems: 2/20;
- 5 gems: 1/20.

The gem-shop path increments a counter for Mystery Boxes opened before the next game. `CMysteryBox::IsAbleBuyMysteryBox()` allows the purchase only while the counter is 0, 1, or 2, limiting the player to three paid openings whose bonuses can be stacked for one upcoming game. Starting that game resets the counter to zero, even if the player later aborts it. Story, daily-bonus, gift, and in-game collected-box paths pass the non-counting mode and therefore do not consume any of these three paid openings.

The static configuration contains:

```text
ItemUnlockLevelMysteryBox = 9
ItemPriceMysteryBox       = 1
MysteryBoxCreateRate      = 150
ItemPriceMultiply         = 300
```

The level-9 Mystery Box shop unlock observed after game 10 matches `ItemUnlockLevelMysteryBox`. `ItemPriceMultiply=300` matches the separately purchased Booster Box power-up. The Mystery Box price unit is inferred to be the shop's gem currency; the binary/config value itself is exactly 1.

## In-game creation rate

`CFortuneManager::IsMysteryBoxCreate(float)` at `0x0FD9CC` performs eligible spawn checks:

1. Mystery-box feature type 6 must be unlocked.
2. The base threshold is `MysteryBoxCreateRate=150` against `lrand48() % 1000`, or 15% per eligible check when no multiplier applies.
3. The supplied fortune/pet factor scales the threshold as `base + base × factor`.
4. A matching quest setting value 58 adds 50 threshold points, raising the base case from 15% to 20%.
5. Failed checks increment a streak counter. After ten random failures, the next eligible check is guaranteed and resets the counter.

“Eligible check” is important: the function is not called every frame. The exact board-generation events that invoke the fortune manager still control how often a 15% check occurs.

## Persistence and one-game consumption

`bonus.dat` contains a 32-byte decrypted image:

| Offset | Size | Meaning |
|---:|---:|---|
| `0x00` | 8 | `Birzzle\0` signature |
| `0x08` | 4 | save timestamp |
| `0x0C` | 1 | pending 10-second Extra Time |
| `0x0D` | 1 | pending starting Booster Box |
| `0x0E` | 1 | pending recurring Super Bombs |
| `0x0F` | 1 | pending recurring Paint Bombs |
| `0x10` | 1 | pending recurring paired bombs |
| `0x11` | 1 | pending 5× XP |
| `0x12` | 1 | pending 10× XP |
| `0x13–0x19` | 7 | reserved bytes copied with the reward structure |
| `0x1A–0x1B` | 2 | unwritten stack gap; ignored on load |
| `0x1C` | 4 | paid Mystery Boxes opened since the previous game start; range 0–3 |

At game initialization, `CClassicBirdManager::InitBirdManager()`:

1. copies the 14-byte pending-reward structure into the active bird manager;
2. calls `CMysteryBox::InitMysteryBoxBonusInfo(1)`;
3. clears the stored pending flags;
4. resets the paid-open counter to zero;
5. writes the cleared `bonus.dat` immediately.

The effects and paid-open limit are therefore consumed/reset when the next game initializes, not when that game completes. Aborting that game cannot recover the three shop openings. The final control snapshot correctly has every pending flag clear and a zero paid-open counter because the Booster Box reward was used by the following game.

The two-byte `0x1A–0x1B` field is not gameplay state. `SaveMysteryBoxBonusInfo()` never initializes it, explaining why those bytes differed between snapshots while every meaningful field remained zero. `decode_birzzle_profiles.py` now reports this gap separately instead of treating it as state.
