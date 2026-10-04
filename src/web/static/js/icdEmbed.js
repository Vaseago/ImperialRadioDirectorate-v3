/* `window.icdEmbed` - the small read/command object the ICD desktop app
 * calls (through QWebEngineView.runJavaScript) when this page runs in embed
 * mode (the boot script in index.html sets data-embed="1"). The contract -
 * names, shapes, version - is written once in ICD's docs/EMBED_CONTRACT.md
 * and implemented in IID, ISD, ILD and IRD; tests/unit/test_embed_mode.py
 * fails if a contract member goes missing here.
 *
 * IRD has no router, so its "route table" is the table of views app.js
 * passes in: the Music and Stories channels, plus a Settings view that holds
 * the application-update panel. Exposes navigation labels, status flags and
 * theme tokens ONLY. Nothing here exists outside embed mode. */

const EMBED_CONTRACT_VERSION = 1;

// The shared design tokens ICD may set. Anything else is rejected.
const TOKEN_NAME = /^--(color|space|radius|font)-[a-z0-9-]+$/;
// A token value is a plain CSS value: no declaration/rule breaking
// characters, no url() (ICD's imagery arrives as its own stylesheet), no comments.
const FORBIDDEN_IN_VALUE = /[;{}\\]|url\(|\/\*/i;
const MAX_VALUE_LENGTH = 200;

function isEmbedded() {
  return document.documentElement.dataset.embed === "1";
}

// The views table in, the nav ICD draws out - built from the live table
// every call, so ICD never keeps a copy that can drift.
function navFromViews(views) {
  return Object.entries(views).map(([id, { label, kind }]) => ({
    id,
    label,
    route: `#/${id}`,
    kind: kind === "settings" ? "settings" : "view",
  }));
}

function statusSnapshot(title) {
  return {
    title,
    connection: ConnectionState.status,
    updateAvailable: UpdateState.updateAvailable,
    restartPending: UpdateState.restartPending,
    detail: UpdateState.restartPending ? UpdateState.restartMessage : "",
  };
}

// Sets each valid token on <html>. Returns {applied, rejected} (token names);
// a non-object argument rejects everything (reported as "*"). Not persisted:
// ICD re-applies after every page load.
function applyThemeTokens(tokens) {
  const applied = [];
  const rejected = [];
  if (tokens === null || typeof tokens !== "object" || Array.isArray(tokens)) {
    return { applied, rejected: ["*"] };
  }
  for (const [name, value] of Object.entries(tokens)) {
    const valid =
      TOKEN_NAME.test(name) &&
      typeof value === "string" &&
      value.length > 0 &&
      value.length <= MAX_VALUE_LENGTH &&
      !FORBIDDEN_IN_VALUE.test(value);
    if (valid) {
      document.documentElement.style.setProperty(name, value);
      applied.push(name);
    } else {
      rejected.push(name);
    }
  }
  return { applied, rejected };
}

// Defines window.icdEmbed (read-only) in embed mode; returns null and does
// nothing otherwise, so a normal visit has no `icdEmbed` at all. `views` is
// `{id: {label, kind, show}}`; `show()` opens that view.
function installIcdEmbed({ title, views }) {
  if (!isEmbedded()) return null;
  const api = Object.freeze({
    version: EMBED_CONTRACT_VERSION,
    getNav: () => navFromViews(views),
    navigate(id) {
      if (!Object.prototype.hasOwnProperty.call(views, id)) return false;
      views[id].show();
      return true;
    },
    getStatus: () => statusSnapshot(title),
    applyTheme: applyThemeTokens,
  });
  Object.defineProperty(window, "icdEmbed", { value: api, enumerable: true });
  return api;
}
