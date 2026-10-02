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

  function showMusic() {
    stories.deactivate();
    player.pause();
    musicPanel.hidden = false;
    storiesPanel.hidden = true;
    music.activate();
  }

  function showStories() {
    music.deactivate();
    player.pause();
    musicPanel.hidden = true;
    storiesPanel.hidden = false;
    stories.activate();
    stories.loadSeriesList();
  }

  document.getElementById("channel-music-btn").addEventListener("click", showMusic);
  document.getElementById("channel-stories-btn").addEventListener("click", showStories);

  music.loadStations();
  showMusic();

  window.addEventListener("beforeunload", () => {
    stories.checkpoint(true);
  });
});
