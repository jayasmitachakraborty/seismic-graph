# seismic-graph

## Graph data model

<p align="center">
  <img src="docs/data-model.drawio.svg" alt="Seismic graph data model" width="720">
</p>

> The diagram is a [draw.io](https://app.diagrams.net) SVG with the editable
> source embedded in the file's `content` attribute. To edit, open
> [`docs/data-model.drawio.svg`](docs/data-model.drawio.svg) directly in
> diagrams.net (File → Open from → Device) and re-export over the same file.

## Neo4j setup

`load/create_indexes.py` is **not** imported or called by
`pipeline/load_flow.py`. It is a manual, one-time setup step that must be
run once against a fresh Aura instance before the load flow:

```bash
make neo4j-indexes   # one-time: create unique-key constraints
make load-flow       # incremental MERGE of nodes + relationships
```
