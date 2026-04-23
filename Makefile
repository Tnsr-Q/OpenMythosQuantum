.PHONY: validate lint test install docs clean

validate:
	bash scripts/validate-openapi.sh

lint:
	bash scripts/lint-openapi.sh

test:
	python3 tests/plugins/run_all_tests.py
	python3 tests/contract/run_all_contract_tests.py

install:
	pip install -e .[dev]
	npm install

docs:
	npx @redocly/cli build-docs openapi/openapi.yaml -o docs/api.html

clean:
	rm -rf .pytest_cache .mypy_cache
