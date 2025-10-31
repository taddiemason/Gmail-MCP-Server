const express = require('express');
const { exec } = require('child_process');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3002;

app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'gmail-mcp-bridge' });
});

// Main tool execution endpoint
app.post('/v1/tools/execute', async (req, res) => {
  try {
    const { tool_name, arguments: args } = req.body;

    if (!tool_name) {
      return res.status(400).json({ error: 'Missing tool_name' });
    }

    // Execute command in gmail-mcp-server container
    const command = buildMCPCommand(tool_name, args);

    if (!command) {
      return res.status(400).json({ error: `Unknown tool: ${tool_name}` });
    }

    console.log(`Executing: ${tool_name}`);

    exec(command, { maxBuffer: 10 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error executing ${tool_name}:`, error);
        return res.status(500).json({
          error: 'Execution failed',
          details: stderr || error.message,
          result: stdout
        });
      }

      try {
        const result = JSON.parse(stdout);
        res.json({ result: result });
      } catch (e) {
        // If output is not JSON, return as plain text
        res.json({ result: stdout });
      }
    });

  } catch (err) {
    console.error('Request handling error:', err);
    res.status(500).json({ error: 'Internal server error', details: err.message });
  }
});

// Build the Docker exec command based on tool name and arguments
function buildMCPCommand(toolName, args) {
  const argsJson = JSON.stringify(args || {}).replace(/"/g, '\\"');

  // Map tool names to MCP commands
  const toolMap = {
    'gmail_search_messages': 'search_messages',
    'gmail_get_message': 'get_message',
    'gmail_get_thread': 'get_thread',
    'gmail_get_attachment_text': 'get_attachment_text',
    'gmail_summarize_emails': 'summarize_emails',
    'gmail_send_message': 'send_message',
    'gmail_create_draft': 'create_draft',
    'gmail_list_drafts': 'list_drafts',
    'gmail_delete_draft': 'delete_draft',
    'gmail_list_labels': 'list_labels',
    'gmail_create_label': 'create_label',
    'gmail_modify_message_labels': 'modify_message_labels',
    'gmail_mark_message_read': 'mark_message_read'
  };

  const mcpTool = toolMap[toolName];
  if (!mcpTool) {
    return null;
  }

  return `docker exec gmail-mcp-server python -c "
import sys
import json
from gmail_mcp import mcp
import asyncio

async def run():
    # Import the tool function
    tool_func = getattr(sys.modules['gmail_mcp'], 'gmail_${mcpTool}', None)
    if not tool_func:
        print(json.dumps({'error': 'Tool not found'}))
        return

    # Parse arguments
    args = json.loads('${argsJson}')

    # Create a mock context (simplified)
    class MockContext:
        def __init__(self):
            self.request_context = type('obj', (object,), {
                'lifespan_state': {'http_client': None}
            })()

        async def elicit(self, prompt, input_type='text'):
            import os
            return os.getenv('GMAIL_ACCESS_TOKEN', '')

    ctx = MockContext()

    # Execute the tool
    result = await tool_func(args, ctx)
    print(json.dumps({'output': result}))

asyncio.run(run())
"`;
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Gmail MCP Bridge Server listening on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`API endpoint: http://localhost:${PORT}/v1/tools/execute`);
});
