# Small Python image. 3.12 matches what students use in the course venv.
FROM python:3.12-slim

WORKDIR /app

# Install packages first so Docker can reuse this layer when only app.py changes.
COPY handbook-chat/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handbook-chat/app.py ./
COPY policies ./policies

ENV PYTHONUNBUFFERED=1

EXPOSE 8501

# 0.0.0.0 = accept connections from outside the container (your browser).
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
