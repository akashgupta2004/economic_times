#!/bin/bash
set -e

echo "=========================================="
echo " AWS g4dn.xlarge Deployment Script"
echo "=========================================="

# 1. Update system and install dependencies
echo "[1/6] Updating system and installing base dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip curl git unzip docker.io

# Start Docker for Neo4j
sudo systemctl enable --now docker
sudo usermod -aG docker $USER

# 2. Install Node.js (for frontend)
echo "[2/6] Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pm2

# 3. Install Ollama & Pull gemma3:4b
echo "[3/6] Installing Ollama (GPU accelerated)..."
curl -fsSL https://ollama.com/install.sh | sh
echo "Pulling gemma3:4b model... (This will take a few minutes)"
ollama pull gemma3:4b

# 4. Set up Neo4j Graph Database
echo "[4/6] Setting up Neo4j Docker container..."
sudo docker run -d --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=none \
    -e NEO4J_apoc_export_file_enabled=true \
    -e NEO4J_apoc_import_file_enabled=true \
    -e NEO4J_apoc_import_file_use__neo4j__config=true \
    -e NEO4JLABS_PLUGINS='["apoc"]' \
    neo4j:5

# 5. Set up Python Backend
echo "[5/6] Setting up Backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Force reinstall PyTorch for CUDA 12.1 (which matches AWS Deep Learning AMI)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 6. Set up React Frontend
echo "[6/6] Setting up Frontend..."
cd ../frontend-web
npm install

echo "=========================================="
echo " Setup Complete! Next steps:"
echo " 1. Start Backend: cd backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo " 2. Start Frontend: cd frontend-web && npm run dev -- --host 0.0.0.0"
echo "=========================================="
