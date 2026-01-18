FROM python:3.9-slim-bookworm

# Install all dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff6 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Copy your files
COPY ./app .

# Install python libraries
RUN pip install --no-cache-dir RPi.GPIO spidev Pillow requests

CMD ["python3", "main.py"]