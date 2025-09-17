FROM python:3.13-slim

WORKDIR /opt/ml/processing/input

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY handler.py .

ENTRYPOINT ["python3", "handler.py"]
