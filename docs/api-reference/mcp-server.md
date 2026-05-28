---
search:
  exclude: true
---

# MCP Server API Reference

The **Spydra MCP Server** provides nine powerful tools for web scraping through the Model Context Protocol (MCP). This server integrates Spydra's capabilities directly into AI chatbots and agents, allowing conversational web scraping with advanced anti-bot bypass features.

You can start the MCP server by running:

```bash
spydra mcp
```

Or import the server class directly:

```python
from spydra.core.ai import SpydraMCPServer

server = SpydraMCPServer()
server.serve(http=False, host="0.0.0.0", port=8000)
```

## Response Model

The standardized response structure that's returned by all MCP server tools:

## ::: spydra.core.ai.ResponseModel
    handler: python
    :docstring:

## Session Models

Model classes for session management:

## ::: spydra.core.ai.SessionInfo
    handler: python
    :docstring:

## ::: spydra.core.ai.SessionCreatedModel
    handler: python
    :docstring:

## ::: spydra.core.ai.SessionClosedModel
    handler: python
    :docstring:

## MCP Server Class

The main MCP server class that provides all web scraping tools:

## ::: spydra.core.ai.SpydraMCPServer
    handler: python
    :docstring: