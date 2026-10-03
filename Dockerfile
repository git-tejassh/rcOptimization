# Local/remote API image: live surrogate + ground-truth FE. Build AFTER `make all` so models/ and data/results/ exist.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY api ./api
COPY config ./config
COPY models ./models
COPY data/results ./data/results
COPY legacy/staad_model/*.STD ./legacy/staad_model/
RUN pip install --no-cache-dir -e . --no-deps
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
