# Task runner (POSIX). Windows users: use make.ps1 with the same target names.
PY ?= $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,.venv/bin/python)

.PHONY: setup audit phase0 phase0b phase1 phase2 phase3 phase4 phase5 all reoptimize test test-slow lint export \
        web-dev web-build api clean

setup:
	python -m venv .venv
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e . --no-deps
	cd web && npm install

audit:
	@echo "Legacy audit: see docs/LEGACY_AUDIT.md"

phase0:
	$(PY) -m rcopt.cli phase0
phase0b:
	$(PY) -m rcopt.cli phase0b
phase1:
	$(PY) -m rcopt.cli phase1
phase2:
	$(PY) -m rcopt.cli phase2
phase3:
	$(PY) -m rcopt.cli phase3
phase4:
	$(PY) -m rcopt.cli phase4
phase5:
	$(PY) -m rcopt.cli phase5

export:
	$(PY) -m rcopt.cli export

all:
	$(PY) -m rcopt.cli all          # phase0 .. phase5, sensitivity, cement scan, report, export

reoptimize:        # usage: make reoptimize PRICES=my_prices.csv
	$(PY) -m rcopt.cli reoptimize --prices $(PRICES)

test:
	$(PY) -m pytest -m "not slow"
test-slow:
	$(PY) -m pytest
lint:
	$(PY) -m ruff check .

web-dev:
	cd web && npm run dev
web-build:
	cd web && npm run build
api:
	$(PY) -m uvicorn api.main:app --reload

clean:
	$(PY) -c "import shutil;[shutil.rmtree(p,ignore_errors=True) for p in ('data/processed','data/results','models','web/dist')]"
