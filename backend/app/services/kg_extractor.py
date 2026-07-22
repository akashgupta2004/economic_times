import logging
import json
from dataclasses import dataclass, field
from gliner import GLiNER
from neo4j import GraphDatabase
from litellm import acompletion
from app.config import settings

logger = logging.getLogger(__name__)

# Load model globally to avoid reloading on every call
# Use a lightweight stable model
GLINER_MODEL = "urchade/gliner_medium-v2.1"
try:
    gliner_model = GLiNER.from_pretrained(GLINER_MODEL)
except Exception as e:
    logger.error(f"Failed to load GLiNER model: {e}")
    gliner_model = None

@dataclass
class Entity:
    """A named entity extracted from a document."""
    name: str
    entity_type: str  
    properties: dict = field(default_factory=dict)
    source_page: int = 0

@dataclass 
class Relation:
    """A relationship between two entities."""
    source: str  
    target: str  
    relation_type: str  
    properties: dict = field(default_factory=dict)

# We define labels for Industrial KG
ENTITY_LABELS = [
    "Machine", "Equipment", "Sensor", "Component", 
    "Error Code", "Maintenance Procedure", "Person", "Location", "Metric"
]

RELATION_KEYWORDS = {
    "has_sensor": ["equipped with", "monitored by", "sensor", "instrumented"],
    "triggers_error": ["triggers", "causes", "results in", "leads to", "generates"],
    "requires_part": ["requires", "needs", "replace with", "part number", "component"],
    "maintained_by": ["maintenance procedure", "SOP", "work instruction", "follow"],
    "operates_at": ["operating", "normal range", "setpoint", "rated"],
    "connected_to": ["connected to", "feeds", "supplies", "downstream", "upstream"],
    "located_in": ["located in", "installed in", "area", "zone", "section"],
}

def extract_entities_local(chunks: list) -> list[Entity]:
    """
    Extract entities from document chunks using GLiNER.
    """
    if not gliner_model:
        logger.warning("GLiNER model not loaded, returning empty entities.")
        return []
    
    entities_dict = {}
    
    for chunk in chunks:
        text = chunk.text
        page = getattr(chunk, "page_number", 0)
        
        try:
            # GLiNER extracts entities with their labels
            extracted = gliner_model.predict_entities(text, ENTITY_LABELS, threshold=0.5)
            
            for e in extracted:
                name = e["text"].strip()
                if not name:
                    continue
                
                entity_type = e["label"]
                if entity_type in ["Machine", "Equipment", "Error Code", "Maintenance Procedure"]:
                    name = name.upper()
                else:
                    name = name.lower()
                    
                if len(name) < 2:
                    continue
                    
                key = f"{entity_type}:{name}"
                if key not in entities_dict:
                    entities_dict[key] = Entity(
                        name=name,
                        entity_type=entity_type,
                        properties={"pages": [page]},
                        source_page=page
                    )
                else:
                    if page not in entities_dict[key].properties.get("pages", []):
                        entities_dict[key].properties.setdefault("pages", []).append(page)
                        
        except Exception as e:
            logger.error(f"GLiNER entity extraction failed on chunk: {e}")
            
    logger.info(f"Extracted {len(entities_dict)} unique entities locally via GLiNER")
    return list(entities_dict.values())


def extract_relations_local(chunks: list, entities: list[Entity]) -> list[Relation]:
    """
    Extract relations between entities using keyword proximity.
    """
    entity_names = {e.name.lower(): e for e in entities}
    relations = []
    seen = set()
    
    for chunk in chunks:
        text_lower = chunk.text.lower()
        page = getattr(chunk, "page_number", 0)
        
        # Find which entities appear in this chunk
        chunk_entities = []
        for name_lower, entity in entity_names.items():
            if name_lower in text_lower:
                chunk_entities.append(entity)
                
        if len(chunk_entities) < 2:
            continue
            
        # Check for relation keywords
        for rel_type, keywords in RELATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    for i, e1 in enumerate(chunk_entities):
                        for e2 in chunk_entities[i+1:]:
                            rel_key = f"{e1.name}|{rel_type}|{e2.name}"
                            if rel_key not in seen:
                                seen.add(rel_key)
                                relations.append(Relation(
                                    source=e1.name,
                                    target=e2.name,
                                    relation_type=rel_type,
                                    properties={"keyword": keyword, "page": page}
                                ))
                    break  # One keyword match per relation type per chunk
                    
    logger.info(f"Extracted {len(relations)} relations locally via GLiNER proximity heuristics")
    return relations


