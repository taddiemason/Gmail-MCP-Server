# Gmail MCP Server Diagnostics Guide

This guide will help you diagnose issues with argument passing from OpenWebUI through the bridge to the MCP server.

## Step 1: Verify Containers Are Running

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected output:
- `gmail-mcp-server` - Should be Up
- `gmail-mcp-bridge` - Should be Up with port 3002 mapped

## Step 2: Test Bridge Health

```bash
curl http://localhost:3002/health
```

Expected output:
```json
{"status":"ok","service":"gmail-mcp-bridge"}
```

## Step 3: Test Bridge with Simple Tool Call

Test the search_emails tool directly:

```bash
curl -X POST http://localhost:3002/v1/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "gmail/search_emails",
    "arguments": {
      "query": "is:unread",
      "max_results": 5,
      "response_format": "markdown"
    }
  }' | jq .
```

**What to check:**
- Does it return a result or an error?
- Is the error about missing arguments or something else?
- Save the full output

## Step 4: Test Without "gmail/" Prefix

```bash
curl -X POST http://localhost:3002/v1/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "search_emails",
    "arguments": {
      "query": "is:unread",
      "max_results": 5,
      "response_format": "markdown"
    }
  }' | jq .
```

## Step 5: Test List Labels (Simplest Tool)

```bash
curl -X POST http://localhost:3002/v1/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "gmail/list_labels",
    "arguments": {}
  }' | jq .
```

This tool has no required arguments, so it should work if the bridge is functioning.

## Step 6: Check Bridge Server Logs

```bash
docker logs gmail-mcp-bridge --tail 100
```

**Look for:**
- Tool execution messages: "Executing: gmail_search_messages"
- Error messages about arguments
- JSON parsing errors
- Docker exec command output

## Step 7: Check MCP Server Logs

```bash
docker logs gmail-mcp-server --tail 100
```

**Look for:**
- MCP server startup messages
- Tool execution logs
- Python errors or tracebacks

## Step 8: Test MCP Server Directly

Execute a tool directly in the MCP container to bypass the bridge:

```bash
docker exec gmail-mcp-server python -c "
import sys
import json
from gmail_mcp import mcp
import asyncio

async def run():
    tool_func = getattr(sys.modules['gmail_mcp'], 'gmail_list_labels', None)
    if not tool_func:
        print(json.dumps({'error': 'Tool not found'}))
        return

    class MockContext:
        def __init__(self):
            self.request_context = type('obj', (object,), {
                'lifespan_state': {'http_client': None}
            })()

        async def elicit(self, prompt, input_type='text'):
            import os
            return os.getenv('GMAIL_ACCESS_TOKEN', '')

    ctx = MockContext()
    result = await tool_func({}, ctx)
    print(json.dumps({'output': result}))

asyncio.run(run())
"
```

This tests the MCP server independently. If this works, the issue is in the bridge.

## Step 9: Rebuild Bridge with Enhanced Logging

The bridge server now includes enhanced logging and better error handling. Rebuild it:

```bash
docker-compose up -d --build mcp-bridge
```

The logs will now show:
- Incoming requests with tool names and arguments
- Raw output from the MCP server
- JSON parsing errors with the attempted parse content
- Python exceptions with full tracebacks

Check the logs:
```bash
docker logs -f gmail-mcp-bridge
```

Then try the tool from OpenWebUI and watch the logs in real-time.

## Step 10: Common Issues

### Issue: "Missing required argument"
- **Cause**: Arguments not being passed to MCP server
- **Check**: Bridge logs for the docker exec command being constructed
- **Fix**: Verify JSON escaping in buildMCPCommand function

### Issue: "Unknown tool"
- **Cause**: Tool name not mapping correctly
- **Check**: Bridge logs for "Unknown tool: X (cleaned: Y)"
- **Fix**: Verify toolMap in bridge-server.js includes the tool name

### Issue: "Permission denied"
- **Cause**: Bridge can't access Docker socket
- **Fix**: Run `sudo usermod -aG docker $USER` and restart

### Issue: Empty or null response
- **Cause**: MCP server returning data but bridge can't parse it
- **Check**: MCP server logs for the actual output
- **Fix**: Check JSON parsing in bridge-server.js line 44-50

## Expected Flow

1. **OpenWebUI Tool** calls `search_emails(query="test")`
2. **gmail_tools.py** sends POST to bridge:
   ```json
   {
     "tool_name": "gmail/search_emails",
     "arguments": {
       "query": "test",
       "max_results": 20,
       "response_format": "markdown"
     }
   }
   ```
3. **Bridge** receives request, maps tool name to `gmail_search_messages`
4. **Bridge** constructs docker exec command with escaped JSON arguments
5. **MCP Server** receives arguments via Python script, executes tool
6. **MCP Server** returns JSON result
7. **Bridge** parses JSON and returns to OpenWebUI
8. **OpenWebUI Tool** returns result to user

## Debugging Checklist

- [ ] Containers are running
- [ ] Health check passes
- [ ] Direct curl to bridge works
- [ ] Bridge logs show tool execution
- [ ] MCP server logs show no errors
- [ ] Direct MCP server test works
- [ ] OpenWebUI request format is correct
- [ ] Tool name mapping is working
- [ ] Arguments are being passed correctly
- [ ] Response is being parsed correctly

## Next Steps

After running these diagnostics, report:
1. Which step first fails
2. The exact error message
3. The relevant logs from bridge and MCP server
4. The output of the curl test commands
