# 🏭 Industrial Copilot - The AI for Field Technicians

> **Built for the ET AI Hackathon 2026**
> 
> *A state-of-the-art Agentic Copilot designed to diagnose machine failures in real-time by fusing Time-Series Machine Learning with Multi-Hop Knowledge Graph Reasoning.*

---

## 🌟 The Problem We Are Solving
In industrial settings, when a machine fails, technicians waste hours cross-referencing live sensor data with hundreds of pages of PDF maintenance manuals to figure out what went wrong and how to fix it.

## 🚀 Our Solution: The Industrial Copilot
We built an autonomous AI agent that acts as a genius sidekick for technicians. 
It features a **Multi-Hop Reasoning Pipeline**:
1. **Real-Time Telemetry Analysis:** The copilot hooks into a live TSDB (Time-Series Database) and runs an **Isolation Forest Machine Learning model** to instantly detect mathematical anomalies (e.g., Extreme Temperature Spikes) in the sensor data.
2. **Graph RAG Diagnosis:** Once an anomaly is found, the agent autonomously queries our **Neo4j Knowledge Graph** (built via LightRAG) to trace the symptom back to a specific component failure, determine the root cause, and fetch the exact Standard Operating Procedure (SOP) to fix it.

---

## 🧠 System Architecture

- **Backend:** `FastAPI` (Python)
- **Agent Orchestration:** `LangGraph` + `LiteLLM` (ReAct Architecture)
- **Knowledge Graph RAG:** `LightRAG` + `Neo4j` + `nano-vectordb`
- **Machine Learning:** `scikit-learn` (Isolation Forest for Anomaly Detection)
- **Time-Series Database:** `SQLite` (Mocking real-time sensor streams)
- **Frontend Dashboard:** `React` + `Vite` (For factory managers)
- **Frontend Mobile:** `Expo` + `React Native` (For field technicians)

---

## 🛠️ Setup Instructions

### Prerequisites
- [Docker](https://www.docker.com/) (For Neo4j database)
- [Node.js](https://nodejs.org/) (For React web dashboard and Expo mobile app)
- [Python 3.10+](https://www.python.org/) (For FastAPI backend)

### Step 1: Start the Knowledge Graph Database (Neo4j)
1. Open a terminal in the root `industrial-copilot` folder.
2. Run the following command to start the Neo4j container in the background:
   ```bash
   docker compose up -d
   ```
3. The Neo4j browser will be available at [http://localhost:7474](http://localhost:7474).

### Step 2: Start the Backend API & Agent
1. Open a new terminal.
2. Navigate to the backend folder:
   ```bash
   cd backend
   ```
3. Activate the virtual environment:
   ```bash
   # On Windows
   .\venv\Scripts\Activate.ps1
   ```
4. Start the FastAPI server:
   ```bash
   python -m uvicorn app.main:app --reload
   ```
5. The API will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Step 3: Start the Web Dashboard
1. Open a new terminal.
2. Navigate to the web folder:
   ```bash
   cd frontend-web
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. The dashboard will be available at [http://localhost:5173](http://localhost:5173).

### Step 4: Start the Mobile Copilot App
1. Open a new terminal.
2. Navigate to the mobile folder:
   ```bash
   cd frontend-mobile
   ```
3. Start the Expo server:
   ```bash
   npx expo start
   ```
4. Press `w` to open it in a web browser, or scan the QR code using the Expo Go app on your phone.

---

## 🧪 Demo: Testing the Multi-Hop Reasoning

Want to see the true power of the Copilot? Type this exact prompt into the chat interface:
> *"Run an anomaly detection on the temperature sensor for Pump_B. If you detect any mathematical anomalies or extreme temperature spikes, search the maintenance guides to tell me what component is failing, the root cause, and the exact SOP to fix it."*

**The AI will:**
1. Connect to the telemetry database.
2. Run the `Isolation Forest` model and discover a 95.5°C anomaly on Pump_B.
3. Automatically search the `Neo4j` knowledge graph for that exact symptom.
4. Output the correct failing component, the root cause, and the exact maintenance SOP required to fix it!
