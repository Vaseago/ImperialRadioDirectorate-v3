/* Thin fetch wrappers over IRD v3's REST surface — one function per
 * endpoint, so the channel controllers never build a URL or a CSRF header
 * themselves. Every scheduling decision (which track, when an interlude
 * plays) stays server-side; this file never rolls dice or picks tracks. */

const CSRF_HEADER_NAME = "X-IRD-Request";
const CSRF_HEADER_VALUE = "1";

async function apiGet(path) {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`GET ${path} failed: ${resp.status}`);
  return resp.json();
}

async function apiPost(path, body, { csrf = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (csrf) headers[CSRF_HEADER_NAME] = CSRF_HEADER_VALUE;
  const resp = await fetch(path, { method: "POST", headers, body: JSON.stringify(body) });
  if (!resp.ok) throw new Error(`POST ${path} failed: ${resp.status}`);
  return resp.json();
}

const Api = {
  listStations: () => apiGet("/api/music/stations"),

  nextForStation: (station, excludeTrackId) => {
    const query = excludeTrackId ? `?exclude_track_id=${encodeURIComponent(excludeTrackId)}` : "";
    return apiGet(`/api/music/stations/${encodeURIComponent(station)}/next${query}`);
  },

  listStorySeries: () => apiGet("/api/stories/series"),

  tuneInToSeries: (seriesId) => apiGet(`/api/stories/series/${encodeURIComponent(seriesId)}`),

  advanceStory: (seriesId, partNumber) =>
    apiPost("/api/stories/advance", { series_id: seriesId, part_number: partNumber }),

  checkpointStory: (seriesId, partNumber, elapsedSeconds, force = false) =>
    apiPost(
      "/api/stories/checkpoint",
      { series_id: seriesId, part_number: partNumber, elapsed_seconds: elapsedSeconds, force },
      { csrf: true }
    ),

  appUpdateStatus: () => apiGet("/api/app-update/status"),
  appUpdateCheck: () => apiPost("/api/app-update/check", null),
  appUpdatePull: () => apiPost("/api/app-update/pull", null),
};
