.PHONY: frontend-check backend-check check

frontend-check:
	npm run lint
	npx tsc --noEmit

backend-check:
	cd medguide-evidence-engine && python -m pytest -q
	cd medguide-evidence-engine && python -m ruff check app scripts tests

check: frontend-check backend-check
