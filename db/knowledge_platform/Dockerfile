FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 FASTEMBED_CACHE_PATH=/opt/fastembed-cache
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2', cache_dir='/opt/fastembed-cache')" \
    && chmod -R a+rX /opt/fastembed-cache
COPY ingest.py similarity_search.py ./
COPY policy_docs ./policy_docs
CMD ["python", "ingest.py"]
