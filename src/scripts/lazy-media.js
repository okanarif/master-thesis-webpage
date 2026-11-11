// Silent loops: play only while visible, stop under reduced motion, manual toggle.
export function initLoops() {
  const loops = [...document.querySelectorAll("video[data-loop]")];
  if (!loops.length) return;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const setPaused = (video, paused) => {
    const fig = video.closest(".loop");
    const btn = fig?.querySelector("[data-loop-toggle]");
    fig?.classList.toggle("loop--paused", paused);
    if (btn) { btn.setAttribute("aria-pressed", String(!paused)); btn.setAttribute("aria-label", paused ? "Play animation" : "Pause animation"); }
  };

  loops.forEach((video) => {
    video.dataset.userPaused = reduce ? "1" : "";
    if (reduce) { video.removeAttribute("autoplay"); video.pause(); setPaused(video, true); }
    video.closest(".loop")?.querySelector("[data-loop-toggle]")?.addEventListener("click", () => {
      if (video.paused) { video.dataset.userPaused = ""; video.play().then(() => setPaused(video, false)).catch(() => {}); }
      else { video.dataset.userPaused = "1"; video.pause(); setPaused(video, true); }
    });
  });

  if (!("IntersectionObserver" in window)) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach(({ target, isIntersecting }) => {
      if (target.dataset.userPaused) return;
      if (isIntersecting) target.play().then(() => setPaused(target, false)).catch(() => setPaused(target, true));
      else target.pause();
    });
  }, { threshold: 0.4 });
  loops.forEach((v) => io.observe(v));
}
