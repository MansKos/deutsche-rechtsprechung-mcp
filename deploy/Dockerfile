FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .
COPY download_db.py .

# Data directory for the SQLite database
RUN mkdir -p /data
ENV RECHTSPRECHUNG_DATA_DIR=/data
ENV MCP_TRANSPORT=streamable-http
ENV PORT=8002

EXPOSE 8002

# Download DB on first start, then run server
CMD ["sh", "-c", "python download_db.py && python server.py"]
