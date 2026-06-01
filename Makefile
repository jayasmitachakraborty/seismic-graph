## Terraform infrastructure management

# Run from the repo root. `make tf-plan`, `make tf-apply`, `make tf-fmt ARGS=-recursive`, etc.
# Each tf-* target sources .env so TF_VAR_* values resolve correctly.

SHELL := /bin/bash
.PHONY: tf-% env-check venv clean ingestion-flow transform-flow load-flow \
        neo4j-indexes neo4j-nodes neo4j-edges neo4j-load

tf-%:
	@set -a && . ./.env && set +a && terraform -chdir=infra $* $(ARGS)

env-check:
	@set -a && . ./.env && set +a && \
		echo "TF_VAR_aura_client_id: $${TF_VAR_aura_client_id:+set}" && \
		echo "TF_VAR_aura_client_secret: $${TF_VAR_aura_client_secret:+set}"

## Virtual environment management

venv:
	@python -m venv venv
	@source venv/bin/activate && pip install -r requirements.txt

clean:
	@rm -rf venv

## Prefect flow management

ingestion-flow:
	@set -a && . ./.env && set +a && \
	python -m pipeline.ingestion_flow --start-year 2015 --end-year 2026

transform-flow:
	@set -a && . ./.env && set +a && \
	python -m pipeline.transformation_flow

load-flow:
	@set -a && . ./.env && set +a && \
	python -m pipeline.load_flow

## Neo4j Aura loader

# One-time after creating a fresh Aura instance.
neo4j-indexes:
	@set -a && . ./.env && set +a && \
	python -m load.create_indexes

neo4j-nodes:
	@set -a && . ./.env && set +a && \
	python -m load.load_nodes

neo4j-edges:
	@set -a && . ./.env && set +a && \
	python -m load.load_relationships

# Full incremental load: nodes first, then the edges that MATCH them.
neo4j-load: neo4j-nodes neo4j-edges
