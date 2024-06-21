# Verwende ein Python-Basisimage
FROM python:3.9-slim

# Installiere Systemabhängigkeiten
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libzbar0 \
    libpoppler-cpp-dev \
    tesseract-ocr \
    tesseract-ocr-deu \
    && rm -rf /var/lib/apt/lists/*

# Kopiere das aktuelle Verzeichnis in das Arbeitsverzeichnis im Container
WORKDIR /app
COPY . /app

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Setze den Standardbefehl für den Container
ENTRYPOINT ["python3", "scanprep/scanprep.py"]

# Argumente für das Skript
CMD ["-h"]
