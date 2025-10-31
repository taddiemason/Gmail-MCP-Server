#!/bin/bash

echo "=== Gmail MCP Bridge Test Script ==="
echo ""

echo "Step 1: Rebuilding bridge container..."
docker-compose up -d --build mcp-bridge

echo ""
echo "Step 2: Waiting for container to start..."
sleep 3

echo ""
echo "Step 3: Testing health endpoint..."
curl -s http://localhost:3002/health | jq .

echo ""
echo "Step 4: Testing list_labels (simplest tool)..."
curl -s -X POST http://localhost:3002/v1/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "gmail_list_labels",
    "arguments": {}
  }' | jq .

echo ""
echo "Step 5: Testing search_emails..."
curl -s -X POST http://localhost:3002/v1/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "gmail_search_messages",
    "arguments": {
      "query": "is:unread",
      "max_results": 5
    }
  }' | jq .

echo ""
echo "Step 6: Checking bridge logs (last 20 lines)..."
docker logs gmail-mcp-bridge --tail 20

echo ""
echo "=== Test Complete ==="
