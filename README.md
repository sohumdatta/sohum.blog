# sohum.blog

The repository is the blog. Every entry, image, sealed dossier, timestamp proof, and this
file live in one signed, append-only history; the site at https://sohum.blog is a build of
`main`. The invariants — signed commits only, no force-pushes, no deletions, every push
OpenTimestamps-anchored — are enforced by repo rulesets, not discipline, and every claim
is probeable: see **TESTING.md**.

Diode entries pass through three gates:

| gate | state | mechanism |
|---|---|---|
| 1 | exists only in git | project branch; plaintext in `_vault/` (gitignored), only ciphertext committed |
| 2 | deployed dark | button-merge to `main` (GitHub-signed freeze event) publishes SHA-256 commitments; page at an opaque URL, unlisted, `noindex`, decrypts only via `#k=<key>` |
| 3 | revealed | `tools/reveal.py` publishes plaintext + key in place; the entry joins the homepage panels |

## Session rhythm

```
git pull --rebase origin main     # start here, always
```

The stamp bot advances `main` with proof commits after every push, so being behind is the
normal state, not drift. All work lands as signed commits (global git config handles it);
anything bound for `main` merges via the PR **button** — merge commits only, squash and
rebase are disabled because they'd collapse per-entry history and skip the GitHub-signed
merge commit.

## Writing a post

```
hugo new content/posts/<slug>/index.md      # a bundle: images live beside the text
# write → git switch -c proj/<slug> → commit → PR → button merge → panel appears
```

Front matter keys, all retroactively editable (edits are themselves on the record):
- `tags: [a, b]` — chips on the panel, `/tags/…/` pages
- `tldr: >-` — renders under the title and replaces the auto-excerpt on the panel
- `notice:` — override the site imprint with another string, or `false` to suppress
- `aliases: ["/old/path/"]` — keep superseded URLs resolving
- `slug:` — owns the `/YYYY/MM/DD/<slug>/` permalink; filename does not

Site-wide notice strings: `hugo.yaml → params.notice` (per-page imprint) and
`params.homeNotice` (homepage policy banner).

## Images

In the post's bundle, referenced by bare filename. Caption = the image *title* string;
layout = a fragment directive on the src:

```markdown
![alt](figure.jpg "*Markdown caption becomes a figcaption.*")
![Sohum](me.jpg#right)        # floats, text wraps; #left #center #wide also exist
```

Floats collapse to full-width on phones; `h2`/`h3` clear floats. Export at web resolution
(~1600px) **before** committing — history is append-only, every byte is permanent. Assets
shared across many pages go in `static/`; everything owned by one entry stays in its bundle.

## Diode entries

```
python3 tools/freeze.py new  <slug>                  # vault at _vault/<slug>/ (never committed)
# write index.md there, drop attachments alongside; salt short predictions inside the file
python3 tools/freeze.py seal <slug> --title "…"      # prints the capability URL — keep it private
git switch -c proj/<slug> && git add content/x && git commit
# PR → BUTTON merge  ← the GitHub-signed, OTS-stamped freeze event
...deadline passes...
python3 tools/reveal.py <slug>                       # or --opaque/--key without the vault
# branch → PR → button merge → panel appears; ciphertext, key.txt, proofs all remain
```

Re-sealing an already-revealed entry is refused by design. The fragment key never
transmits; anyone holding the URL can read and forward — disclosure control, not DRM.
Sealed pages render client-side (marked.js): captions there are hand-written italic
lines until reveal, when Hugo takes over.

## Comments, likes, subscribe

Comments and reactions live as GitHub Discussions (giscus) on this repo — widgets are
live on every non-diode page; panel like/comment counts are baked at build time and
refresh on the daily scheduled deploy. RSS at `/index.xml`.

## Map

```
tools/freeze.py, reveal.py        gates 1–3 (AES-256-GCM, key in URL fragment)
tools/gitmeta.py                  per-entry start / commits / last-modified → data/
tools/social_counts.py            Discussions → panel counts (CI)
static/js/diode.js (+marked)      in-browser unsealing + hash verification
layouts/_markup/                  render hooks: external links new-tab, image captions/floats
layouts/, assets/css/extended/    PaperMod overrides + custom styling
.github/workflows/deploy.yml      gitmeta → counts → hugo → Pages (daily cron)
.github/workflows/stamp.yml       OTS-stamp every main push; weekly proof upgrades
proofs/                           <sha>.txt + .ots — the anchored time bounds
TESTING.md                        the six-tier probe suite; run after any settings change
```

## Verification (the skeptic's chain, no trust in GitHub required)

`sha256sum` of a revealed file equals the hash in the earlier sealed page → that page's
merge commit is signature-verified (`git log --show-signature`, allowed-signers recipe in
TESTING.md tier 6) → `ots verify proofs/<sha>.txt.ots` bounds it, and all ancestry beneath
it, to a Bitcoin-anchored time. Bootstrap seam: commits before `873fd21` predate the
identity baseline and read Unverified — kept deliberately; the verified era starts there.

## Known edges

- Five theme files are overridden site-side (`list`, `single`, `baseof`, `rss`,
  `opengraph.html`) — re-diff after PaperMod submodule bumps; the last three exist only to
  silence upstream deprecations and can be deleted when upstream fixes them.
- `meta/enforcement-witness` is immortal by design (deletion-refusal witness, TESTING.md tier 2).
- Panel counts are as-of-last-build; giscus widgets are live.
- A sealed bundle's existence and timing are public — that's the pre-registration point.
- WordPress's remaining role: registrar for both domains; the frozen WP copy reverts to
  its subdomain when the plan lapses (Mar 2027).

---

*Supersedes the migration-era README (scaffold + WP cutover runbook, completed
2026-09-17). That text, like everything else here, remains in this file's git history.*
