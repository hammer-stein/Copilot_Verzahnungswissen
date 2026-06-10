FROM continuumio/miniconda3:latest

WORKDIR /app

# Environment zuerst kopieren (Docker Layer Cache nutzen)
COPY environment.yml .
RUN conda env create -f environment.yml && conda clean -afy

# Quellcode kopieren
COPY src/ src/

# Verzeichnisse für Daten und Ausgabe anlegen
RUN mkdir -p data/examples output

# Conda-Environment für Shell-Befehle aktivieren
SHELL ["conda", "run", "-n", "gear-copilot", "/bin/bash", "-c"]

# Port 8001 nach draußen freigeben (8000 ist vom RAG-Backend belegt)
EXPOSE 8001

# Einstiegspunkt: Uvicorn-Webserver mit der FastAPI-App starten
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "gear-copilot", \
            "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
