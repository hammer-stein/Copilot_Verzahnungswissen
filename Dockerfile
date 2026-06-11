FROM python:3.11-slim

WORKDIR /app

# Saubere Logs (kein Output-Buffering) und kein Bytecode-Müll im Image.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Vorhersehbarer Pfad für den Hugging-Face-Modell-Cache (BGE-M3) → per Volume persistierbar.
    HF_HOME=/app/.cache/huggingface

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode + Frontend (inkl. frontend/design-system = neues GUI) + Domänendateien.
COPY app/ app/
COPY frontend/ frontend/
COPY schemas/ schemas/
COPY prompts/ prompts/

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
