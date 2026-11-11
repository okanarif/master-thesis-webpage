# master-thesis-webpage

Static project page. Content lives in `content/*.yaml`, markup in `src/templates`,
styles in `src/styles`, behaviour in `src/scripts`. `tools/build.py` renders
everything into `dist/`, which GitHub Actions deploys to GitHub Pages.

```
make setup   # one-time: virtualenv + dependencies
make build   # render dist/
make check   # build + lint
make watch   # local preview at http://localhost:8000 with rebuild on change
```

Web media in `assets/` are produced by the scripts in `tools/media/` from local
source files that are not part of this repository.
