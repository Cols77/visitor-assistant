.PHONY: install run eval test

install:
	pip install -r requirements.txt

run:
	uvicorn tourassist.app.main:app --reload --host 0.0.0.0 --port 8000

eval:
	python scripts/run_eval.py --tenant demo --cases eval/tenants/demo/cases.json

test:
	pytest -q
