.PHONY: install data api ingest transform check demo demo-mismatch preview docs clean

PY ?= python3
export DUCKDB_PATH ?= $(CURDIR)/warehouse.duckdb

install:            ## Install local dependencies
	pip install -r requirements-dev.txt

data:               ## Generate synthetic platform data
	$(PY) mock_crm/generate_data.py

api:                ## Run the mock CRM API in the foreground
	$(PY) mock_crm/app.py

demo: clean data    ## Full local run: mock API -> ingest -> dbt build -> checks -> dashboard preview
	@$(PY) mock_crm/app.py > /tmp/mock_api.log 2>&1 & echo $$! > /tmp/mock_api.pid; sleep 2
	SUMMARY_LOOKBACK_DAYS=120 $(PY) pipeline.py; status=$$?; kill `cat /tmp/mock_api.pid`; \
	$(PY) scripts/build_dashboard_preview.py; exit $$status

demo-mismatch:      ## Simulate lost bet data and watch reconciliation + alerting catch it
	$(PY) scripts/simulate_data_loss.py
	cd dbt && dbt build --profiles-dir . ; cd .. ; $(PY) -m monitoring.check_and_alert dbt/target || true

preview:            ## Rebuild the HTML dashboard preview from the warehouse
	$(PY) scripts/build_dashboard_preview.py

docs:               ## Generate and serve dbt docs (lineage + data dictionary)
	cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .

clean:
	rm -f warehouse.duckdb warehouse.duckdb.wal
	rm -rf dbt/target dbt/logs

docker-demo:        ## Same as `make demo`, in Docker (output in ./output)
	docker compose up --build --abort-on-container-exit --exit-code-from pipeline

docker-mismatch:    ## Simulate data loss against the Docker warehouse
	docker compose run --rm -e DUCKDB_PATH=/output/warehouse.duckdb pipeline sh -c \
	  "python scripts/simulate_data_loss.py && cd dbt && dbt build --profiles-dir . ; cd .. && python -m monitoring.check_and_alert dbt/target"

docker-clean:
	docker compose down --remove-orphans
	rm -rf output
