DIRS = pydeclares tests

format:
	pipenv run isort $(DIRS)
	pipenv run black -S -l 120 $(DIRS)

lint:
	pipenv run flake8 $(DIRS)
	pipenv run isort $(DIRS) --check
	pipenv run black -S -l 120 $(DIRS) --diff

test:
	pipenv run pytest

testcov: test
	@echo "building coverage html"
	@pipenv run coverage html

init: Pipfile.lock
	@echo "start initialize python developing environment"
	@pipenv install
	@pipenv install --dev --pre

publish:
	pipenv run python setup.py sdist bdist_wheel
	@echo "clean dist..."
	@rm -rf dist
	@rm -rf build
	@rm -rf pydeclares.egg-info
