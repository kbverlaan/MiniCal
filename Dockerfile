# Gebruik een officiële Python runtime als parent image
FROM python:3.13-slim

# Zet de werkdirectory in de container
WORKDIR /usr/src/app

# Kopieer het dependency-bestand
COPY requirements.txt ./

# Installeer de dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Kopieer de applicatiecode
COPY . .

# Definieer de command om de applicatie te draaien
CMD ["python", "main.py"]
