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

    // Log incoming request for debugging
    console.log('=== Incoming Request ===');
    console.log('Tool:', tool_name);
    console.log('Arguments:', JSON.stringify(args, null, 2));

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
        console.error('stderr:', stderr);
        console.error('stdout:', stdout);
        return res.status(500).json({
          error: 'Execution failed',
          details: stderr || error.message,
          stdout: stdout,
          stderr: stderr
        });
      }

      console.log('Raw output:', stdout);

      try {
        const result = JSON.parse(stdout);

        // Check if the result contains an error from the Python script
        if (result.error) {
          console.error('Tool execution error:', result);
          return res.status(500).json({
            error: result.error,
            type: result.type,
            traceback: result.traceback
          });
        }

        res.json({ result: result });
      } catch (e) {
        console.error('JSON parse error:', e);
        console.error('Attempted to parse:', stdout);
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
  // Serialize arguments as JSON - no shell escaping needed with heredoc
  const argsJson = JSON.stringify(args || {});

  // Strip "gmail/" prefix if present
  const cleanToolName = toolName.replace(/^gmail\//, '');

  // Map tool names from OpenWebUI to MCP function names
  const toolMap = {
    // Format from OpenWebUI Tools (gmail_tools.py)
    'search_emails': 'gmail_search_messages',
    'get_email': 'gmail_get_message',
    'get_thread': 'gmail_get_thread',
    'get_attachment_text': 'gmail_get_attachment_text',
    'summarize_emails': 'gmail_summarize_emails',
    'send_email': 'gmail_send_message',
    'create_draft': 'gmail_create_draft',
    'list_drafts': 'gmail_list_drafts',
    'delete_draft': 'gmail_delete_draft',
    'list_labels': 'gmail_list_labels',
    'create_label': 'gmail_create_label',
    'modify_labels': 'gmail_modify_message_labels',
    'mark_read': 'gmail_mark_message_read',
    // Also support direct MCP names
    'gmail_search_messages': 'gmail_search_messages',
    'gmail_get_message': 'gmail_get_message',
    'gmail_get_thread': 'gmail_get_thread',
    'gmail_get_attachment_text': 'gmail_get_attachment_text',
    'gmail_summarize_emails': 'gmail_summarize_emails',
    'gmail_send_message': 'gmail_send_message',
    'gmail_create_draft': 'gmail_create_draft',
    'gmail_list_drafts': 'gmail_list_drafts',
    'gmail_delete_draft': 'gmail_delete_draft',
    'gmail_list_labels': 'gmail_list_labels',
    'gmail_create_label': 'gmail_create_label',
    'gmail_modify_message_labels': 'gmail_modify_message_labels',
    'gmail_mark_message_read': 'gmail_mark_message_read'
  };

  const mcpToolName = toolMap[cleanToolName];
  if (!mcpToolName) {
    console.error(`Unknown tool: ${toolName} (cleaned: ${cleanToolName})`);
    return null;
  }

  return `docker exec gmail-mcp-server python -c "
import sys
import json
from gmail_mcp import mcp
import asyncio
import gmail_mcp

async def run():
    try:
        # Import the tool function
        tool_func = getattr(gmail_mcp, '${mcpToolName}', None)
        if not tool_func:
            print(json.dumps({'error': 'Tool not found: ${mcpToolName}'}))
            sys.exit(1)

        # Parse arguments from JSON string
        args_json = '''${argsJson}'''
        args_dict = json.loads(args_json)

        # Get the input model class name (e.g., gmail_search_messages -> GmailSearchInput)
        # This is a mapping of tool names to their Pydantic input models
        model_map = {
            'gmail_search_messages': 'GmailSearchInput',
            'gmail_get_message': 'GmailGetMessageInput',
            'gmail_get_thread': 'GmailGetThreadInput',
            'gmail_get_attachment_text': 'GmailGetAttachmentTextInput',
            'gmail_summarize_emails': 'SummarizeEmailsInput',
            'gmail_send_message': 'GmailSendInput',
            'gmail_create_draft': 'GmailDraftInput',
            'gmail_list_drafts': 'GmailListDraftsInput',
            'gmail_delete_draft': 'GmailDeleteDraftInput',
            'gmail_list_labels': 'GmailListLabelsInput',
            'gmail_create_label': 'GmailCreateLabelInput',
            'gmail_modify_message_labels': 'GmailModifyLabelsInput',
            'gmail_mark_message_read': 'GmailMarkReadInput'
        }

        model_class_name = model_map.get('${mcpToolName}')
        if model_class_name:
            # Get the Pydantic model class and instantiate it with the arguments
            model_class = getattr(gmail_mcp, model_class_name, None)
            if model_class:
                params = model_class(**args_dict)
            else:
                # Fallback to dict if model class not found
                params = args_dict
        else:
            # Use dict directly for tools without specific models
            params = args_dict

        # Create a mock context with a real HTTP client
        import httpx

        class MockContext:
            def __init__(self):
                self.http_client = httpx.AsyncClient(timeout=30.0)
                self.request_context = type('obj', (object,), {
                    'lifespan_state': {'http_client': self.http_client}
                })()

            async def elicit(self, prompt, input_type='text'):
                import os
                return os.getenv('GMAIL_ACCESS_TOKEN', '')

            async def cleanup(self):
                await self.http_client.aclose()

        ctx = MockContext()

        # Execute the tool
        try:
            result = await tool_func(params, ctx)
            print(json.dumps({'output': result}))
        finally:
            # Clean up the HTTP client
            await ctx.cleanup()

    except Exception as e:
        import traceback
        print(json.dumps({
            'error': str(e),
            'type': type(e).__name__,
            'traceback': traceback.format_exc()
        }))
        sys.exit(1)

asyncio.run(run())
"`;
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Gmail MCP Bridge Server listening on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`API endpoint: http://localhost:${PORT}/v1/tools/execute`);
});
