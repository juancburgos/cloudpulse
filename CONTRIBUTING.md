# Contributing

Thanks for looking. This repository is primarily a portfolio/teaching artifact, so the bar for changes is:
**does it make the architecture easier to understand or more honest to operate?**

## Ways to contribute

- **Bug reports** — open an issue using the template. Include the exact `curl` you ran and the response.
- **Documentation fixes** — typos, broken links, unclear paragraphs. These are genuinely welcome; clarity is
  the point of the project.
- **Small, focused improvements** — anything on `docs/ROADMAP.md` marked "Now".
- **Questions** — open a discussion/issue; if the answer is generally useful it becomes documentation.

## What will likely be declined

- Adding layers, frameworks or services "because production systems have them" (see the out-of-scope list in
  `docs/ROADMAP.md`).
- Rewrites that trade readability for cleverness.
- Anything that adds a hard dependency on a specific cloud provider.

## Development setup

```bash
git clone https://github.com/USER/cloudpulse.git
cd cloudpulse
cp .env.example .env
make up        # api + db in Docker
make smoke     # verify /healthz
make test      # backend tests
```

Android:

```bash
cd android && ./gradlew assembleDebug       # JDK 17 + Android SDK 36
```

## Pull request checklist

- [ ] The change is described in the PR title/body **and why** it is needed.
- [ ] `make test` passes locally.
- [ ] `make lint` passes (formatting + import order).
- [ ] Documentation updated when behaviour, contract or operations change.
- [ ] If the change is an architecture decision, an ADR was added or amended in `docs/ADR/`.
- [ ] No secrets, no `.env`, no keystores, no build artifacts.
- [ ] The diff is focused — one concern per PR.

## Commit messages

Use conventional prefixes so the history reads as intent:

```
feat(api): expose database latency in /api/v1/status
fix(backend): bound database connect timeout to 3s
docs(adr): record why Caddy is the only public ingress
chore(ci): run pytest on pull requests
```

## Coding style

- **Python**: PEP 8, `ruff format` + `ruff check` (line length 100). Type hints on public functions.
- **Kotlin**: standard Android/Kotlin style, 4-space indentation, no wildcard imports.
- **SQL**: keywords uppercase, one clause per line, indexes named explicitly.
- **Docs**: Markdown, one sentence per line is fine, diagrams in Mermaid so they stay reviewable in diffs.

## License

By contributing you agree that your contribution is licensed under the MIT License of this repository.
