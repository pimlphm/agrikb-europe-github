from __future__ import annotations

import json
from pathlib import Path

import networkx as nx


class GraphBuilder:
    def __init__(self, chunk_dir: str | Path, output_path: str | Path) -> None:
        self.chunk_dir = Path(chunk_dir)
        self.output_path = Path(output_path)

    def build(self) -> dict:
        graph = nx.MultiDiGraph()
        chunk_files = sorted(self.chunk_dir.glob("*.json"))

        for path in chunk_files:
            chunk = json.loads(path.read_text(encoding="utf-8"))
            chunk_id = chunk["chunk_id"]
            graph.add_node(chunk_id, kind="chunk", chunk_type=chunk.get("chunk_type", "evidence"))

            for entity in chunk.get("entities", []):
                graph.add_node(entity, kind="entity")
                graph.add_edge(entity, chunk_id, relation="mentioned_in")

            for condition in chunk.get("conditions", []):
                condition_id = f"condition::{condition}"
                graph.add_node(condition_id, kind="condition", label=condition)
                graph.add_edge(chunk_id, condition_id, relation="occurs_in")

            for relation in chunk.get("relations", []):
                relation_id = f"relation::{chunk_id}::{relation.get('type', 'related_to')}"
                graph.add_node(relation_id, kind="relation", label=relation.get("type", "related_to"))
                graph.add_edge(chunk_id, relation_id, relation="has_relation")

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        nx.write_graphml(graph, self.output_path)
        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "output_path": str(self.output_path),
        }
