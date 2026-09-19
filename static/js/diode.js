/* diode.js — client-side unsealing for diode entries.
 *
 * Contract with tools/freeze.py:
 *   key      : 32 bytes, base64url (no padding), carried in the URL fragment as #k=<key>
 *   payloads : <bundle>/m.enc (manifest) and <bundle>/pNN.enc, each = 12-byte IV || AES-256-GCM ciphertext+tag
 *   manifest : JSON { version, files: [ { payload, name, label, sha256, mime, body } ] }
 *              exactly one entry has body:true — Markdown rendered as the post.
 *
 * The fragment is never transmitted: browsers do not send #… in requests, so no server,
 * log, or crawler sees the key. Decryption and verification happen entirely in-page.
 */
(function () {
  "use strict";

  var stateEl = document.getElementById("diode-state");
  var rootEl = document.getElementById("diode-root");
  var artEl = document.getElementById("diode-artifacts");
  if (!stateEl || !rootEl) return;

  function setState(msg) { stateEl.textContent = msg; }

  var m = (location.hash || "").match(/[#&]k=([A-Za-z0-9_-]+)/);
  if (!m) return; // sealed view: commitments table only — nothing else to do

  if (!(window.crypto && crypto.subtle)) {
    setState("This browser does not expose WebCrypto (needs HTTPS); the entry stays sealed.");
    return;
  }

  function b64urlToBytes(s) {
    s = s.replace(/-/g, "+").replace(/_/g, "/");
    while (s.length % 4) s += "=";
    var bin = atob(s), out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  function hex(buf) {
    var b = new Uint8Array(buf), s = "";
    for (var i = 0; i < b.length; i++) s += b[i].toString(16).padStart(2, "0");
    return s;
  }

  var keyBytes = b64urlToBytes(m[1]);
  if (keyBytes.length !== 32) { setState("Key in #k= is malformed (expected 32 bytes, base64url)."); return; }

  var base = location.pathname.endsWith("/") ? location.pathname : location.pathname + "/";

  function fetchPayload(name) {
    return fetch(base + name, { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(name + ": HTTP " + r.status);
      return r.arrayBuffer();
    });
  }

  function decrypt(key, buf) {
    var b = new Uint8Array(buf);
    if (b.length < 13) return Promise.reject(new Error("payload too short"));
    var iv = b.slice(0, 12), ct = b.slice(12);
    return crypto.subtle.decrypt({ name: "AES-GCM", iv: iv }, key, ct);
  }

  function markRow(payload, ok) {
    var row = document.querySelector('.diode-table tr[data-payload="' + payload + '"]');
    if (!row) return;
    var cell = row.querySelector(".diode-check");
    cell.textContent = ok ? "\u2713 verified" : "\u2717 HASH MISMATCH";
    cell.className = "diode-check " + (ok ? "diode-ok" : "diode-fail");
  }

  setState("Key present — unsealing in this browser\u2026");

  crypto.subtle.importKey("raw", keyBytes, "AES-GCM", false, ["decrypt"])
    .then(function (key) {
      return fetchPayload("m.enc")
        .then(function (buf) { return decrypt(key, buf); })
        .then(function (pt) { return JSON.parse(new TextDecoder().decode(pt)); })
        .then(function (manifest) {
          var files = manifest.files || [];
          return Promise.all(files.map(function (f) {
            return fetchPayload(f.payload)
              .then(function (buf) { return decrypt(key, buf); })
              .then(function (pt) {
                return crypto.subtle.digest("SHA-256", pt).then(function (d) {
                  var ok = hex(d) === String(f.sha256 || "").toLowerCase();
                  markRow(f.payload, ok);
                  return { f: f, bytes: pt, ok: ok };
                });
              });
          }));
        });
    })
    .then(function (items) {
      var urls = {};   // real filename -> blob URL, plus payload name -> blob URL
      var body = null, allOk = true;
      items.forEach(function (it) {
        allOk = allOk && it.ok;
        if (it.f.body) { body = it; return; }
        var blob = new Blob([it.bytes], { type: it.f.mime || "application/octet-stream" });
        var u = URL.createObjectURL(blob);
        urls[it.f.name] = u;
        urls[it.f.payload] = u;
      });

      if (body) {
        var md = new TextDecoder().decode(body.bytes);
        rootEl.innerHTML = window.marked ? marked.parse(md) : "<pre></pre>";
        if (!window.marked) rootEl.firstChild.textContent = md;
        // Point links and images at the decrypted artifacts.
        rootEl.querySelectorAll("a[href], img[src]").forEach(function (el) {
          var attr = el.tagName === "IMG" ? "src" : "href";
          var v = (el.getAttribute(attr) || "").replace(/^\.\//, "");
          if (urls[v]) el.setAttribute(attr, urls[v]);
          // no key-carry across /x/ links: every dossier has its own key by
          // construction, so carrying this page's key to another dossier can
          // only ever produce a wrong-key unseal failure on its stub
        });
      }

      var names = items.filter(function (it) { return !it.f.body; });
      if (names.length && artEl) {
        var h = document.createElement("h4"); h.textContent = "Unsealed artifacts";
        var ul = document.createElement("ul");
        names.forEach(function (it) {
          var li = document.createElement("li"), a = document.createElement("a");
          a.href = urls[it.f.name]; a.download = it.f.name;
          a.textContent = it.f.name + (it.f.label ? " (" + it.f.label + ")" : "");
          li.appendChild(a); ul.appendChild(li);
        });
        artEl.appendChild(h); artEl.appendChild(ul);
      }

      setState(allOk
        ? "Unsealed. Every artifact's SHA-256 matches the frozen commitment above."
        : "Unsealed, but at least one artifact FAILED verification against its frozen hash — treat this entry as tampered.");
    })
    .catch(function (e) {
      setState("Unsealing failed: " + (e && e.message ? e.message : e) +
        " — wrong key, missing payload, or corrupted ciphertext. The commitments above remain valid.");
    });
})();
