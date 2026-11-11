// Click-to-load YouTube facade (youtube-nocookie) with chapter seeking.
// Nothing is requested from YouTube until the visitor presses play or a chapter.
const API_SRC = "https://www.youtube.com/iframe_api";
let apiPromise = null;

function loadApi() {
  if (apiPromise) return apiPromise;
  apiPromise = new Promise((resolve) => {
    if (window.YT?.Player) return resolve(window.YT);
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => { prev?.(); resolve(window.YT); };
    const s = document.createElement("script");
    s.src = API_SRC; s.async = true;
    document.head.appendChild(s);
  });
  return apiPromise;
}

export function initYouTube() {
  document.querySelectorAll("[data-youtube]").forEach((facade) => {
    const id = facade.dataset.youtube;
    if (!id) return;
    const frame = facade.querySelector(".yt__frame");
    const playBtn = facade.querySelector("[data-youtube-play]");
    const chapters = document.querySelector(`[data-chapters-for="${facade.id}"]`);
    let player = null, ready = null, pendingSeek = null;

    const activate = (seek = null) => {
      if (ready) return ready;
      pendingSeek = seek;
      const mount = document.createElement("div");
      frame.innerHTML = ""; frame.appendChild(mount);
      ready = loadApi().then((YT) => new Promise((resolve) => {
        player = new YT.Player(mount, {
          host: "https://www.youtube-nocookie.com",
          videoId: id,
          playerVars: { autoplay: 1, rel: 0, modestbranding: 1, playsinline: 1, start: seek ?? 0 },
          events: {
            onReady: (e) => { e.target.getIframe().title = facade.dataset.title || "Video"; if (pendingSeek != null) e.target.seekTo(pendingSeek, true); e.target.playVideo(); resolve(player); },
            onStateChange: () => highlight(),
          },
        });
      }));
      return ready;
    };

    const highlight = () => {
      if (!player?.getCurrentTime || !chapters) return;
      const t = player.getCurrentTime();
      const items = [...chapters.querySelectorAll("[data-seek]")];
      let current = null;
      items.forEach((el) => { if (Number(el.dataset.seek) <= t + 0.5) current = el; });
      items.forEach((el) => el.toggleAttribute("aria-current", el === current));
      if (current) current.setAttribute("aria-current", "true");
    };
    setInterval(highlight, 1000);

    playBtn?.addEventListener("click", () => activate());
    chapters?.querySelectorAll("[data-seek]").forEach((el) => {
      el.addEventListener("click", (ev) => {
        ev.preventDefault();
        const t = Number(el.dataset.seek);
        if (player?.seekTo) { player.seekTo(t, true); player.playVideo(); }
        else activate(t);
        facade.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    });
  });
}
