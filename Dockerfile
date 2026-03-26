FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects PORT env variable; ADK api_server uses 8080 by default
ENV PORT=8080

EXPOSE 8080

# adk api_server runs the agent as a REST API on the given port
CMD ["sh", "-c", "adk api_server --host 0.0.0.0 --port ${PORT} wardrobe_agent"]
