DEPS:=requirements.txt

PIP:="venv/bin/pip"
CMD_FROM_VENV:=". venv/bin/activate; which"
TOX=`"$(CMD_FROM_VENV)" "tox"`
PYTHON=$(shell "$(CMD_FROM_VENV)" "python")
TOX_PY_LIST="$(shell $(TOX) -l | grep ^py | xargs | sed -e 's/ /,/g')"

.PHONY: clean pyclean test lint isort docs docker setup.py tox

tox: venv
	@$(TOX)

pyclean:
	@find . -name *.pyc -delete
	@rm -rf *.egg-info build
	@rm -rf coverage.xml .coverage

clean: pyclean
	@rm -rf venv
	@rm -rf .tox

venv:
	@virtualenv -p python2.7 venv
	@$(PIP) install -U "pip>=8.0" -q
	@$(PIP) install -r $(DEPS)

test: venv pyclean
	$(TOX) -e $(TOX_PY_LIST)

test/%: venv pyclean
	$(TOX) -e $(TOX_PY_LIST) -- $*

lint: venv
	@$(TOX) -e lint
	@$(TOX) -e isort-check

isort: venv
	@$(TOX) -e isort-fix

setup.py: venv
	@$(PYTHON) setup_gen.py
	@$(PYTHON) setup.py check --restructuredtext

publish: setup.py
	@$(PYTHON) setup.py sdist upload

build: clean venv tox setup.py
