FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV TOURASSIST_DATA_DIR=/app/data

EXPOSE 8000

CMD ["uvicorn", "tourassist.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
