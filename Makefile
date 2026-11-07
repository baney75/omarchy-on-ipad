.PHONY: check build clean

check:
	python3 scripts/validate.py
	python3 scripts/public_surface.py
	python3 scripts/workflow_policy.py
	python3 -m unittest discover -s tests -v

build:
	python3 scripts/build_site.py

clean:
	rm -rf _site
