import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp.github_tools import github_clone, github_search
from mcp.filesystem import list_dir, read_file, delete_file

app = Server("ai-forge-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="github_clone", description="Clone a GitHub repository", inputSchema={
            "type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]
        }),
        Tool(name="github_search", description="Search GitHub repos", inputSchema={
            "type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]
        }),
        Tool(name="list_dir", description="List directory contents", inputSchema={
            "type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]
        }),
        Tool(name="read_file", description="Read file content", inputSchema={
            "type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]
        }),
        Tool(name="delete_file", description="Delete a file or directory", inputSchema={
            "type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]
        })
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "github_clone":
        res = await github_clone(arguments["url"])
    elif name == "github_search":
        res = await github_search(arguments["query"])
    elif name == "list_dir":
        res = await list_dir(arguments["path"])
    elif name == "read_file":
        res = await read_file(arguments["path"])
    elif name == "delete_file":
        res = await delete_file(arguments["path"])
    else:
        res = "Tool not found"
        
    return [TextContent(type="text", text=str(res))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
