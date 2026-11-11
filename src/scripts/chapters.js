// Chapter buttons for in-page <video> elements (not YouTube).
export function initChapters() {
  document.querySelectorAll("[data-chapters-for]").forEach((list) => {
    const video = document.getElementById(list.dataset.chaptersFor);
    if (!(video instanceof HTMLVideoElement)) return;
    const items = [...list.querySelectorAll("button[data-seek]")];
    if (!items.length) return;
    items.forEach((btn) => btn.addEventListener("click", () => {
      video.currentTime = Number(btn.dataset.seek);
      video.play().catch(() => {});
    }));
    video.addEventListener("timeupdate", () => {
      let current = null;
      items.forEach((b) => { if (Number(b.dataset.seek) <= video.currentTime + 0.5) current = b; });
      items.forEach((b) => b.toggleAttribute("aria-current", b === current));
      if (current) current.setAttribute("aria-current", "true");
    });
  });
}
