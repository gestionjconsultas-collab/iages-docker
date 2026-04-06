FROM python:3.11-slim

# Dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libmagic1 \
    libmupdf-dev \
    tesseract-ocr \
    tesseract-ocr-spa \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el backend
COPY backend/ .

# Copiar el build del frontend principal
COPY frontend/dist/ ./static/dist/

# Copiar el build del portal del empleado
COPY frontend/portal/dist/ ./static/portal/

# Copiar entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Directorio para archivos subidos (se mapea con volume)
RUN mkdir -p /app/storage /app/uploads

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
