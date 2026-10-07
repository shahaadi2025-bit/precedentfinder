FROM python:3.12-slim
WORKDIR /app
ARG INSTALL_RAG=false
COPY requirements.txt requirements-rag.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_RAG" = "true" ]; then pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir sentence-transformers chromadb; fi
COPY . .
ENV DATA_DIR=/data ENABLE_RAG=false
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
