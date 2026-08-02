FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies first so this layer is cached across code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code (venv/, data/, output/ are excluded via .dockerignore)
COPY . .

RUN mkdir -p data/raw output

# Bake the dataset into the image so the container runs standalone, no network needed at runtime
RUN python download_data.py

ENV PYTHONUNBUFFERED=1

CMD ["python", "pipeline.py"]
