#!/usr/bin/env python3
"""reveal.py — Gate 3 for diode entries.

  python3 tools/reveal.py <slug>                        key read from _vault/<slug>/vault.json
  python3 tools/reveal.py --opaque <dir> --key <b64u>   vault-less recovery (key + repo suffice)

What it does, all inside the bundle content/x/<opaque>/:
  * decrypts m.enc + pNN.enc with the entry key and writes the plaintext files
    under their real names (ciphertext and manifest stay put — the record keeps both)
  * writes key.txt so anyone can re-derive plaintext from the historic ciphertext
  * rewrites index.md: drops the gate keys (_build / searchHidden), sets diode: false,
    appends the entry body + a provenance section; keeps the frozen table, date and tags
The next signed commit + button-merge publishes it, and the homepage panel appears
because the page simply rejoins the collections PaperMod lists.

Requires: pip install cryptography
"""
import argparse, base64, datetime, hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
VAULT = ROOT / "_vault"
XDIR = ROOT / "content" / "x"

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    sys.exit("reveal.py needs the 'cryptography' package:  pip install cryptography")


def dec(key: bytes, blob: bytes) -> bytes:
    return AESGCM(key).decrypt(blob[:12], blob[12:], None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--opaque"); ap.add_argument("--key")
    args = ap.parse_args()

    if args.slug:
        vj = VAULT / args.slug / "vault.json"
        if not vj.is_file():
            sys.exit(f"no vault.json at {vj}; use --opaque/--key instead")
        meta = json.loads(vj.read_text())
        opaque, key_b64 = meta["opaque"], meta["key"]
    elif args.opaque and args.key:
        opaque, key_b64 = args.opaque, args.key
    else:
        sys.exit("give a vault slug, or --opaque and --key")

    key = base64.urlsafe_b64decode(key_b64 + "==")
    bundle = XDIR / opaque
    if not bundle.is_dir():
        sys.exit(f"no bundle at {bundle}")

    manifest = json.loads(dec(key, (bundle / "m.enc").read_bytes()))
    body_md, prov = "", []
    for f in manifest["files"]:
        pt = dec(key, (bundle / f["payload"]).read_bytes())
        sha = hashlib.sha256(pt).hexdigest()
        status = "verified" if sha == f["sha256"] else "MISMATCH — do not publish"
        if f.get("body"):
            body_md = pt.decode()
            prov.append(f"| {f['label']} | this page's body | `{f['sha256']}` | {status} |")
        else:
            (bundle / f["name"]).write_bytes(pt)
            prov.append(f"| {f['label']} | [{f['name']}]({f['name']}) | `{f['sha256']}` | {status} |")
        print(f"{f['payload']} -> {f['name']}: {status}")

    (bundle / "key.txt").write_text(key_b64 + "\n")

    stub = bundle / "index.md"
    lines = stub.read_text().splitlines()
    out, i, in_build = [], 0, False
    assert lines[0] == "---"
    out.append("---")
    i = 1
    while i < len(lines) and lines[i] != "---":
        ln = lines[i]
        if ln.startswith("build:"):
            in_build = True
        elif in_build and ln.startswith("  "):
            pass
        elif ln.startswith("searchHidden:"):
            in_build = False
        elif ln.startswith("diode:"):
            in_build = False
            out.append("diode: false")
        else:
            in_build = False
            out.append(ln)
        i += 1
    out.append(f"revealed: {datetime.date.today().isoformat()}")
    out.append("---")
    out += ["", body_md.rstrip(), "", "---", "", "## Provenance", "",
            "This entry was frozen as an encrypted diode bundle and revealed on "
            f"{datetime.date.today().isoformat()}. The original ciphertext (`p*.enc`, `m.enc`), the "
            "entry key ([key.txt](key.txt)) and the OpenTimestamps proofs in `/proofs/` remain in the "
            "repository, so the freeze can be re-verified end to end: the GitHub-signed merge commit "
            "that published this page's SHA-256 commitments predates this reveal in the anchored history.",
            "", "| artifact | file | SHA-256 of plaintext | check |", "|---|---|---|---|"] + prov + [""]
    stub.write_text("\n".join(out))

    print(f"\nrevealed in place: {bundle.relative_to(ROOT)}")
    print("verify any artifact yourself:  sha256sum <file>")
    print("publish: commit (signed) on a branch, PR, merge with the button.")


if __name__ == "__main__":
    main()
