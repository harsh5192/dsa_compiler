/* Shell behaviour shared by every page: theme, tabs, service worker. */
(function () {
  "use strict";

  /* ------------------------------------------------------------- theme */
  var STORAGE_KEY = "dsa-theme";

  function readTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      return null;
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (err) {
      /* private mode: the attribute is enough for this page view */
    }
  }

  var stored = readTheme();
  if (stored) {
    document.documentElement.setAttribute("data-theme", stored);
  }

  document.addEventListener("click", function (event) {
    var toggle = event.target.closest("[data-theme-toggle]");
    if (!toggle) return;
    var order = ["system", "light", "dark"];
    var current = document.documentElement.getAttribute("data-theme") || "system";
    var next = order[(order.indexOf(current) + 1) % order.length];
    applyTheme(next);
    toggle.setAttribute("title", "Theme: " + next);
  });

  /* -------------------------------------------------------------- tabs */
  document.addEventListener("click", function (event) {
    var tab = event.target.closest(".tab[data-tab]");
    if (!tab) return;
    var group = tab.closest(".panel-editor") || tab.parentElement.parentElement;
    group.querySelectorAll(".tab").forEach(function (el) {
      el.classList.toggle("is-active", el === tab);
    });
    group.querySelectorAll(".tab-panel").forEach(function (panel) {
      panel.classList.toggle("is-active", panel.dataset.panel === tab.dataset.tab);
    });
  });

  /* ------------------------------------------------- current nav marking */
  var here = window.location.pathname;
  document.querySelectorAll(".topnav a").forEach(function (link) {
    var href = link.getAttribute("href") || "";
    if (href !== "/" && here.indexOf(href) === 0) {
      link.setAttribute("aria-current", "page");
    }
  });

  /* ----------------------------------------------- offline-friendly SW */
  // Registered only on http(s); a file:// install just skips it.
  if ("serviceWorker" in navigator && window.location.protocol.indexOf("http") === 0) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {
        /* offline caching is a bonus, never a requirement */
      });
    });
  }

  /* --------------------------------------------- editor tab indentation */
  document.addEventListener("keydown", function (event) {
    var area = event.target;
    if (!area || area.tagName !== "TEXTAREA") return;
    if (!area.classList.contains("editor-textarea")) return;
    if (event.key === "Tab") {
      event.preventDefault();
      var start = area.selectionStart;
      var end = area.selectionEnd;
      area.value = area.value.slice(0, start) + "    " + area.value.slice(end);
      area.selectionStart = area.selectionEnd = start + 4;
      area.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
})();
