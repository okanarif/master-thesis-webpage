// <dialog>-based image zoom for figures. Arrow keys move within the same data-lightbox group.
export function initLightbox() {
  const links = [...document.querySelectorAll("a[data-lightbox]")];
  if (!links.length || typeof HTMLDialogElement === "undefined") return;

  const dlg = document.createElement("dialog");
  dlg.className = "lightbox";
  dlg.innerHTML = `
    <div class="lightbox__inner">
      <img class="lightbox__img" alt="">
      <p class="lightbox__caption"></p>
      <button class="lightbox__prev" type="button" aria-label="Previous image">‹</button>
      <button class="lightbox__next" type="button" aria-label="Next image">›</button>
      <button class="lightbox__close" type="button" aria-label="Close">×</button>
    </div>`;
  document.body.appendChild(dlg);
  const img = dlg.querySelector(".lightbox__img");
  const cap = dlg.querySelector(".lightbox__caption");
  const prev = dlg.querySelector(".lightbox__prev");
  const next = dlg.querySelector(".lightbox__next");
  let group = [], index = 0;

  const show = (i) => {
    index = (i + group.length) % group.length;
    const a = group[index];
    const inner = a.querySelector("img");
    img.src = a.href; img.alt = inner?.alt || "";
    cap.textContent = a.dataset.caption || "";
    prev.hidden = next.hidden = group.length < 2;
  };
  const open = (a) => {
    group = links.filter((l) => l.dataset.lightbox === a.dataset.lightbox);
    show(group.indexOf(a));
    dlg.showModal();
  };

  links.forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); open(a); }));
  prev.addEventListener("click", () => show(index - 1));
  next.addEventListener("click", () => show(index + 1));
  dlg.querySelector(".lightbox__close").addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  dlg.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") show(index - 1);
    if (e.key === "ArrowRight") show(index + 1);
  });
  dlg.addEventListener("close", () => { img.removeAttribute("src"); });
}
