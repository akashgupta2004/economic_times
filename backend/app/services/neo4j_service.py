from neo4j import GraphDatabase
from app.config import settings

class Neo4jService:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def upsert_triplets(self, triplets: list[dict]):
        """
        Upserts extracted RDF triplets into Neo4j.
        Expected format: [{"subject": "PMP-101", "predicate": "has_parameter", "object": "300 PSI"}]
        """
        query = """
        UNWIND $triplets AS triplet
        MERGE (s:Entity {name: triplet.subject})
        MERGE (o:Entity {name: triplet.object})
        WITH s, o, triplet
        CALL apoc.create.relationship(s, triplet.predicate, {}, o) YIELD rel
        RETURN count(rel)
        """
        with self.driver.session() as session:
            session.run(query, triplets=triplets)

    def get_context_for_entity(self, entity_name: str):
        """
        Retrieves graph context for a specific entity to augment RAG.
        """
        query = """
        MATCH (s:Entity {name: $entity_name})-[r]-(o:Entity)
        RETURN s.name, type(r), o.name
        LIMIT 10
        """
        with self.driver.session() as session:
            result = session.run(query, entity_name=entity_name)
            return [{"subject": record[0], "predicate": record[1], "object": record[2]} for record in result]

    def get_stats(self):
        """
        Retrieves total node and relationship counts.
        """
        query_nodes = "MATCH (n) RETURN count(n) as count"
        query_rels = "MATCH ()-[r]->() RETURN count(r) as count"
        try:
            with self.driver.session() as session:
                nodes = session.run(query_nodes).single()["count"]
                rels = session.run(query_rels).single()["count"]
                return {"nodes": nodes, "relationships": rels}
        except Exception as e:
            return {"nodes": 0, "relationships": 0}

neo4j_service = Neo4jService()
