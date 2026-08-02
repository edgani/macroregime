"""Mechanism-first economic graph."""
import networkx as nx
from eros.mechanisms.registry import MechanismEdge
from eros.ontology.entities import Entity


class EconomicGraph:
    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def add_entity(self, entity: Entity) -> None:
        self.graph.add_node(entity.entity_id, **entity.model_dump())

    def add_mechanism_edge(self, edge: MechanismEdge) -> None:
        self.graph.add_edge(edge.source_entity, edge.target_entity, key=edge.mechanism_id, **edge.model_dump(mode="json"))

    def export_rows(self) -> list[dict[str, object]]:
        return [{"source": source, "target": target, **data} for source, target, data in self.graph.edges(data=True)]
