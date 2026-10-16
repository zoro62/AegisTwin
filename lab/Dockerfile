FROM python:3.12.10-slim
WORKDIR /lab
COPY service.py .
COPY probe.py .
USER 65534:65534
CMD ["python", "service.py"]
