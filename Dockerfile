# Gebruik een officiële Python runtime als parent image
FROM python:3.13-slim

# Zet de werkdirectory in de container
WORKDIR /usr/src/app

# Kopieer het dependency-bestand
COPY requirements.txt ./

# Upgrade pip en installeer dependencies met een langere timeout
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Kopieer de applicatiecode
COPY . .

# Definieer de command om de applicatie te draaien
CMD ["python", "main.py"]
