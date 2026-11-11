.PHONY: setup build check serve watch clean media-sim media-hero media-flights media-figures media-photos media-og media-all

PY := .venv/bin/python

setup:
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt

build:
	$(PY) tools/build.py

check: build
	$(PY) tools/check.py dist

serve: build
	$(PY) tools/serve.py --port 8000

watch:
	$(PY) tools/serve.py --port 8000 --watch

clean:
	rm -rf dist

# Media pipeline: reads Media/ (local only), writes assets/ (committed)
media-sim:
	bash tools/media/20_sim_web.sh
media-hero:
	bash tools/media/10_hero.sh
media-flights:
	bash tools/media/30_flight_clips.sh
media-figures:
	$(PY) tools/media/50_figures.py
media-photos:
	$(PY) tools/media/60_photos.py
media-og:
	$(PY) tools/media/70_og_image.py
media-all: media-sim media-hero media-figures media-photos media-og
