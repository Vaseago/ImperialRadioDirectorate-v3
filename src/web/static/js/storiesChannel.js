/* Stories channel controller — tuned per-series, like Music's stations:
 * the listener picks which story to play from a list always re-fetched
 * from the server (so a new stories/ subfolder shows up with no frontend
 * change), and that story plays until it ends. Each series remembers its
 * own resume position server-side. When a series finishes, the server's
 * `/advance` response may auto-advance into the next series that hasn't
 * been heard yet (`series_completed: true` with a track item) or stop
 * entirely once nothing unlistened remains (`series_completed: true`
 * with no track item) — this controller just plays whatever position the
 * server hands back next, it never decides story order itself. */

const STORY_CHECKPOINT_INTERVAL_MS = 15000;

class StoriesChannel {
  constructor(player, { seriesList, nowPlaying }) {
    this.player = player;
    this.seriesList = seriesList;
    this.nowPlaying = nowPlaying;
    this.queue = [];
    this.currentSeriesId = null;
    this.currentPartNumber = null;
    this.active = false;
    this.checkpointTimer = null;

    this.player.addEventListener("ended", () => this.onPartEnded());
  }

  async loadSeriesList() {
    const { series } = await Api.listStorySeries();
    this.seriesList.innerHTML = "";
    for (const entry of series) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `${entry.series_id} (${entry.part_count} parts${entry.listened ? ", listened" : ""})`;
      button.addEventListener("click", () => this.tuneInToSeries(entry.series_id));
      item.appendChild(button);
      this.seriesList.appendChild(item);
    }
  }

  activate() {
    this.active = true;
    this.checkpointTimer = setInterval(() => this.checkpoint(false), STORY_CHECKPOINT_INTERVAL_MS);
  }

  deactivate() {
    this.active = false;
    this.queue = [];
    if (this.checkpointTimer) clearInterval(this.checkpointTimer);
    this.checkpointTimer = null;
    this.checkpoint(true);
  }

  async tuneInToSeries(seriesId) {
    this.queue = [];
    const data = await Api.tuneInToSeries(seriesId);
    if (!data.track) {
      this.nowPlaying.textContent = `${seriesId}: no playable content`;
      return;
    }
    this.currentSeriesId = data.position.series_id;
    this.currentPartNumber = data.position.part_number;
    this.nowPlaying.textContent = `${this.currentSeriesId} part ${this.currentPartNumber}`;
    this.player.src = data.track.stream_url;
    this.player.currentTime = data.elapsed_seconds;
    this.player.play();
  }

  onPartEnded() {
    if (!this.active || this.currentSeriesId === null) return;
    this.checkpoint(true); // final position of the part that just ended
    if (this.queue.length) this.playNextQueued();
    else this.advance();
  }

  async advance() {
    const { items, series_completed } = await Api.advanceStory(this.currentSeriesId, this.currentPartNumber);
    this.queue.push(...items);
    if (this.queue.length) {
      this.playNextQueued();
    } else if (series_completed) {
      this.nowPlaying.textContent = "Every story has been heard — tune into one manually to continue";
      this.currentSeriesId = null;
      this.currentPartNumber = null;
    }
    if (series_completed) this.loadSeriesList();
  }

  playNextQueued() {
    const item = this.queue.shift();
    if (!item) return;
    if (item.kind === "track" && item.position) {
      this.currentSeriesId = item.position.series_id;
      this.currentPartNumber = item.position.part_number;
    }
    this.nowPlaying.textContent = `${item.kind}: ${this.currentSeriesId} part ${this.currentPartNumber}`;
    this.player.src = item.track.stream_url;
    this.player.currentTime = 0;
    this.player.play();
  }

  checkpoint(force) {
    if (this.currentSeriesId === null) return;
    Api.checkpointStory(this.currentSeriesId, this.currentPartNumber, this.player.currentTime, force).catch(() => {});
  }
}
