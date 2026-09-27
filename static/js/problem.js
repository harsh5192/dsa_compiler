/* The solve page: run, submit, autosave, shortcuts, optional Monaco.
 *
 * Everything is plain fetch + DOM.  No framework, no CDN.  If the locally
 * bundled Monaco assets are missing (the default for a fresh checkout) the
 * plain textarea stays in charge and everything still works.
 */
(function () {
  "use strict";

  var workspace = document.querySelector(".workspace");
  if (!workspace) return;

  var cfg = workspace.dataset;
  var codeInput = document.getElementById("code-input");
  var customCases = document.getElementById("custom-cases");
  var languageSelect = document.getElementById("language-select");
  var btnRun = document.getElementById("btn-run");
  var btnSubmit = document.getElementById("btn-submit");
  var btnReset = document.getElementById("btn-reset");
  var saveState = document.getElementById("save-state");
  var verdictBar = document.getElementById("verdict-bar");
  var verdictEl = document.getElementById("verdict");
  var verdictSummary = document.getElementById("verdict-summary");
  var casesBody = document.getElementById("cases-body");
  var complexityBody = document.getElementById("complexity-body");
  var consoleCompile = document.getElementById("console-compile");
  var consoleOut = document.getElementById("console-stdout");
  var consoleErr = document.getElementById("console-stderr");

  var VERDICT_LABELS = {
    accepted: "Accepted",
    wrong_answer: "Wrong Answer",
    compilation_error: "Compilation Error",
    runtime_error: "Runtime Error",
    time_limit_exceeded: "Time Limit Exceeded",
    memory_limit_exceeded: "Memory Limit Exceeded",
    empty_submission: "Empty Submission",
    internal_error: "Internal Error",
    custom: "Output only",
  };

  var savedAt = null;
  var dirty = false;
  var monaco = null;
  var autosaveTimer = null;

  /* ------------------------------------------------------------ helpers */
  function language() {
    return languageSelect ? languageSelect.value : "";
  }

  function csrf() {
    return cfg.csrf || "";
  }

  function text(value) {
    return value === null || value === undefined ? "" : String(value);
  }

  function short(value, limit) {
    var str = text(value);
    return str.length > limit ? str.slice(0, limit) + "…" : str;
  }

  function bytes(value) {
    if (value < 1024) return value + " B";
    if (value < 1024 * 1024) return (value / 1024).toFixed(1) + " KB";
    return (value / (1024 * 1024)).toFixed(1) + " MB";
  }

  function setTab(name) {
    var tab = document.querySelector('.tab[data-tab="' + name + '"]');
    if (tab) tab.click();
  }

  function getCode() {
    if (monaco) return monaco.editor.getModels()[0].getValue();
    return codeInput.value;
  }

  function setCode(value) {
    if (monaco) {
      monaco.editor.getModels()[0].setValue(value);
    } else {
      codeInput.value = value;
    }
    onEdited();
  }

  function markSaved(note) {
    savedAt = Date.now();
    dirty = false;
    saveState.textContent = note || "Saved";
  }

  function markDirty() {
    dirty = true;
    if (savedAt) {
      var seconds = Math.max(1, Math.round((Date.now() - savedAt) / 1000));
      saveState.textContent = "Unsaved (" + seconds + "s)";
    } else {
      saveState.textContent = "Unsaved";
    }
  }

  function onEdited() {
    markDirty();
    if (cfg.autosave === "1") scheduleAutosave();
  }

  /* --------------------------------------------------------- networking */
  function postJSON(url, payload) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(payload),
    }).then(function (response) {
      return response
        .json()
        .catch(function () {
          return { ok: false, error: "The server sent a reply we could not read." };
        })
        .then(function (data) {
          data.status = response.status;
          return data;
        });
    });
  }

  function getJSON(url) {
    return fetch(url, { credentials: "same-origin" })
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {
        data.status = response.status;
        return data;
      });
  }

  /* --------------------------------------------------------- rendering */
  function showError(message) {
    verdictBar.hidden = false;
    verdictBar.classList.remove("is-running");
    verdictEl.className = "verdict verdict-internal_error";
    verdictEl.textContent = "Error";
    verdictSummary.textContent = message;
    setTab("output");
  }

  function renderCases(cases) {
    casesBody.innerHTML = "";
    if (!cases || !cases.length) {
      casesBody.innerHTML =
        '<tr class="empty-row"><td colspan="6" class="muted">No cases were executed.</td></tr>';
      return;
    }
    cases.forEach(function (item) {
      var row = document.createElement("tr");
      var label = item.label || "Test case";
      if (item.is_custom) label += " (custom)";
      row.innerHTML =
        "<td>" + escapeHtml(label) + "</td>" +
        '<td title="' + escapeAttr(text(item.input)) + '">' + escapeHtml(short(item.input, 60)) + "</td>" +
        '<td title="' + escapeAttr(text(item.expected_output)) + '">' + escapeHtml(short(item.expected_output, 60)) + "</td>" +
        '<td title="' + escapeAttr(text(item.actual_output)) + '"><strong>' +
        escapeHtml(short(item.actual_output, 80)) + "</strong></td>" +
        "<td>" +
        '<span class="verdict verdict-' + escapeAttr(item.verdict) + '">' +
        escapeHtml(VERDICT_LABELS[item.verdict] || item.verdict) + "</span>" +
        (item.error ? '<div class="muted small">' + escapeHtml(short(item.error, 160)) + "</div>" : "") +
        "</td>" +
        "<td>" + (item.execution_time || 0).toFixed(3) + "s</td>";
      casesBody.appendChild(row);
    });
  }

  function renderComplexity(data) {
    if (!data) {
      complexityBody.textContent = "Run or submit to see the estimate.";
      return;
    }
    var expected = data.expected || {};
    var notes = (data.notes || []).map(function (n) { return "<li>" + escapeHtml(n) + "</li>"; }).join("");
    complexityBody.innerHTML =
      "<table class='table'><tbody>" +
      "<tr><th>Time</th><td>" + escapeHtml(data.time) + "</td></tr>" +
      "<tr><th>Space</th><td>" + escapeHtml(data.space) + "</td></tr>" +
      "<tr><th>Reference</th><td>" + escapeHtml(text(expected.time) || "—") + " time, " +
      escapeHtml(text(expected.space) || "—") + " space</td></tr>" +
      "<tr><th>Confidence</th><td>" + escapeHtml(data.confidence) + "</td></tr>" +
      "</tbody></table>" +
      (notes ? "<p class='muted small'>Notes</p><ul class='muted small'>" + notes + "</ul>" : "") +
      "<p class='muted small'>Heuristic only: it reads your source, it does not measure it.</p>";
  }

  function renderReport(data, mode) {
    var report = data.report || {};
    verdictBar.hidden = false;
    verdictBar.classList.remove("is-running");
    verdictEl.className = "verdict verdict-" + report.verdict;
    verdictEl.textContent = VERDICT_LABELS[report.verdict] || report.verdict;

    var bits = [
      report.test_cases_passed + "/" + report.total_test_cases + " cases",
      (report.execution_time || 0).toFixed(3) + "s total",
      bytes(report.memory_used || 0),
    ];
    if (mode === "submit" && data.submission_url) {
      bits.push("saved as submission #" + data.submission_id);
    }
    if (report.error_message) bits.push(short(report.error_message, 140));
    verdictSummary.textContent = bits.join(" · ");

    renderCases(report.cases);
    renderComplexity(data.complexity);
    consoleCompile.textContent = text(report.compile_output) || "— (nothing to show)";
    consoleOut.textContent = text(report.stdout) || "—";
    consoleErr.textContent = text(report.stderr) || "—";

    if (mode === "submit" && data.progress && data.progress.solved) {
      markSaved("Solved");
    }
  }

  function escapeHtml(value) {
    return text(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  function escapeAttr(value) {
    return escapeHtml(value).replace(/"/g, "&quot;");
  }

  /* ------------------------------------------------------------ actions */
  function busy(isBusy, label) {
    btnRun.disabled = isBusy;
    btnSubmit.disabled = isBusy;
    if (isBusy) {
      verdictBar.hidden = false;
      verdictBar.classList.add("is-running");
      verdictEl.className = "verdict";
      verdictEl.innerHTML = '<span class="spinner"></span> Running';
      verdictSummary.textContent = label || "compiling and executing…";
    }
  }

  function send(url, mode, label) {
    var code = getCode();
    if (!code.trim()) {
      showError("There is no code to run yet.");
      return;
    }
    busy(true, label);
    var payload = {
      problem: cfg.problem,
      language: language(),
      code: code,
      custom_cases: customCases ? customCases.value.trim() : "",
      save: true,
    };
    postJSON(url, payload)
      .then(function (data) {
        if (!data.ok) {
          showError(data.error || "The request failed.");
          return;
        }
        renderReport(data, mode);
        markSaved(mode === "submit" ? "Submitted" : "Ran");
        if (mode === "submit" && data.submission_url) {
          verdictSummary.innerHTML = escapeHtml(verdictSummary.textContent) +
            ' · <a href="' + escapeAttr(data.submission_url) + '">open submission</a>';
        }
      })
      .catch(function () {
        showError("The runner did not answer. Is the server still running?");
      })
      .then(function () {
        busy(false);
      });
  }

  function saveNow(quiet) {
    var code = getCode();
    if (!code.trim()) return;
    return postJSON(cfg.apiSave, {
      problem: cfg.problem,
      language: language(),
      code: code,
    })
      .then(function (data) {
        if (data.ok) {
          markSaved(quiet ? "Saved" : "Saved " + new Date().toLocaleTimeString());
        } else if (!quiet) {
          saveState.textContent = "Save failed";
        }
      })
      .catch(function () {
        if (!quiet) saveState.textContent = "Save failed";
      });
  }

  function scheduleAutosave() {
    if (autosaveTimer) clearTimeout(autosaveTimer);
    var delay = parseInt(cfg.autosaveDelay, 10) || 1200;
    autosaveTimer = setTimeout(function () {
      if (dirty) saveNow(true);
    }, delay);
  }

  function loadStarter() {
    var url = cfg.apiStarter + "?language=" + encodeURIComponent(language());
    getJSON(url)
      .then(function (data) {
        if (data.ok) setCode(data.code);
      })
      .catch(function () {
        /* keep whatever the user has */
      });
  }

  /* ------------------------------------------------------------ wiring */
  codeInput.addEventListener("input", onEdited);

  if (btnRun) {
    btnRun.addEventListener("click", function () {
      send(cfg.apiRun, "run");
    });
  }
  if (btnSubmit) {
    btnSubmit.addEventListener("click", function () {
      send(cfg.apiSubmit, "submit");
    });
  }
  if (btnReset) {
    btnReset.addEventListener("click", function () {
      if (getCode().trim() && !window.confirm("Replace your code with the starter template?")) {
        return;
      }
      loadStarter();
    });
  }
  if (languageSelect) {
    languageSelect.addEventListener("change", function () {
      if (getCode().trim() && !window.confirm("Switching language loads that language's starter code. Continue?")) {
        return;
      }
      loadStarter();
    });
  }

  document.addEventListener("keydown", function (event) {
    if (!(event.ctrlKey || event.metaKey)) return;
    var key = event.key.toLowerCase();
    if (key === "s") {
      event.preventDefault();
      saveNow(false);
    } else if (key === "enter" && event.shiftKey) {
      event.preventDefault();
      send(cfg.apiSubmit, "submit");
    } else if (key === "enter") {
      event.preventDefault();
      send(cfg.apiRun, "run");
    }
  });

  window.addEventListener("beforeunload", function (event) {
    if (!dirty) return;
    if (savedAt) return; // recently saved, nothing to warn about
    event.preventDefault();
    event.returnValue = "";
  });

  markSaved("Saved");
  setTab("cases");

  /* ------------------------------------------------------------- monaco */
  // Opt-in: only used when the assets are actually on disk, so an offline or
  // fresh checkout degrades to the textarea instead of failing to load.
  if (cfg.editor === "monaco") {
    var loader = document.createElement("script");
    loader.src = "/static/editor/monaco/vs/loader.js";
    loader.onload = function () {
      window.require.config({ paths: { vs: "/static/editor/monaco/vs" } });
      window.require(["vs/editor/editor.main"], function () {
        var host = document.getElementById("monaco-host");
        if (!host) return;
        monaco = window.monaco;
        host.hidden = false;
        codeInput.hidden = true;
        monaco.editor.defineTheme("dsa-light", {
          base: "vs",
          inherit: true,
          rules: [],
          colors: {},
        });
        var initial = codeInput.value;
        monaco.editor.create(host, {
          value: initial,
          language: monacoLanguage(),
          theme: cfg.editorTheme === "vs" ? "vs" : "vs-dark",
          fontSize: parseInt(cfg.fontSize, 10) || 14,
          automaticLayout: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          tabSize: 4,
        });
        monaco.editor.getModels()[0].onDidChangeContent(onEdited);
      });
    };
    loader.onerror = function () {
      codeInput.hidden = false; // plain editor stays
    };
    document.head.appendChild(loader);
  }

  function monacoLanguage() {
    var option = languageSelect && languageSelect.selectedOptions[0];
    return (option && option.dataset.monaco) || "plaintext";
  }
})();
