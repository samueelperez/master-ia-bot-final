FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias
COPY requirements/ /app/requirements/
COPY external-data-service/requirements.txt /app/

# Instalar dependencias Python con constraints
RUN pip install --no-cache-dir -c requirements/constraints.txt -r requirements.txt

# Copiar código fuente  
COPY external-data-service/ /app/

EXPOSE 9005

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9005"]
