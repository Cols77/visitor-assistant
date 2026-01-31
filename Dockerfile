FROM python:3.11-slim

WORKDIR /workspace/visitor-assistant

COPY requirements.txt /workspace/visitor-assistant/requirements.txt
RUN pip install --no-cache-dir -r /workspace/visitor-assistant/requirements.txt

COPY . /workspace/visitor-assistant

ENV PYTHONPATH=/workspace/visitor-assistant
ENV TOURASSIST_DATA_DIR=/workspace/visitor-assistant/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
