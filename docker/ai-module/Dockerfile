FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias
COPY requirements/ /app/requirements/
COPY ai-module/requirements.txt /app/

# Instalar dependencias Python con constraints
RUN pip install --no-cache-dir -c requirements/constraints.txt -r requirements.txt

# Copiar código fuente
COPY ai-module/ /app/

EXPOSE 9004

CMD ["python", "llm_inference.py"]
