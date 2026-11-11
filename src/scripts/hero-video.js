// Hero loop: honour reduced motion, recover from blocked autoplay, pause when the tab is hidden.
export function initHeroVideo() {
  const video = document.querySelector("[data-hero-video]");
  const play = document.querySelector("[data-hero-play]");
  if (!video) return;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const showButton = () => { if (play) play.hidden = false; };
  const hideButton = () => { if (play) play.hidden = true; };

  if (reduce) {
    video.removeAttribute("autoplay");
    video.pause();
    showButton();
  } else {
    video.play().then(hideButton).catch(showButton);
  }
  play?.addEventListener("click", () => video.play().then(hideButton).catch(() => {}));
  video.addEventListener("click", () => { if (video.paused) video.play().then(hideButton).catch(() => {}); });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) video.pause();
    else if (!reduce && play?.hidden !== false) video.play().catch(() => {});
  });
}
