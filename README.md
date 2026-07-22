# Industrial Copilot - Setup Guide

This guide will help you start all the components of the Universal Ingestion Pipeline & Expert Knowledge Copilot.

## Prerequisites
- [Docker](https://www.docker.com/) (For Neo4j database)
- [Node.js](https://nodejs.org/) (For React web dashboard and Expo mobile app)
- [Python 3.10+](https://www.python.org/) (For FastAPI backend)

## Step 1: Start the Knowledge Graph Database (Neo4j)
1. Open a terminal in the root `industrial-copilot` folder.
2. Run the following command to start the Neo4j container in the background:
   ```bash
   docker compose up -d
   ```
3. The Neo4j browser will be available at [http://localhost:7474](http://localhost:7474).

## Step 2: Start the Backend API
The backend handles the RAGFlow webhook, LLM extraction (via Gemini/Groq), and Neo4j integration.
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

## Step 3: Start the Web Dashboard
The web dashboard is for system administrators to view ingestion status.
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

## Step 4: Start the Mobile Copilot App
The mobile app provides the conversational voice interface for field technicians.
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
