# Pull request

## What and why

<!-- One paragraph: the change, and the problem it solves. Link the issue if there is one. -->

## Type of change

- [ ] Bug fix (no contract change)
- [ ] New capability (additive)
- [ ] Breaking change (requires `/api/v2` or a migration note)
- [ ] Documentation
- [ ] Infrastructure / deployment
- [ ] Android app (implies a new `versionCode` and a Play release)

## How it was verified

<!-- Commands you ran and what you saw. Evidence beats assurances. -->

```bash
make test
make lint
API_URL=https://api.example.com bash scripts/smoke-test.sh
```

- [ ] Unit tests pass locally
- [ ] Lint passes
- [ ] Smoke test passes against a deployment (production or local stack)
- [ ] Manually exercised the failure path (e.g. stopped a container) when relevant

## Checklist

- [ ] Documentation updated when behaviour, contract or operations changed
- [ ] An ADR was added/amended if this is an architecture decision
- [ ] `CHANGELOG.md` updated under *Unreleased*
- [ ] `versionCode` bumped if an Android artifact will be uploaded
- [ ] No secrets, `.env` files, keystores or build artifacts in the diff
- [ ] The diff is focused on one concern

## Notes for the reviewer

<!-- Trade-offs you accepted, alternatives you rejected, anything you are unsure about. -->
