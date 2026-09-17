# TESTING — bedrock probe suite

Every invariant this repo claims, as runnable probes. Re-run relevant tiers after any
ruleset/settings change, a PaperMod submodule bump, a Hugo version bump, or on suspicion.
For enforcement tiers, **PASS is a refusal** — the system demonstrating what it refuses
to allow is the receipt.

| tier | proves | residue | run when |
|---|---|---|---|
| 1 | unsigned commits refused | none | after any ruleset change |
| 2 | force-push + deletion refused; merge-commit-only PRs | one immortal `meta/` branch (first run only) | once, + after ruleset changes |
| 3 | every main-push timestamp-anchored, ancestry-bounded | none (read-only) | anytime; proofs mature over days |
| 4 | live site serves the design (crawlable, panels, giscus) | none; optional giscus loop leaves 1 discussion | after deploys/theme changes |
| 5 | diode gates 1–2–3 + browser decryptor | none (local only, discarded) | before first real dossier |
| 6 | a bare clone carries the whole verifiable record | /tmp clone | occasionally; also the third-party recipe |

---

## Tier 1 — signing enforcement (PASS = push refused, nothing lands)

```bash
git switch -c probe-unsigned
git commit --allow-empty --no-gpg-sign -m "probe: unsigned, must be refused"
git push origin probe-unsigned        # EXPECT: rejected, citing signed-commit verification
git switch main && git branch -D probe-unsigned
```

If it lands instead: ruleset Enforcement is not **Active**, or branch targeting misses
non-default branches. Fix, retract the branch if deletions still allowed, re-run.

## Tier 2 — force-push, deletion, merge buttons

First run creates one permanent witness branch (deletions being refused is the point):

```bash
git switch -c meta/enforcement-witness
git commit --allow-empty -m "witness: exists to prove the rules refuse"
git push origin meta/enforcement-witness           # lands (signed)
git commit --amend --no-edit
git push --force origin meta/enforcement-witness   # EXPECT: refused (force-push block)
git push origin --delete meta/enforcement-witness  # EXPECT: refused (restrict deletions)
git switch main && git branch -D meta/enforcement-witness
```

Re-runs: the branch already exists on the remote — fetch it, amend locally, repeat the
two EXPECT-refused pushes; create nothing new.

Merge-button check while it exists: open a PR from `meta/enforcement-witness`; the merge
button must offer **only** "Create a merge commit" (no squash, no rebase). Close unmerged.

## Tier 3 — OpenTimestamps pipeline (read-only)

```bash
pip install opentimestamps-client --user     # once
git pull --rebase origin main
ls proofs/                                   # one .txt/.ots pair per main-push
for f in proofs/*.ots; do echo "== $f"; ots verify "$f"; done
```

Both outcomes are valid states:
- `Pending confirmation in Bitcoin blockchain` — calendar attestation exists, anchor not
  yet mined/upgraded. Young proofs live here for hours-to-days. Not a failure.
- `Success! Bitcoin block N attests ...`
- Two proofs citing the SAME transaction is correct: calendars Merkle-aggregate many
  stamps into one on-chain anchor.
- PATH: `pipx ensurepath` APPENDS, which loses to `/usr/bin/ots` — prepend instead:
  `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc` — fully anchored (weekly upgrade job, or run
  Actions → bedrock-stamp → Run workflow to attempt an upgrade now).

Ancestry bound (the Merkle claim, executable) — one stamped tip bounds all history
beneath it:

```bash
SHA=$(basename proofs/*.txt .txt | tail -1)
git cat-file -t "$SHA"                                   # EXPECT: commit
git merge-base --is-ancestor <first-scaffold-sha> "$SHA" && echo BOUNDED
```

## Tier 4 — live-site invariants (read-only)

