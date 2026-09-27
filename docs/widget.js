/* Yubi Design - musteri yorumlari kutusu (v3) */
(function () {
  if (window.__yubiReviews) return;
  window.__yubiReviews = true;

  var BASE = (document.currentScript && document.currentScript.src || "").replace(/widget\.js.*$/, "") ||
    "https://kansadia.github.io/yubi-yorumlar/";
  var PAGE = 6;
  var cache = {};
  var lastPath = null;

  function css() {
    if (document.getElementById("yubi-rv-css")) return;
    var s = document.createElement("style");
    s.id = "yubi-rv-css";
    s.textContent =
      ".yrv{max-width:1200px;margin:48px auto 32px;padding:0 16px;font-family:inherit;color:#0e1417}" +
      ".yrv h2{font-size:22px;font-weight:600;margin:0 0 6px}" +
      ".yrv-sum{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:14px;color:#555;margin-bottom:20px}" +
      ".yrv-avg{font-size:28px;font-weight:700;color:#0e1417}" +
      ".yrv-st{color:#f5a623;letter-spacing:1px;font-size:16px}" +
      ".yrv-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}" +
      ".yrv-card{border:1px solid #e6e6e6;border-radius:2px;padding:14px;background:#fff}" +
      ".yrv-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-size:13px}" +
      ".yrv-name{font-weight:600}.yrv-date{color:#888;font-size:12px}" +
      ".yrv-txt{font-size:14px;line-height:1.5;margin:6px 0 0;white-space:pre-line;word-break:break-word}" +
      ".yrv-imgs{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}" +
      ".yrv-imgs a{display:block;width:64px;height:64px;border-radius:2px;overflow:hidden;background:#f3f3f3}" +
      ".yrv-imgs img{width:100%;height:100%;object-fit:cover}" +
      ".yrv-more{display:block;margin:18px auto 0;background:#0e1417;color:#fff;border:0;border-radius:2px;padding:11px 26px;font:inherit;font-size:14px;cursor:pointer}" +
      "@media(max-width:600px){.yrv{margin-top:32px}.yrv-grid{grid-template-columns:1fr}}";
    document.head.appendChild(s);
  }

  function esc(t) {
    return String(t).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function stars(n) {
    n = Math.round(n || 0);
    return "★★★★★".slice(0, n) + "☆☆☆☆☆".slice(0, 5 - n);
  }
  function initials(n) {
    var parts = String(n || "").split(/\s+/).map(function (w) {
      var m = w.replace(/[^A-Za-zÇĞİÖŞÜçğıöşü]/g, "");
      return m ? m.charAt(0).toLocaleUpperCase("tr-TR") + "**" : "";
    }).filter(Boolean);
    return parts.length ? parts.join(" ") : "*** ***";
  }
  function fmtDate(ms) {
    if (!ms) return "";
    try { return new Date(ms).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" }); }
    catch (e) { return ""; }
  }

  function getSkus() {
    try {
      var r = window.next && window.next.router;
      var c = r && r.components && r.components[r.route];
      var pp = c && c.props && c.props.pageProps;
      if (!pp) {
        var nd = document.getElementById("__NEXT_DATA__");
        pp = nd && JSON.parse(nd.textContent).props.pageProps;
      }
      if (!pp || pp.pageType !== "PRODUCT") return [];
      var vs = (pp.pageSpecificData && pp.pageSpecificData.variants) || [];
      var out = [];
      vs.forEach(function (v) { if (v.sku && out.indexOf(v.sku) < 0) out.push(v.sku); });
      return out;
    } catch (e) { return []; }
  }

  function load(sku) {
    if (cache[sku] !== undefined) return Promise.resolve(cache[sku]);
    var safe = sku.replace(/[^A-Za-z0-9_-]/g, "_");
    return fetch(BASE + "r/" + safe + ".json", { cache: "no-cache" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (d) { cache[sku] = d; return d; });
  }

  function card(rv) {
    var imgs = (rv.i || []).map(function (p) {
      var u = /^https?:/.test(p) ? p : BASE + "img/" + p;
      return '<a href="' + esc(u) + '" target="_blank" rel="noopener"><img loading="lazy" src="' +
        esc(u) + '" alt="Müşteri fotoğrafı"></a>';
    }).join("");
    return '<div class="yrv-card"><div class="yrv-top"><span class="yrv-name">' + esc(initials(rv.n)) +
      '</span><span class="yrv-st">' + stars(rv.r) + '</span></div>' +
      '<div class="yrv-date">' + fmtDate(rv.d) + '</div>' +
      '<p class="yrv-txt">' + esc(rv.t) + '</p>' +
      (imgs ? '<div class="yrv-imgs">' + imgs + '</div>' : "") + '</div>';
  }

  function render(data, anchor) {
    var old = document.getElementById("yubi-reviews");
    if (old) old.remove();
    if (!data || !data.reviews || !data.reviews.length) return;
    css();
    var box = document.createElement("section");
    box.id = "yubi-reviews";
    box.className = "yrv";
    box.innerHTML = '<h2>Müşteri Yorumları</h2><div class="yrv-sum">' +
      (data.avg ? '<span class="yrv-avg">' + Number(data.avg).toFixed(1).replace(".", ",") + '</span><span class="yrv-st">' + stars(data.avg) + '</span>' : "") +
      '<span>' + data.ratings + ' değerlendirme · ' + data.reviews.length + ' yorum</span>' +
      '</div>' +
      '<div class="yrv-grid"></div>';
    var grid = box.querySelector(".yrv-grid");
    var shown = 0;
    function more() {
      grid.insertAdjacentHTML("beforeend", data.reviews.slice(shown, shown + PAGE).map(card).join(""));
      shown += PAGE;
      if (shown >= data.reviews.length && btn) btn.remove();
    }
    var btn = null;
    if (data.reviews.length > PAGE) {
      btn = document.createElement("button");
      btn.className = "yrv-more";
      btn.type = "button";
      btn.textContent = "Daha fazla yorum göster";
      btn.onclick = more;
      box.appendChild(btn);
    }
    more();
    anchor.parentNode.insertBefore(box, anchor.nextSibling);
  }

  function run(tries) {
    var path = location.pathname;
    var anchor = document.querySelector('[class*="style_productContainer__"]');
    var skus = getSkus();
    if (!anchor || !skus.length) {
      if ((tries || 0) < 20) setTimeout(function () { if (location.pathname === path) run((tries || 0) + 1); }, 300);
      return;
    }
    Promise.all(skus.map(load)).then(function (list) {
      if (location.pathname !== path) return;
      var merged = null;
      list.forEach(function (d) {
        if (!d) return;
        if (!merged) { merged = { avg: d.avg, ratings: d.ratings, reviews: d.reviews.slice() }; return; }
        var tot = merged.ratings + d.ratings;
        merged.avg = tot ? Math.round((merged.avg * merged.ratings + d.avg * d.ratings) / tot * 10) / 10 : merged.avg;
        merged.ratings = tot;
        merged.reviews = merged.reviews.concat(d.reviews);
      });
      render(merged, anchor);
    });
  }

  function tick() {
    if (location.pathname !== lastPath) {
      lastPath = location.pathname;
      var old = document.getElementById("yubi-reviews");
      if (old) old.remove();
      setTimeout(run, 400);
    }
  }
  setInterval(tick, 700);
  tick();
})();
