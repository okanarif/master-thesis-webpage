// Highlights the nav link of the section currently in view.
export function initNav() {
  const links = [...document.querySelectorAll("[data-nav]")];
  if (!links.length || !("IntersectionObserver" in window)) return;
  const byId = new Map(links.map((a) => [a.dataset.nav, a]));
  const sections = [...byId.keys()].map((id) => document.getElementById(id)).filter(Boolean);
  const visible = new Map();

  const update = () => {
    let best = null;
    for (const [id, ratio] of visible) if (ratio > 0 && (!best || ratio > visible.get(best))) best = id;
    links.forEach((a) => a.removeAttribute("aria-current"));
    if (best) byId.get(best).setAttribute("aria-current", "true");
  };
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => visible.set(e.target.id, e.isIntersecting ? e.intersectionRatio : 0));
    update();
  }, { rootMargin: "-40% 0px -50% 0px", threshold: [0, 0.1, 0.25, 0.5] });
  sections.forEach((s) => io.observe(s));
}
