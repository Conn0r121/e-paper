FROM python:3.9-slim-bookworm
# Install C-libraries required by Waveshare's drivers
RUN apt-get update && apt-get install -y \
    gcc python3-dev libjpeg-dev zlib1g-dev libfreetype6-dev \
    liblcms2-dev libopenjp2-7 libtiff5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# 1. Copy your app code AND the waveshare folders
COPY ./app .

# 2. Install the Python "glue" libraries
RUN pip install RPi.GPIO spidev Pillow

CMD ["python3", "main.py"]