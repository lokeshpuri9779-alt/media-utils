FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ORT_DISABLE_TELEMETRY=1 \
    ASTRA_GPU_BIND=0.0.0.0 \
    ASTRA_GPU_PORT=8765 \
    ASTRA_ALLOW_PAID_CHARACTER_VIDEO=0

RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv git ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/astra
COPY requirements.txt /opt/astra/requirements.txt
RUN python3 -m pip install --break-system-packages -r /opt/astra/requirements.txt

COPY open_source_video_engine.py /opt/astra/
COPY gpu_worker_health.py /opt/astra/
COPY gpu_worker_server.py /opt/astra/

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python3 -c "import os,urllib.request; u='http://127.0.0.1:'+os.getenv('ASTRA_GPU_PORT','8765')+'/health'; r=urllib.request.Request(u,headers={'Authorization':'Bearer '+os.environ.get('ASTRA_GPU_WORKER_TOKEN','')}); urllib.request.urlopen(r,timeout=5).read()" || exit 1

CMD ["python3","gpu_worker_server.py"]