async def enrich_with_llm(
    entities: list[Entity],
    relations: list[Relation],
    summary_text: str
) -> tuple[list[Entity], list[Relation]]:
    """
    Send a condensed summary to the LLM to validate and enrich
    the locally extracted entities and relations.
    """
    if not settings.GROQ_API_KEY:
        logger.warning("No GROQ_API_KEY set, skipping LLM enrichment")
        return entities, relations
    
    entity_summary = ", ".join(f"{e.name} ({e.entity_type})" for e in entities[:30])
    relation_summary = ", ".join(f"{r.source} -[{r.relation_type}]-> {r.target}" for r in relations[:20])
    
    truncated_source = summary_text[:1500] if len(summary_text) > 1500 else summary_text
    
    prompt = f"""You are an industrial knowledge graph expert. I extracted entities and relations from a document using GLiNER.

Source text (truncated):
{truncated_source}

Entities found: {entity_summary}
Relations found: {relation_summary}

Respond ONLY with a JSON object containing:
1. "new_entities": list of objects with "name", "entity_type" (Machine/Sensor/Error Code/Component/Maintenance Procedure/Metric/Location/Person), and "description" 
2. "new_relations": list of objects with "source", "target", "relation_type", and "description"

Only add entities/relations that are clearly stated in the text and that I missed. Keep it concise."""

    try:
        response = await acompletion(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise industrial knowledge extraction assistant. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            api_key=settings.GROQ_API_KEY,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        existing_names = {e.name.lower() for e in entities}
        for new_e in result.get("new_entities", []):
            if new_e.get("name", "").lower() not in existing_names:
                entities.append(Entity(
                    name=new_e["name"],
                    entity_type=new_e.get("entity_type", "unknown"),
                    properties={"description": new_e.get("description", ""), "source": "llm_enrichment"}
                ))
        
        existing_rels = {f"{r.source}|{r.relation_type}|{r.target}" for r in relations}
        for new_r in result.get("new_relations", []):
            rel_key = f"{new_r.get('source', '')}|{new_r.get('relation_type', '')}|{new_r.get('target', '')}"
            if rel_key not in existing_rels:
                relations.append(Relation(
                    source=new_r["source"],
                    target=new_r["target"],
                    relation_type=new_r.get("relation_type", "related_to"),
                    properties={"description": new_r.get("description", ""), "source": "llm_enrichment"}
                ))
        
        logger.info(
            f"LLM enrichment added {len(result.get('new_entities', []))} entities "
            f"and {len(result.get('new_relations', []))} relations"
        )
        
    except Exception as e:
        logger.error(f"LLM enrichment failed (non-fatal): {e}")
    
    return entities, relations


async def insert_into_neo4j(
    entities: list[Entity],
    relations: list[Relation],
    document_title: str = "Unknown Document"
) -> dict:
    """
    Batch-insert extracted entities and relations into Neo4j.
    Returns stats about what was inserted.
    """
    uri = settings.NEO4J_URI
    username = settings.NEO4J_USERNAME
    password = settings.NEO4J_PASSWORD
    
    stats = {"entities_created": 0, "relations_created": 0, "errors": []}
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            session.run(
                "MERGE (d:Document {title: $title})",
                title=document_title
            )
            
            for entity in entities:
                try:
                    label = entity.entity_type.capitalize().replace(" ", "_")
                    session.run(
                        f"MERGE (e:{label} {{name: $name}}) "
                        f"SET e.entity_type = $entity_type, "
                        f"e.source_page = $page "
                        f"WITH e "
                        f"MERGE (d:Document {{title: $doc_title}}) "
                        f"MERGE (d)-[:CONTAINS]->(e)",
                        name=entity.name,
                        entity_type=entity.entity_type,
                        page=entity.source_page,
                        doc_title=document_title
                    )
                    stats["entities_created"] += 1
                except Exception as e:
                    stats["errors"].append(f"Entity '{entity.name}': {str(e)}")
            
            for relation in relations:
                try:
                    rel_type = relation.relation_type.upper().replace(" ", "_")
                    session.run(
                        f"MATCH (a {{name: $source}}) "
                        f"MATCH (b {{name: $target}}) "
                        f"MERGE (a)-[r:{rel_type}]->(b) "
                        f"SET r.source_doc = $doc_title",
                        source=relation.source,
                        target=relation.target,
                        doc_title=document_title
                    )
                    stats["relations_created"] += 1
                except Exception as e:
                    stats["errors"].append(f"Relation '{relation.source}->{relation.target}': {str(e)}")
        
        driver.close()
        
    except Exception as e:
        logger.error(f"Neo4j insertion failed: {e}")
        stats["errors"].append(f"Neo4j connection: {str(e)}")
    
    logger.info(
        f"Neo4j insertion complete: {stats['entities_created']} entities, "
        f"{stats['relations_created']} relations, {len(stats['errors'])} errors"
    )
    return stats
