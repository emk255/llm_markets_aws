FROM python:3.9-slim
WORKDIR /src
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /src/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /src
CMD ["python", "/src/run.py"]
