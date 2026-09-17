# sohum.blog — git-driven, bedrock-first

Hugo + PaperMod on GitHub Pages. The repository is the record: every entry's history is
signed, timestamp-anchored, and public. Diode entries pass through three gates:

| gate | state | mechanism |
|---|---|---|
| 1 | exists only in git | project branch; plaintext lives in `_vault/` (gitignored), only ciphertext is committed |
| 2 | deployed dark | button-merge to `main` → GitHub-signed merge commit publishes the SHA-256 commitments; page renders at an opaque URL, excluded from homepage/RSS/sitemap/search, `noindex`; content decrypts only via `#k=<key>` in the URL fragment |
| 3 | revealed | `tools/reveal.py` publishes plaintext + key in place; the entry rejoins the collections and its homepage panel appears |

Bedrock invariants, enforced structurally: a ruleset refuses unsigned pushes on all
branches; force-pushes and deletions are blocked; every push to `main` is stamped with
OpenTimestamps (free — calendars pay the Bitcoin anchoring), and the proofs are committed
back **via the GitHub API so the bot's commits are GitHub-signed** and pass the ruleset.

---

## One-time setup

**Prerequisites (local):** git, Hugo ≥ 0.166 extended, Python 3, `pip install cryptography`.

1. **Init and sign.** GitInfo reads history, so init before the first build:
   ```
   git init -b main && git config gpg.format ssh
   git config user.signingkey ~/.ssh/id_ed25519.pub && git config commit.gpgsign true
   git add -A && git commit -m "scaffold"
   ```
   Upload the same SSH key to GitHub as a **signing key** (Settings → SSH and GPG keys →
   New SSH key → key type: *Signing Key*) so your commits show Verified.

2. **Theme submodule, first build.**
   ```
   git submodule add https://github.com/adityatelange/hugo-PaperMod themes/PaperMod
   git commit -m "theme: PaperMod (submodule)" && hugo server
   ```

3. **Port the WordPress content.** WP Admin → Tools → Export → download the XML. Commit the
   raw XML (`import/wp-export.xml`) as its own commit — the genealogy then provably starts
   from the pre-migration state. Paste the post body into `content/posts/hello-world.md`
   and the two pages (`about.md`, `on-speaking-to-llms.md`). All three URLs are preserved.

4. **Create the GitHub repo and push.** Then, in the repo settings — these are the
   non-negotiables, and only you can click them:
   - **Pages** → Source: *GitHub Actions*.
   - **Rules → Rulesets → New branch ruleset**: target *All branches*; enable
     *Require signed commits*, *Block force pushes*, *Restrict deletions*.
   - **General → Pull Requests**: uncheck *Allow squash merging* and *Allow rebase merging*
     (squash would collapse per-entry commit counts; button merges must be true merge
     commits — those are the GitHub-signed freeze events).
   - **General → Features**: enable *Discussions*.

5. **Comments/likes (giscus).** Install the giscus app on the repo
   (github.com/apps/giscus), then at giscus.app pick repo + category *Comments* (Announcements
   type) and copy `repoId`/`categoryId` into `hugo.yaml → params.giscus`. Counts appear on
   panels after the next build; the daily scheduled build keeps them fresh.

6. **Domain cutover** (order matters): verify `sohum.blog` under Settings → Pages *first*
   (TXT record), confirm the site on `<you>.github.io`, then at the DNS host replace
   WordPress.com's records with GitHub Pages' four apex A records + `www` CNAME, add the
   custom domain, wait for the cert, enforce HTTPS. Only then downgrade the WP.com plan
   (keep the domain registration).

## Daily use

**Normal post:** `hugo new content/posts/my-title.md` → write → commit on a branch → PR →
merge with the button. Panel appears; permalink is `/YYYY/MM/DD/slug/`.

**Diode entry:**
```
python3 tools/freeze.py new  pdn-prereg          # makes _vault/pdn-prereg/
# write _vault/pdn-prereg/index.md, drop attachments (pdf/png/…) alongside
python3 tools/freeze.py seal pdn-prereg --title "Dossier: PDN pre-registration"
git checkout -b proj/pdn-prereg && git add content/x && git commit -m "seal: pdn-prereg"
# PR → merge with the BUTTON  ← the GitHub-signed freeze event
```
The seal step prints the capability URL (`…/x/<opaque>/#k=<key>`). The fragment never
leaves the browser. Share it, or don't. Re-running `seal` re-encrypts after edits
(same key, same URL) — do that only *before* the freeze you care about.

**Hygiene for short predictions:** a one-line claim is brute-forceable from its hash, so
put a random salt line inside the file (see the vault template). Big artifacts don't need it.

**Reveal (after the deadline passes):**
```
python3 tools/reveal.py pdn-prereg     # or --opaque <dir> --key <b64u> without the vault
git checkout -b reveal/pdn-prereg && git add content/x && git commit -m "reveal: pdn-prereg"
# PR → button merge → homepage panel appears
```
Ciphertext, key, and proofs all stay in the tree, so the freeze re-verifies forever.

**Notice & TL;DR (after the title, as on the WP site):** the originality notice is
site-wide (`hugo.yaml → params.notice`); override per page with its own string or suppress
with `notice: false`. Add `tldr: "…"` to any entry's front matter — it renders under the
title and replaces the auto-excerpt on its homepage panel. Both survive diode re-seals
and reveals.

**Retroactive tags:** edit `tags: […]` in any entry's front matter and commit — chips and
`/tags/…/` pages update, and the edit itself is on the record.

## What a skeptical reader can check

1. `sha256sum <revealed file>` equals the hash rendered by the sealed page's earlier commit.
2. That commit is a GitHub-signed button merge (`git log --show-signature`).
3. `ots verify proofs/<tip>.txt.ots` bounds that commit — and, via Merkle ancestry, everything
   beneath it — to a Bitcoin-anchored time. No trust in the author's clock, or in GitHub.

## Map

```
tools/freeze.py, reveal.py     gates 1–3 (AES-256-GCM, key in fragment, cryptography lib)
tools/gitmeta.py               start / commit-count / last-modified per entry → data/gitmeta.json
tools/social_counts.py         likes & comment counts from Discussions → data/social.json (CI)
static/js/diode.js (+marked)   in-browser unsealing + per-artifact hash verification
layouts/…                      PaperMod overrides: metrics meta row, tag chips, giscus, noindex
.github/workflows/deploy.yml   gitmeta → social → hugo → Pages (daily cron refreshes counts)
.github/workflows/stamp.yml    OTS-stamp each main push; weekly upgrade; API commits (GitHub-signed)
```

## Known edges

- The capability URL is exactly that: anyone holding it can read and forward. Disclosure
  control, not DRM. Existence + timing of sealed bundles is public (that's the point).
- `layouts/list.html` is a patched copy of PaperMod's (tag chips) — re-diff it after theme updates.
- Panel like/comment counts are as-of-last-build; giscus widgets on the entry pages are live.
- Verified by build-testing: seal → deploy-dark → decrypt (WebCrypto) → reveal → panel +
  metrics + tags, with zero leakage into homepage/RSS/sitemap/search. Not testable outside
  GitHub: the two workflows end-to-end (OTS calendars, Discussions API) — review their logs
  on first run.
