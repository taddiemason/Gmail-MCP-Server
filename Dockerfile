FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy MCP server code
COPY gmail_mcp.py .

# Expose MCP server port
EXPOSE 3002

# Run the MCP server
CMD ["python", "gmail_mcp.py"]
