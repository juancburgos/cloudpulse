# Publishing to Google Play

This document records how the Android app is built, signed and released, and what the Play Console requires
from a **new personal developer account**. It is written down because the constraints — not the code — are what
usually surprise people.

## Artifacts

| Artifact | Command | Notes |
|---|---|---|
| Debug APK | `make android-debug` | Local testing on a device |
| Release AAB | `make bundle` | What Play accepts; signed with the upload key |
| Play signing | Managed by Google (Play App Signing enabled) | The upload key is **not** in this repository |

The upload keystore lives outside the repository (`play-package/keys/`, git-ignored). Losing it means asking
Google for an upload-key reset; losing the app-signing key is not possible because Google holds it.

## Versioning rules

- `versionCode` must increase with **every** artifact uploaded to Play — including across different tracks.
  Uploading the same `versionCode` twice fails with *"Version code N has already been used"*. This is the most
  common first-release mistake: the internal-testing bundle and the closed-testing bundle need different codes.
- `versionName` is the human-facing version (`1.0.0`) and may repeat.

## Release flow used here

1. **Internal testing** — immediate distribution to a small list (up to 100 testers). No review required to
   install, which makes it the fastest way to put a build in someone's hands.
2. **Closed testing (Alpha)** — the track Google's policy requires: this is where the 12-tester / 14-day rule
   applies for personal accounts.
3. **Production** — unlocked only after the closed test criterion is met and the production application is
   approved.

## The constraint that shapes the timeline (personal accounts)

For personal developer accounts created after 13 November 2023, Google requires, before granting production
access:

- a published **closed testing** release,
- **at least 12 testers opted-in** (testers must be real people; test accounts you create yourself are not a
  legitimate way to satisfy this),
- for **at least 14 continuous days**.

Consequences worth documenting, because they are not obvious:

| Question | Answer |
|---|---|
| Is there a deadline for each tester to accept? | No. The closed test does not expire; testers can join any time. |
| When does the 14-day counter run? | Only on days with ≥ 12 testers opted-in, and it must be continuous. Dropping below 12 stops or restarts the count. |
| What happens if fewer than 12 accept? | Production access simply stays locked. Nothing is penalised; the app remains distributable to testers. |
| Is there an alternative? | Yes: an **organisation** developer account (legal entity + D-U-N-S number) is exempt from the 12-tester requirement. |

Testers accept by opening `https://play.google.com/apps/testing/<applicationId>` with their own Google account
and tapping *Become a tester*. Installing afterwards is not what the counter measures, but Google reviews the
test for realism — recruiting real users who actually run the app is both the honest and the safe approach.

### A silent failure worth knowing about

A closed-testing release can read **"Available to selected testers"** while the track has **no testers at all**.
The Testers tab lets you switch between *Email lists* and *Google Groups*; both save independently, and the
switch is stored per track. If the track ends up on *Google Groups* with an empty field, the saved configuration
is "no testers", the release still looks healthy, and the 14-day counter never starts — the first symptom would
otherwise appear two weeks later as a production request that is refused.

The lesson generalises: after saving a track configuration, **reload the page and re-read the saved state**
rather than trusting the button you just pressed. Verify with the tester-facing artefact (the opt-in page must
say *You are a tester* for an address on the list), not with the console's own status text.

## Store listing assets

| Asset | Size | Source in this repo |
|---|---|---|
| App icon | 512×512 PNG | `screenshots/icon-512.png` |
| Feature graphic | 1024×500 PNG | `screenshots/feature-graphic-1024x500.png` |
| Phone screenshots | 1080×1920 (9:16) | `screenshots/screenshot-1.png`, `screenshot-2.png` |
| Privacy policy | public URL | `web/privacidad.html` served by Caddy |

Screenshots must respect the store's aspect-ratio rules (16:9 or 9:16); a 1080×2400 capture is rejected — the
captures here were regenerated at exactly 1080×1920 for that reason.

## Declarations completed for this app

Ads: none · Sign-in: none required · Content rating: IARC questionnaire (utility/tool, no descriptors) ·
Target audience: 13+ · Data safety: no data collected or shared · Advertising ID: not used · Government,
financial and health features: none.

## Checklist for the next release

- [ ] Bump `versionCode` (and `versionName` for a user-visible change)
- [ ] `make test` and `make smoke` against production
- [ ] `make bundle`
- [ ] Upload to **internal testing**, verify on a real device (install from the tester link)
- [ ] Promote the same bundle to **closed testing** and publish
- [ ] Update `CHANGELOG.md` and tag the release in git
