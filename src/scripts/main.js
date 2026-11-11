// Entry point. Every module is optional progressive enhancement; the page works without JS.
import { initNav } from "./nav.js";
import { initHeroVideo } from "./hero-video.js";
import { initLoops } from "./lazy-media.js";
import { initYouTube } from "./youtube.js";
import { initChapters } from "./chapters.js";
import { initLightbox } from "./lightbox.js";

document.documentElement.classList.add("js");
initNav();
initHeroVideo();
initLoops();
initYouTube();
initChapters();
initLightbox();
