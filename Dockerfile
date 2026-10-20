FROM python:3.13.7-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8050
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py energy.py charts.py house_scene.py runtime.py ui.py ./
COPY assets ./assets
EXPOSE 8050
CMD ["sh", "-c", "exec gunicorn app:server --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120"]
