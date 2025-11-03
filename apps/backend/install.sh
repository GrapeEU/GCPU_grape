#!/bin/bash
#
# Grape Backend - Installation Script
# Usage: ./install.sh
#

set -euo pipefail

echo "Grape Backend - Installation"
echo "================================"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "[!] uv is not installed"
    echo "[*] Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "[+] uv installed"
    echo "[!] Please restart your terminal and run this script again"
    exit 0
fi

echo "[+] uv detected: $(uv --version)"
echo ""

# Create virtual environment
echo "[*] Creating Python 3.12 virtual environment..."
uv venv --python 3.12 --seed pip

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    ACTIVATE_CMD=".venv\\Scripts\\activate"
    VENV_PYTHON=".venv\\Scripts\\python.exe"
else
    ACTIVATE_CMD="source .venv/bin/activate"
    VENV_PYTHON=".venv/bin/python"
fi

if [ ! -x "$VENV_PYTHON" ]; then
    if [ -x ".venv/bin/python3" ]; then
        VENV_PYTHON=".venv/bin/python3"
    elif [ -x ".venv/bin/python3.12" ]; then
        VENV_PYTHON=".venv/bin/python3.12"
    elif [ -x ".venv/Scripts/python.exe" ]; then
        VENV_PYTHON=".venv/Scripts/python.exe"
    else
        echo "[!] Executable Python introuvable dans la virtualenv (.venv)."
        echo "    Vérifiez que 'uv venv' a bien créé l'environnement."
        exit 1
    fi
fi

echo "[+] Virtual environment created"
echo ""

echo "[*] Installing Python dependencies..."
if [ -f requirements.txt ]; then
    uv pip install -r requirements.txt
else
    uv sync
fi

echo "[+] Dependencies installed"
echo ""

# Install Spacy models
echo "[*] Downloading Spacy models..."
"$VENV_PYTHON" -m spacy download en_core_web_sm
"$VENV_PYTHON" -m spacy download en_core_web_lg

echo "[+] Spacy models installed"
echo ""

# Optional: Install scispacy models
read -p "Do you want to install scientific models (scispacy)? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "[*] Installing scispacy models..."
    uv pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
    uv pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bionlp13cg_md-0.5.4.tar.gz
    uv pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_craft_md-0.5.4.tar.gz
    echo "[+] Scispacy models installed"
fi

echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "[*] Creating .env file..."
    cp .env.example .env
    echo "[+] .env file created"
    echo "[!] Don't forget to configure your API keys in .env"
else
    echo "[i] .env file already exists"
fi

echo ""
cat <<EOF

[+] Installation complete!

Next steps:
  1. Edit apps/backend/.env and provide your Google Cloud project or service-account settings
     (GOOGLE_APPLICATION_CREDENTIALS / GOOGLE_CLOUD_PROJECT, etc.).
  2. If you run the frontend from another domain, update apps/web/.env to point NEXT_PUBLIC_API_URL to your backend URL.
  3. Start GraphDB locally:
       docker-compose -f ../../docker-compose.graphdb.yml up -d
  4. Create/load the OWL2-RL repository named "unified" (done automatically if you run the existing compose file),
     then load the demo data:
       bash ../../scripts/refresh_unified_demo.sh
  5. Ensure the Ollama embedding model is available:
       ollama pull nomic-embed-text
  6. Generate embeddings for the unified KG (once GraphDB is running):
       python ../../scripts/generate_grape_embeddings.py unified
  7. Activate the virtualenv and launch the API:
       $ACTIVATE_CMD
       python main.py

Docs:        http://localhost:8000/docs
Healthcheck: http://localhost:8000/api/health

EOF
