FROM python:3.12-slim-bookworm

# Runtime + build dependencies.
#   - gcc / python3-dev: needed to build RPi.GPIO and spidev from source
#   - fonts-dejavu-core: bundled fonts used by the dashboard
# Pillow ships prebuilt wheels, so its image libraries are no longer required here.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Install Python deps first so this layer is cached across app-code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app .

CMD ["python3", "main.py"]
