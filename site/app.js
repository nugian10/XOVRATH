/* XOVRATH — shared site logic.
   Reads collection data at runtime. Nothing about supply, counts or
   artwork is hard-coded here beyond the known collection size (2,222)
   and the six classifications. If the collection files are not there
   yet, the site shows honest "not yet published" states. */

(function () {
  "use strict";
  const CFG = window.XOVRATH_CONFIG;
  const $ = (sel, el) => (el || document).querySelector(sel);
  const $$ = (sel, el) => Array.from((el || document).querySelectorAll(sel));

  const pad = (n) => String(n).padStart(3, "0");
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[c]);

  /* ---------- nav active state ---------- */
  const page = (location.pathname.split("/").pop() || "index.html").split("?")[0];
  $$(".nav-links a").forEach((a) => {
    const href = a.getAttribute("href");
    if (href === page || (page === "" && href === "index.html") || (page === "index.html" && href === "index.html")) {
      a.classList.add("active");
    }
  });

  /* ---------- contract status line ---------- */
  $$(".js-contract-status").forEach((el) => {
    if (CFG.CONTRACT_ADDRESS) {
      el.innerHTML = '<span class="dot"></span><span>MINT IS LIVE — ' + esc(CFG.CONTRACT_ADDRESS) + "</span>";
    } else {
      el.innerHTML = '<span class="dot"></span><span>CONTRACT NOT DEPLOYED YET — MINTING OPENS AFTER DEPLOY</span>';
    }
  });
  $$(".js-contract-address").forEach((el) => {
    el.textContent = CFG.CONTRACT_ADDRESS || "Not deployed yet — no contract address exists.";
  });

  /* ---------- data loading ---------- */
  let collectionCache = null;
  let tokensCache = null;

  async function fetchJSON(url) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
  }

  async function loadCollection() {
    if (collectionCache !== undefined && collectionCache !== null) return collectionCache;
    collectionCache = await fetchJSON(CFG.COLLECTION_JSON);
    return collectionCache;
  }

  // Returns an array of {id, classification, background, accent, form, elements}
  // for every token 1..TOTAL_SUPPLY. Uses all-tokens.json when present;
  // otherwise synthesises placeholder slots so the archive still lists
  // all 2,222 slots honestly as "artwork pending".
  async function loadTokens() {
    if (tokensCache) return tokensCache;
    const data = await fetchJSON(CFG.ALL_TOKENS_JSON);
    const byId = {};
    if (Array.isArray(data)) {
      data.forEach((t) => { if (t && t.id != null) byId[Number(t.id)] = t; });
    }
    const tokens = [];
    for (let i = 1; i <= CFG.TOTAL_SUPPLY; i++) {
      const t = byId[i];
      tokens.push({
        id: i,
        classification: t && t.classification ? t.classification : null,
        background: t && t.background ? t.background : null,
        accent: t && t.accent ? t.accent : null,
        form: t && t.form ? t.form : null,
        elements: t && t.elements ? t.elements : null,
        known: Boolean(t),
      });
    }
    tokensCache = tokens;
    return tokens;
  }

  function classificationCounts(tokens) {
    const counts = {};
    CFG.CLASSIFICATIONS.forEach((c) => { counts[c] = 0; });
    tokens.forEach((t) => { if (t.classification && counts[t.classification] != null) counts[t.classification]++; });
    return counts;
  }

  /* ---------- home stats ---------- */
  async function initStats() {
    const host = $("#stats");
    if (!host) return;
    const col = await loadCollection();
    const tokens = await loadTokens();
    const known = tokens.filter((t) => t.known).length;
    const counts = classificationCounts(tokens);
    const classCount = CFG.CLASSIFICATIONS.filter((c) => counts[c] > 0).length || CFG.CLASSIFICATIONS.length;

    const total = (col && (col.totalSupply || col.total || col.maxSupply)) || CFG.TOTAL_SUPPLY;
    const set = (key, val) => {
      const el = host.querySelector('[data-stat="' + key + '"]');
      if (el) el.textContent = val;
    };
    set("total", Number(total).toLocaleString("en-US"));
    set("classifications", String(classCount));
    set("published", known > 0 ? Number(known).toLocaleString("en-US") : "—");
    set("supply", "0");
    const note = $("#stats-note");
    if (note) {
      note.textContent = known === 0
        ? "Collection artwork has not been published yet. Counts update here automatically once the collection files land."
        : known < CFG.TOTAL_SUPPLY
          ? known.toLocaleString("en-US") + " of " + CFG.TOTAL_SUPPLY.toLocaleString("en-US") + " artworks published so far."
          : "All " + CFG.TOTAL_SUPPLY.toLocaleString("en-US") + " artworks published.";
    }
  }

  /* ---------- featured artworks (home) ---------- */
  function initFeatured() {
    const host = $("#featured");
    if (!host) return;
    const ids = [1, 42, 87, 126, 203, 318];
    loadTokens().then((tokens) => {
      const byId = {};
      tokens.forEach((t) => { byId[t.id] = t; });
      host.innerHTML = ids.map((id) => cardHTML(byId[id] || { id: id, known: false })).join("");
      bindArtFallbacks(host);
    });
  }

  /* ---------- card markup ---------- */
  function cardHTML(t) {
    const cls = t.classification || "UNKNOWN";
    const clsClass = t.classification ? "" : " purple";
    return (
      '<a class="card" href="archive.html?id=' + t.id + '">' +
        '<span class="art">' +
          '<img src="' + esc(CFG.IMAGE_PATH(t.id)) + '" alt="XOVRATH #' + pad(t.id) + '" loading="lazy" data-token="' + t.id + '">' +
        "</span>" +
        '<span class="meta">' +
          '<span class="id">#' + pad(t.id) + "</span>" +
          '<span class="cls' + clsClass + '">' + esc(cls) + "</span>" +
        "</span>" +
      "</a>"
    );
  }

  // If an artwork file is missing, replace the broken image with a
  // quiet placeholder instead of a broken-image icon.
  function bindArtFallbacks(root) {
    $$("img[data-token]", root).forEach((img) => {
      img.addEventListener("error", () => {
        const art = img.closest(".art");
        if (art) {
          art.innerHTML = '<span class="pending">XOVRATH<br>#' + pad(img.getAttribute("data-token")) + "<br>ARTWORK PENDING</span>";
        }
      }, { once: true });
      if (img.complete && img.naturalWidth === 0) {
        img.dispatchEvent(new Event("error"));
      }
    });
  }

  /* ---------- explore: paginated gallery ---------- */
  const PAGE_SIZE = 48;
  let exploreTokens = [];
  let explorePage = 1;

  function renderExplorePage() {
    const host = $("#explore-grid");
    if (!host) return;
    const start = (explorePage - 1) * PAGE_SIZE;
    const slice = exploreTokens.slice(start, start + PAGE_SIZE);
    host.innerHTML = slice.map(cardHTML).join("");
    bindArtFallbacks(host);
    const totalPages = Math.max(1, Math.ceil(exploreTokens.length / PAGE_SIZE));
    const count = $("#explore-count");
    if (count) {
      count.textContent = "PAGE " + explorePage + " / " + totalPages + " — SHOWING " +
        (slice.length ? start + 1 : 0) + "–" + Math.min(start + PAGE_SIZE, exploreTokens.length) +
        " OF " + exploreTokens.length.toLocaleString("en-US");
    }
    const prev = $("#explore-prev"), next = $("#explore-next");
    if (prev) prev.disabled = explorePage <= 1;
    if (next) next.disabled = explorePage >= totalPages;
    if (prev) prev.style.opacity = explorePage <= 1 ? 0.35 : 1;
    if (next) next.style.opacity = explorePage >= totalPages ? 0.35 : 1;
  }

  function initExplore() {
    const host = $("#explore-grid");
    if (!host) return;
    loadTokens().then((tokens) => {
      exploreTokens = tokens;
      explorePage = 1;
      renderExplorePage();
      const prev = $("#explore-prev"), next = $("#explore-next");
      if (prev) prev.addEventListener("click", () => { if (explorePage > 1) { explorePage--; renderExplorePage(); window.scrollTo({ top: 0, behavior: "smooth" }); } });
      if (next) next.addEventListener("click", () => {
        const totalPages = Math.ceil(exploreTokens.length / PAGE_SIZE);
        if (explorePage < totalPages) { explorePage++; renderExplorePage(); window.scrollTo({ top: 0, behavior: "smooth" }); }
      });
    });
  }

  /* ---------- archive: filters + detail ---------- */
  let archiveTokens = [];

  function renderArchive(list) {
    const host = $("#archive-grid");
    if (!host) return;
    const count = $("#archive-count");
    if (count) count.textContent = list.length.toLocaleString("en-US") + " ARTIFACT" + (list.length === 1 ? "" : "S");
    if (list.length === 0) {
      host.innerHTML = '<div class="empty">NO ARTIFACTS MATCH THESE FILTERS.<br>TRY CLEARING A FILTER.</div>';
      return;
    }
    // Render in chunks so 2,222 cards do not block the page.
    host.innerHTML = "";
    const CHUNK = 200;
    let i = 0;
    (function chunk() {
      const slice = list.slice(i, i + CHUNK);
      host.insertAdjacentHTML("beforeend", slice.map(archiveCardHTML).join(""));
      bindArtFallbacks(host);
      i += CHUNK;
      if (i < list.length) setTimeout(chunk, 0);
    })();
  }

  function archiveCardHTML(t) {
    const cls = t.classification || "UNKNOWN";
    const clsClass = t.classification ? "" : " purple";
    return (
      '<a class="card" href="archive.html?id=' + t.id + '">' +
        '<span class="art">' +
          '<img src="' + esc(CFG.IMAGE_PATH(t.id)) + '" alt="XOVRATH #' + pad(t.id) + '" loading="lazy" data-token="' + t.id + '">' +
        "</span>" +
        '<span class="meta">' +
          '<span class="id">#' + pad(t.id) + "</span>" +
          '<span class="cls' + clsClass + '">' + esc(cls) + "</span>" +
        "</span>" +
        '<span class="meta" style="border-top:0;padding-top:0;">' +
          '<span class="small muted">STATUS</span>' +
          '<span class="small" style="color:var(--purple-soft);letter-spacing:0.14em;">AVAILABLE</span>' +
        "</span>" +
      "</a>"
    );
  }

  function fillFilter(select, values, label) {
    if (!select) return;
    const opts = ['<option value="">' + label + "</option>"].concat(
      values.map((v) => '<option value="' + esc(v) + '">' + esc(v) + "</option>")
    );
    select.innerHTML = opts.join("");
  }

  function applyArchiveFilters() {
    const cls = ($("#filter-class") || {}).value || "";
    const bg = ($("#filter-bg") || {}).value || "";
    const ac = ($("#filter-accent") || {}).value || "";
    const q = (($("#filter-search") || {}).value || "").trim();
    let list = archiveTokens;
    if (cls) list = list.filter((t) => t.classification === cls);
    if (bg) list = list.filter((t) => t.background === bg);
    if (ac) list = list.filter((t) => t.accent === ac);
    if (q) {
      const n = parseInt(q.replace(/^#/, ""), 10);
      if (!isNaN(n)) list = list.filter((t) => t.id === n);
      else list = list.filter((t) => (t.classification || "").toLowerCase().includes(q.toLowerCase()));
    }
    renderArchive(list);
  }

  function initArchive() {
    const host = $("#archive-grid");
    if (!host) return;
    const params = new URLSearchParams(location.search);
    const idParam = parseInt(params.get("id") || "", 10);
    if (!isNaN(idParam) && idParam >= 1 && idParam <= CFG.TOTAL_SUPPLY) {
      showDetail(idParam);
      return;
    }
    loadTokens().then((tokens) => {
      archiveTokens = tokens;
      const bgs = [...new Set(tokens.map((t) => t.background).filter(Boolean))].sort();
      const acs = [...new Set(tokens.map((t) => t.accent).filter(Boolean))].sort();
      fillFilter($("#filter-class"), CFG.CLASSIFICATIONS, "ALL CLASSIFICATIONS");
      fillFilter($("#filter-bg"), bgs, "ALL BACKGROUNDS");
      fillFilter($("#filter-accent"), acs, "ALL ACCENTS");
      ["filter-class", "filter-bg", "filter-accent", "filter-search"].forEach((fid) => {
        const el = document.getElementById(fid);
        if (el) el.addEventListener("input", applyArchiveFilters);
      });
      renderArchive(tokens);
    });
  }

  /* ---------- token detail ---------- */
  async function showDetail(id) {
    const listView = $("#archive-list");
    const detailView = $("#token-detail");
    if (listView) listView.style.display = "none";
    if (!detailView) return;
    detailView.style.display = "block";
    const tokens = await loadTokens();
    const t = tokens.find((x) => x.id === id) || { id: id, known: false };
    const meta = await fetchJSON(CFG.METADATA_PATH(id));
    const title = $("#detail-title");
    if (title) title.textContent = "XOVRATH #" + pad(id);
    const art = $("#detail-art");
    if (art) {
      art.innerHTML = '<img src="' + esc(CFG.IMAGE_PATH(id)) + '" alt="XOVRATH #' + pad(id) + '" data-token="' + id + '">';
      bindArtFallbacks(art);
    }
    const clsEl = $("#detail-class");
    if (clsEl) clsEl.textContent = t.classification || (meta && meta.attributes
      ? (meta.attributes.find((a) => a.trait_type === "Classification") || {}).value || "UNKNOWN"
      : "UNKNOWN");
    const rows = [];
    rows.push(["Token ID", "#" + pad(id)]);
    rows.push(["Classification", (t.classification || "UNKNOWN")]);
    if (t.background) rows.push(["Background", t.background]);
    if (t.form) rows.push(["Form", t.form]);
    if (t.accent) rows.push(["Accent", t.accent]);
    if (t.elements) rows.push(["Elements", Array.isArray(t.elements) ? t.elements.join(", ") : String(t.elements)]);
    if (meta && Array.isArray(meta.attributes)) {
      meta.attributes.forEach((a) => {
        if (a && a.trait_type && !rows.some((r) => r[0] === a.trait_type)) {
          rows.push([a.trait_type, String(a.value)]);
        }
      });
    }
    if (meta && meta.name) rows.push(["Name", meta.name]);
    if (meta && meta.description) rows.push(["Description", meta.description]);
    rows.push(["Status", "Available — mint is live"]);
    rows.push(["Total supply on-chain", "0 — mint is live"]);
    const body = $("#detail-attrs");
    if (body) {
      body.innerHTML = rows.map((r) =>
        "<tr><td>" + esc(r[0]) + "</td><td>" + esc(r[1]) + "</td></tr>"
      ).join("");
    }
    const metaNote = $("#detail-meta-note");
    if (metaNote) {
      metaNote.textContent = meta
        ? "Metadata loaded from the collection."
        : "Metadata for this token has not been published yet. Attributes shown come from the collection index, if available.";
    }
    document.title = "XOVRATH #" + pad(id) + " — XOVRATH";
  }

  /* ---------- mint page: agent prompt ---------- */
  function initMint() {
    const pre = $("#agent-prompt");
    if (!pre) return;
    const addr = CFG.CONTRACT_ADDRESS;
    const addrLine = addr
      ? "The XOVRATH contract address is " + addr + " on BNB Smart Chain Mainnet (chain 56)."
      : "The XOVRATH contract is not deployed yet. Do not mint anything until the owner gives you the deployed contract address — if there is no deployed contract address, stop and say so.";
    pre.textContent =
      "Mint one XOVRATH on BNB Smart Chain (chain id 56).\n" +
      addrLine + "\n" +
      "First check that my wallet holds a SPACE ID .ai Agent ID — the contract only mints to wallets holding one. There is no per-wallet mint limit.\n" +
      "Then read currentPrice() on the contract and call mint() with no arguments, sending exactly that value.\n" +
      "Show me the exact amount before I sign, and confirm the transaction on-chain once it is done.";
    const btn = $("#copy-prompt");
    if (btn) {
      btn.addEventListener("click", () => {
        const text = pre.textContent;
        const done = () => { btn.textContent = "COPIED"; setTimeout(() => { btn.textContent = "COPY PROMPT"; }, 2000); };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
        } else {
          fallbackCopy(text, done);
        }
      });
    }
  }
  function fallbackCopy(text, done) {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) { /* clipboard unavailable */ }
    document.body.removeChild(ta);
    done();
  }

  /* ---------- boot ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    initStats();
    initFeatured();
    initExplore();
    initArchive();
    initMint();
  });
})();
