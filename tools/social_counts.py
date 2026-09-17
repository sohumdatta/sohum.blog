#!/usr/bin/env python3
"""Emit data/social.json — {"/<path>/": {likes, comments}} from GitHub Discussions (giscus).
Runs in CI with GH_TOKEN/GITHUB_TOKEN; writes {} and exits quietly when it can't."""
import json, os, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "social.json"

def write(d):
    OUT.write_text(json.dumps(d, indent=1) + "\n")
    print(f"social: {len(d)} entries")

tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
repo = os.environ.get("GITHUB_REPOSITORY", "")
if not (tok and "/" in repo):
    write({}); raise SystemExit(0)

owner, name = repo.split("/", 1)
QUERY = """query($o:String!,$n:String!,$c:String){repository(owner:$o,name:$n){
 discussions(first:100,after:$c){pageInfo{hasNextPage endCursor}
 nodes{title reactions{totalCount} comments{totalCount}}}}}"""
data, cursor = {}, None
try:
    while True:
        body = json.dumps({"query": QUERY, "variables": {"o": owner, "n": name, "c": cursor}}).encode()
        req = urllib.request.Request("https://api.github.com/graphql", data=body,
            headers={"Authorization": f"bearer {tok}", "Content-Type": "application/json"})
        resp = json.load(urllib.request.urlopen(req, timeout=30))
        d = resp["data"]["repository"]["discussions"]
        for node in d["nodes"]:
            t = node["title"].strip().strip("/")
            if t:
                data[f"/{t}/"] = {"likes": node["reactions"]["totalCount"],
                                  "comments": node["comments"]["totalCount"]}
        if not d["pageInfo"]["hasNextPage"]:
            break
        cursor = d["pageInfo"]["endCursor"]
except Exception as e:  # counts are decoration; the build must not die for them
    print("social: skipped:", e)
write(data)
