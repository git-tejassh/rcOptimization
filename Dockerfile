# One image = dashboard + API (live evaluator + strength review). Build:  docker build -t rc-app --build-arg MODELS_URL=<link to models.zip> .
# Run:    docker run -p 8000:8000 rc-app      then open http://localhost:8000
FROM node:20-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt gdown
COPY src ./src
COPY api ./api
COPY config ./config
COPY scripts ./scripts
COPY data/results ./data/results
COPY models/manifest.json ./models/manifest.json
COPY --from=web /web/dist ./web/dist
RUN pip install --no-cache-dir -e . --no-deps
ARG MODELS_URL=""
ENV MODELS_URL=${MODELS_URL}
RUN if [ -n "$MODELS_URL" ]; then python scripts/fetch_models.py; fi
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "python -m rcopt.cli serve --host 0.0.0.0 --port ${PORT}"]
