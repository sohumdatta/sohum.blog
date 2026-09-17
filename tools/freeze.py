#!/usr/bin/env python3
"""freeze.py — Gate 1 & 2 tooling for diode entries.

  python3 tools/freeze.py new  <slug>              create _vault/<slug>/ workdir (plaintext, gitignored)
  python3 tools/freeze.py seal <slug> [--title T]  encrypt vault -> content/x/<opaque>/, write stub + commitments

Vault layout (_vault/<slug>/ — NEVER committed; .gitignore covers it):
  index.md      the entry body (Markdown)          -> payload p00.enc, label "entry"
  <any files>   attachments (pdf/png/txt/...)      -> p01.enc, p02.enc, ... labels a-01, a-02, ...
  vault.json    key + opaque bundle name + labels  (created by `new`/first `seal`)

Sealed bundle (content/x/<opaque>/ — committed):
  index.md      public stub: diode front matter + frozen SHA-256 table + {{< diode >}}
  m.enc         encrypted manifest (real filenames live here, not in the clear)
  pNN.enc       12-byte IV || AES-256-GCM(ciphertext+tag), one key per entry

Requires: pip install cryptography
"""
import argparse, base64, datetime, hashlib, json, mimetypes, pathlib, secrets, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
VAULT = ROOT / "_vault"
XDIR = ROOT / "content" / "x"
BASEURL = "https://sohum.blog"

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    sys.exit("freeze.py needs the 'cryptography' package:  pip install cryptography")


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def enc(key: bytes, plaintext: bytes) -> bytes:
    iv = secrets.token_bytes(12)
    return iv + AESGCM(key).encrypt(iv, plaintext, None)


def load_vault(slug: str) -> pathlib.Path:
    v = VAULT / slug
    if not v.is_dir():
        sys.exit(f"no vault at {v} — run: python3 tools/freeze.py new {slug}")
    return v


def cmd_new(args):
    v = VAULT / args.slug
    if v.exists():
        sys.exit(f"{v} already exists")
    v.mkdir(parents=True)
    (v / "index.md").write_text(
        "Write the sealed entry here (Markdown).\n\n"
        "Link attachments by their real filename, e.g. ![plot](results.png)\n"
        "or [predictions](predictions.pdf) — the decryptor rewires them.\n"
    )
    meta = {"opaque": secrets.token_hex(8), "key": b64u(secrets.token_bytes(32)), "title": args.slug}
    (v / "vault.json").write_text(json.dumps(meta, indent=2))
    print(f"vault created: {v}")
    print("  1. write index.md, drop attachments alongside it")
    print(f"  2. seal:  python3 tools/freeze.py seal {args.slug} --title \"Public Title\"")


def cmd_seal(args):
    v = load_vault(args.slug)
    meta = json.loads((v / "vault.json").read_text())
    if args.title:
        meta["title"] = args.title
    key = base64.urlsafe_b64decode(meta["key"] + "==")
    bundle = XDIR / meta["opaque"]
    bundle.mkdir(parents=True, exist_ok=True)

    body = v / "index.md"
    if not body.is_file():
        sys.exit(f"{body} missing — the entry body is required")
    attachments = sorted(p for p in v.iterdir()
                         if p.is_file() and p.name not in ("index.md", "vault.json", "manifest.json"))

    files, frozen = [], []
    for i, src in enumerate([body] + attachments):
        pt = src.read_bytes()
        payload = f"p{i:02d}.enc"
        sha = hashlib.sha256(pt).hexdigest()
        label = "entry" if i == 0 else f"a-{i:02d}"
        (bundle / payload).write_bytes(enc(key, pt))
        files.append({"payload": payload, "name": src.name, "label": label, "sha256": sha,
                      "mime": mimetypes.guess_type(src.name)[0] or "application/octet-stream",
                      "body": i == 0})
        frozen.append({"payload": payload, "label": label, "sha256": sha})

    manifest = {"version": 1, "files": files}
    (bundle / "m.enc").write_bytes(enc(key, json.dumps(manifest).encode()))

    stub = bundle / "index.md"
    if stub.is_file() and "diode: false" in stub.read_text():
        sys.exit(f"{stub} is already revealed — re-sealing would clobber the published page. "
                 "Start a new entry instead.")
    keep = {}  # re-seal: preserve date and hand edits to tags / tldr / notice (inline form)
    if stub.is_file():
        for line in stub.read_text().splitlines():
            k = line.split(":", 1)[0]
            if k in ("date", "tags", "tldr", "notice"):
                keep[k] = line
    fm = ["---",
          f'title: "{meta["title"]}"',
          keep.get("date", f"date: {datetime.date.today().isoformat()}"),
          "diode: true",
          "searchHidden: true",
          "build:",
          "  list: never",
          "  render: always",
          keep.get("tags", "tags: []")]
    for k in ("tldr", "notice"):
        if k in keep:
            fm.append(keep[k])
    fm.append("frozen:")
    for f in frozen:
        fm += [f"  - payload: {f['payload']}",
               f"    label: {f['label']}",
               f"    sha256: {f['sha256']}"]
    fm += ["---", "", "{{< diode >}}", ""]
    stub.write_text("\n".join(fm))

    (v / "manifest.json").write_text(json.dumps(manifest, indent=2))
    meta["sealed"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    (v / "vault.json").write_text(json.dumps(meta, indent=2))

    print(f"sealed -> {bundle.relative_to(ROOT)}  ({len(files)} artifact(s))")
    print(f"capability URL (keep private):\n  {BASEURL}/x/{meta['opaque']}/#k={meta['key']}")
    print("next: git checkout -b proj/" + args.slug + " && git add content/x && git commit  (signed)")
    print("      open a PR and merge with the BUTTON — that GitHub-signed merge commit is the freeze event.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_new = sub.add_parser("new"); p_new.add_argument("slug"); p_new.set_defaults(fn=cmd_new)
    p_seal = sub.add_parser("seal"); p_seal.add_argument("slug"); p_seal.add_argument("--title", default=None)
    p_seal.set_defaults(fn=cmd_seal)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
