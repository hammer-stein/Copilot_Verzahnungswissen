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

# Einstiegspunkt: STEP-Parser ausführen
# Verwendung: docker run -v ./data:/app/data -v ./output:/app/output gear-copilot \
#             --input /app/data/examples/zahnrad.stp --output /app/output/result.json
# Den Port nach draußen freigeben
EXPOSE 8000

# Einstiegspunkt: Uvicorn-Webserver mit der FastAPI-App starten
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "gear-copilot", \
            "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
