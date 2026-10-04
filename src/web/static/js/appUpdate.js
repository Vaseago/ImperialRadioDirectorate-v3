/* App-update panel controller — same "check, then ask" two-step flow the
 * backend enforces: Check only ever reveals what's pending, Pull is a
 * separate, deliberate, confirmed action. No push/WebSocket here (IRD v3
 * has none) — this just polls `GET /api/app-update/status` once on load,
 * same as any other page reflecting server-side state. */

// What the ICD embed contract's getStatus() reports about updates
// (js/icdEmbed.js): an update waiting, and a restart that has been announced.
const UpdateState = { updateAvailable: false, restartPending: false, restartMessage: "" };

class AppUpdatePanel {
  constructor({ panel, statusText, checkButton, pullButton }) {
    this.panel = panel;
    this.statusText = statusText;
    this.checkButton = checkButton;
    this.pullButton = pullButton;

    this.checkButton.addEventListener("click", () => this.check());
    this.pullButton.addEventListener("click", () => this.pull());
  }

  async init() {
    const { pending, available } = await Api.appUpdateStatus();
    if (!available) {
      this.panel.hidden = true;
      return;
    }
    this.panel.hidden = false;
    this.render(pending);
  }

  async check() {
    this.statusText.textContent = "Checking...";
    const { pending } = await Api.appUpdateCheck();
    this.render(pending);
  }

  async pull() {
    if (!window.confirm("Pull the update and restart the server now? The app will be briefly unavailable.")) {
      return;
    }
    this.statusText.textContent = "Pulling update...";
    const result = await Api.appUpdatePull();
    this.statusText.textContent = result.self_restarting
      ? "Update pulled — server is restarting..."
      : "Update pulled — please restart the server manually to load it.";
    this.pullButton.hidden = true;
    UpdateState.updateAvailable = false;
    if (result.self_restarting) {
      UpdateState.restartPending = true;
      UpdateState.restartMessage = "Update pulled - server is restarting...";
    }
  }

  render(pending) {
    UpdateState.updateAvailable = Boolean(pending);
    if (!pending) {
      this.statusText.textContent = "No pending update found (or not checked yet).";
      this.pullButton.hidden = true;
      return;
    }
    this.statusText.textContent =
      `Update available: ${pending.current_commit} -> ${pending.latest_commit} ` +
      `(${pending.commits_behind} commit${pending.commits_behind === 1 ? "" : "s"} behind)`;
    this.pullButton.hidden = false;
  }
}