```bash
curl -sI https://sohum.blog | grep -i '^server'                    # server: GitHub.com
curl -sI http://sohum.blog | head -1                               # 301 (HTTPS enforced)
curl -s https://sohum.blog/robots.txt                              # permissive, no blanket Disallow
curl -s https://sohum.blog/sitemap.xml | grep -c '<loc>'           # > 0, and no /x/<opaque> entries
curl -s https://sohum.blog/index.xml | grep -o '<title>[^<]*'      # RSS carries posts only
curl -s https://sohum.blog | grep -o '[0-9]* commits'              # panels carry git metrics
curl -s https://sohum.blog/2026/03/07/hello-world/ | grep -c 'data-repo-id'   # giscus emitted
```

Optional live giscus loop (residue: one discussion + one reaction, deletable in the
Discussions tab): react on a post via the giscus box → Actions → deploy → Run workflow →
`curl -s https://sohum.blog | grep -o '[0-9]* likes'`.

## Tier 5 — diode rehearsal (entirely local; nothing enters the record)

```bash
python3 tools/freeze.py new rehearsal
printf '# Rehearsal\n\nsalt: 7c1f2e...\n\nSee [note](note.txt)\n' > _vault/rehearsal/index.md
echo "test artifact" > _vault/rehearsal/note.txt
python3 tools/freeze.py seal rehearsal --title "Rehearsal"
hugo server
```

In a browser, open the printed capability URL with the host swapped to
`localhost:1313` (secure context, so WebCrypto runs). EXPECT, in order:
1. hash-table rows flip to “✓ verified”; body renders; `note.txt` under Unsealed artifacts
2. `localhost:1313/` shows **no** rehearsal panel; `/index.xml` omits it; page source
   carries `noindex`
3. `python3 tools/reveal.py rehearsal` → rebuild → panel **appears**, provenance table present
4. `python3 tools/freeze.py seal rehearsal` → EXPECT: refused (revealed-entry guard)

Discard: `rm -rf content/x/<opaque> _vault/rehearsal` — then `git status` must show
nothing staged from any of it.

## Tier 6 — bare clone carries everything (also the third-party verification recipe)

```bash
cd /tmp && git clone --recurse-submodules git@github.com:sohumdatta/sohum.blog.git bedrock-check
cd bedrock-check && hugo --minify && python3 tools/gitmeta.py
for f in proofs/*.ots; do ots verify "$f"; done
```

Signature verification with zero trust in GitHub (any third party can do this from a
public clone, substituting the author's published key):

```bash
echo "<github-email> $(cat ~/.ssh/id_ed25519.pub)" > ~/.config/git/allowed_signers
git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
git log --show-signature -5          # EXPECT: Good "git" signature on post-baseline commits
```

Trustless chain, assembled: good signature (authorship) → merge-base ancestry (order) →
OTS Bitcoin anchor (upper time bound). No step consults GitHub.

---

## Known-untested until the first real dossier

- Sealed-bundle leak profile on the production CDN as actually served (search index,
  sitemap, RSS at sohum.blog rather than localhost)
- An OTS bound standing against a genuine external deadline
- A reveal's afterlife in the live record: panel, comments, counts on a real entry

Bootstrap seam, on the record: commits before `873fd21` ("chore: identity and signing
baseline") carry a hostname email and read Unverified; the verified era begins there.
Kept deliberately — genealogy over rewriting — and predates any frozen commitment.

---

## Run record

- **2026-09-17 — first full suite.** Tiers 1, 2, 4, 5, 6: PASS. Tier 3: PASS pending
  anchor — calendar attestations live on all proofs, two transactions broadcast and
  counting confirmations; terminal `Success!` awaits confirmations + a proof upgrade.
  Environment finding: `/usr/bin/ots` is an unrelated text summarizer (v0.4.2) shadowing
  the OTS client — fixed by PATH prepend; tier 3 guard added. Enforcement finding
  (pre-run): ruleset existed but sat **Disabled**; armed to Active, unsigned probe then
  refused. Identity finding: hostname email on pre-`873fd21` commits; baseline set,
  verified era begins there.
