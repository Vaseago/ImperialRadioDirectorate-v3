/* Bootstrap — wires the two channel controllers to the shared <audio>
 * element and the channel-switch buttons. Functional skeleton only. */

document.addEventListener("DOMContentLoaded", () => {
  const player = document.getElementById("player");

  const music = new MusicChannel(player, {
    stationSelect: document.getElementById("station-select"),
    tuneButton: document.getElementById("tune-music-btn"),
    nowPlaying: document.getElementById("music-now-playing"),
  });

  const stories = new StoriesChannel(player, {
    seriesList: document.getElementById("story-series-list"),
    nowPlaying: document.getElementById("stories-now-playing"),
  });

  const musicPanel = document.getElementById("music-panel");
  const storiesPanel = document.getElementById("stories-panel");
  const updatePanel = document.getElementById("app-update-panel");
  const settingsUnavailable = document.getElementById("settings-unavailable");
  let currentChannel = "music";

  function showMusic() {
    currentChannel = "music";
    stories.deactivate();
    player.pause();
    musicPanel.hidden = false;
    storiesPanel.hidden = true;
    music.activate();
  }

  function showStories() {
    currentChannel = "stories";
    music.deactivate();
    player.pause();
    musicPanel.hidden = true;
    storiesPanel.hidden = false;
    stories.activate();
    stories.loadSeriesList();
  }

  // ICD embed mode (js/icdEmbed.js): ICD draws the nav, so these are the views
  // it can open. Settings holds the update panel and never touches the player,
  // so it is safe to open while something plays; going back to the channel
  // already tuned only reveals it again (re-opening it the normal way would
  // stop the audio).
  const pageRoot = document.documentElement;
  function openChannelView(name, show) {
    pageRoot.dataset.icdView = name;
    if (name === currentChannel) {
      musicPanel.hidden = name !== "music";
      storiesPanel.hidden = name !== "stories";
      return;
    }
    show();
  }
  function openSettingsView() {
    pageRoot.dataset.icdView = "settings";
    musicPanel.hidden = true;
    storiesPanel.hidden = true;
    settingsUnavailable.hidden = !updatePanel.hidden;
  }
  installIcdEmbed({
    title: "Imperial Radio Directorate",
    views: {
      music: { label: "Music", kind: "view", show: () => openChannelView("music", showMusic) },
      stories: { label: "Stories", kind: "view", show: () => openChannelView("stories", showStories) },
      settings: { label: "Settings", kind: "settings", show: openSettingsView },
    },
  });

  document.getElementById("channel-music-btn").addEventListener("click", showMusic);
  document.getElementById("channel-stories-btn").addEventListener("click", showStories);

  music.loadStations();
  showMusic();
  pageRoot.dataset.icdView = "music";

  const appUpdate = new AppUpdatePanel({
    panel: document.getElementById("app-update-panel"),
    statusText: document.getElementById("app-update-status"),
    checkButton: document.getElementById("app-update-check-btn"),
    pullButton: document.getElementById("app-update-pull-btn"),
  });
  appUpdate.init();

  window.addEventListener("beforeunload", () => {
    stories.checkpoint(true);
  });
});
