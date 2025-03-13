```bash
docker compose up -d
python -m venv .venv
source .venv/activate
pip install -r requirements.txt
uvicorn main:app
```
