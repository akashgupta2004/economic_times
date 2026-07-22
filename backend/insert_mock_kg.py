import os
from neo4j import GraphDatabase

# Neo4j configuration from .env
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "password"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# Cypher query to inject the mock machine maintenance guide and root causes
CYPHER_QUERY = """
// 1. Create the Main Equipment Node
MERGE (pump:Equipment {id: 'Pump_B', name: 'Main Cooling Pump B'})
SET pump.description = 'Critical cooling pump for Sector 4', pump.max_temp = 90.0, pump.min_pressure = 80.0

// 2. Create the Components
MERGE (bearing:Component {id: 'Bearing_Assembly', name: 'Rotor Bearing Assembly'})
MERGE (valve:Component {id: 'Pressure_Valve', name: 'Intake Pressure Valve'})
MERGE (sensor:Component {id: 'Sensor_Hub', name: 'Telemetry Sensor Hub'})

// Link Components to Pump
MERGE (pump)-[:HAS_COMPONENT]->(bearing)
MERGE (pump)-[:HAS_COMPONENT]->(valve)
MERGE (pump)-[:HAS_COMPONENT]->(sensor)

// 3. Create the Anomalies (that match the Isolation Forest output)
MERGE (a_temp:Anomaly {id: 'Anomaly_Temp_Spike', name: 'Extreme Temperature Spike (>95C)'})
MERGE (a_pres_drop:Anomaly {id: 'Anomaly_Pres_Drop', name: 'Massive Pressure Drop (<50 PSI)'})
MERGE (a_vib:Anomaly {id: 'Anomaly_Vib_Temp', name: 'High Vibration + High Temp'})
MERGE (a_zero:Anomaly {id: 'Anomaly_Sensor_Zero', name: 'All Sensors Read Zero'})
MERGE (a_pres_spike:Anomaly {id: 'Anomaly_Pres_Spike', name: 'Extreme Pressure Spike (>150 PSI)'})

// Link Anomalies to Components
MERGE (bearing)-[:CAN_EXPERIENCE]->(a_temp)
MERGE (bearing)-[:CAN_EXPERIENCE]->(a_vib)
MERGE (valve)-[:CAN_EXPERIENCE]->(a_pres_drop)
MERGE (valve)-[:CAN_EXPERIENCE]->(a_pres_spike)
MERGE (sensor)-[:CAN_EXPERIENCE]->(a_zero)

// 4. Create the Root Causes (The "Why")
MERGE (rc_lube:RootCause {id: 'RC_Lubrication_Failure', name: 'Lubrication Starvation', description: 'Lack of oil causing metal-on-metal friction.'})
MERGE (rc_seal:RootCause {id: 'RC_Seal_Rupture', name: 'O-Ring Seal Rupture', description: 'Internal pressure seal blowout causing fluid loss.'})
MERGE (rc_bearing:RootCause {id: 'RC_Bearing_Degradation', name: 'Severe Bearing Degradation', description: 'Ball bearing fracture causing extreme mechanical vibration.'})
MERGE (rc_power:RootCause {id: 'RC_Power_Loss', name: 'Telemetry Power Loss', description: '24V DC relay failure to sensor array.'})
MERGE (rc_blockage:RootCause {id: 'RC_Line_Blockage', name: 'Downstream Line Blockage', description: 'Blockage causing fluid backpressure.'})

// Link Anomalies to Root Causes
MERGE (a_temp)-[:CAUSED_BY]->(rc_lube)
MERGE (a_vib)-[:CAUSED_BY]->(rc_bearing)
MERGE (a_pres_drop)-[:CAUSED_BY]->(rc_seal)
MERGE (a_zero)-[:CAUSED_BY]->(rc_power)
MERGE (a_pres_spike)-[:CAUSED_BY]->(rc_blockage)

// 5. Create the Maintenance Actions (The "Fix")
MERGE (action_grease:MaintenanceAction {id: 'Action_Add_Grease', name: 'Inject High-Temp Grease (SOP-402)'})
MERGE (action_bearing:MaintenanceAction {id: 'Action_Replace_Bearing', name: 'Emergency Bearing Replacement (SOP-911)'})
MERGE (action_seal:MaintenanceAction {id: 'Action_Replace_Seal', name: 'Replace O-Ring Seal (SOP-105)'})
MERGE (action_relay:MaintenanceAction {id: 'Action_Check_Relay', name: 'Reset 24V Relay (SOP-200)'})
MERGE (action_flush:MaintenanceAction {id: 'Action_Flush_Line', name: 'Flush Downstream Line (SOP-700)'})

// Link Root Causes to Actions
MERGE (rc_lube)-[:RESOLVED_BY]->(action_grease)
MERGE (rc_bearing)-[:RESOLVED_BY]->(action_bearing)
MERGE (rc_seal)-[:RESOLVED_BY]->(action_seal)
MERGE (rc_power)-[:RESOLVED_BY]->(action_relay)
MERGE (rc_blockage)-[:RESOLVED_BY]->(action_flush)

// 6. Tie it all to a Mock Document Source so RAG can cite it
MERGE (doc:Document {id: 'Doc_OEM_PumpB', name: 'Pump B Maintenance & Troubleshooting Guide (Revision 4)', url: 'mock_manuals/Pump_B_Guide.pdf'})
MERGE (action_grease)-[:DOCUMENTED_IN]->(doc)
MERGE (action_bearing)-[:DOCUMENTED_IN]->(doc)
MERGE (action_seal)-[:DOCUMENTED_IN]->(doc)
MERGE (action_relay)-[:DOCUMENTED_IN]->(doc)
MERGE (action_flush)-[:DOCUMENTED_IN]->(doc)
"""

def inject_mock_data():
    with driver.session() as session:
        print("Injecting Mock Maintenance Guide into Neo4j...")
        session.run(CYPHER_QUERY)
        print("Successfully built Knowledge Graph topology for Pump_B!")
        
        # Verify
        result = session.run("MATCH (n) WHERE n.id STARTS WITH 'Pump_B' OR n.id STARTS WITH 'RC_' OR n.id STARTS WITH 'Action_' RETURN count(n) as count")
        count = result.single()["count"]
        print(f"Total specific nodes injected/verified: {count}")

if __name__ == "__main__":
    inject_mock_data()
    driver.close()
