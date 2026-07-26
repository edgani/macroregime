PYTHON ?= python3
export PYTHONPATH := $(CURDIR)/src

.PHONY: install validate test bootstrap collect status streamlit api docker-up docker-down
install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install .

test:
	$(PYTHON) -m pytest -q

validate:
	$(PYTHON) scripts/validate_all.py

bootstrap:
	$(PYTHON) scripts/warroom.py bootstrap-all

collect:
	$(PYTHON) scripts/warroom.py collect-all

status:
	$(PYTHON) scripts/warroom.py status

streamlit:
	$(PYTHON) scripts/warroom.py streamlit --host 127.0.0.1 --port 8501

api:
	$(PYTHON) scripts/warroom.py serve --host 127.0.0.1 --port 8080

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
