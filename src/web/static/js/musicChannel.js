/* Music channel controller — tune into a station, play whatever the
 * server queues up (an interlude first if its 25% roll fires, then the
 * picked track), fetch the next item once the queue drains. The station
 * list is always re-fetched from the server, never hardcoded, so a new
 * subfolder under music/ (or an extra_music_dirs override) shows up
 * without any frontend change. */

class MusicChannel {
  constructor(player, { stationSelect, tuneButton, nowPlaying }) {
    this.player = player;
    this.stationSelect = stationSelect;
    this.tuneButton = tuneButton;
    this.nowPlaying = nowPlaying;
    this.queue = [];
    this.lastTrackId = null;
    this.active = false;

    this.tuneButton.addEventListener("click", () => this.tuneIn());
    this.player.addEventListener("ended", () => this.onTrackEnded());
  }

  async loadStations() {
    const { stations } = await Api.listStations();
    this.stationSelect.innerHTML = "";
    for (const station of stations) {
      const option = document.createElement("option");
      option.value = station;
      option.textContent = station;
      this.stationSelect.appendChild(option);
    }
  }

  activate() {
    this.active = true;
  }

  deactivate() {
    this.active = false;
    this.queue = [];
  }

  onTrackEnded() {
    if (!this.active) return;
    if (this.queue.length) this.playNextQueued();
    else this.fetchNext();
  }

  async tuneIn() {
    this.queue = [];
    this.lastTrackId = null;
    await this.fetchNext();
  }

  async fetchNext() {
    const station = this.stationSelect.value;
    if (!station) return;
    const { items } = await Api.nextForStation(station, this.lastTrackId);
    this.queue.push(...items);
    this.playNextQueued();
  }

  playNextQueued() {
    const item = this.queue.shift();
    if (!item) return;
    if (item.kind === "track") this.lastTrackId = item.track.id;
    this.nowPlaying.textContent = `${item.kind}: ${item.track.title}`;
    this.player.src = item.track.stream_url;
    this.player.play();
  }
}
