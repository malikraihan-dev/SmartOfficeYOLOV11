FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics

WORKDIR /app/backend

# Dependensi sistem untuk OpenCV dan PortAudio (sounddevice)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt

# Pasang PyTorch CPU terlebih dahulu agar ukuran image hemat (~180 MB vs ~3 GB CUDA)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Salin kode backend dan aset training yang diunduh oleh endpoint /api/sensors/assets/*
COPY backend/ /app/backend/
COPY SmartOffice_Colab_Training_SCD40.ipynb /app/SmartOffice_Colab_Training_SCD40.ipynb
COPY sensor_training/scd40_dummy.csv /app/sensor_training/scd40_dummy.csv

RUN mkdir -p /app/backend/snapshots /app/backend/training_data /app/backend/dataset_images /app/backend/instance

EXPOSE 5000

CMD ["sh", "-c", "python scripts/docker_bootstrap.py && python -u app.py"]
