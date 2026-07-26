FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WARROOM_ROOT=/opt/warroom
WORKDIR /opt/warroom
RUN useradd --system --uid 10001 --create-home warroom
COPY requirements.txt pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.txt && pip install .
COPY . .
RUN chown -R warroom:warroom /opt/warroom
USER warroom
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health',timeout=3).read()"
CMD ["python","-m","streamlit","run","streamlit_app.py","--server.address=0.0.0.0","--server.port=8501","--server.headless=true","--server.fileWatcherType=none"]
