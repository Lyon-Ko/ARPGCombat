import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command=sys.executable, args=['Tools/combat_mcp.py'])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            print('MCP_TOOLS', [t.name for t in result.tools])
            status = await session.call_tool('status', {})
            print('MCP_STATUS', status.model_dump_json())
            assert not status.isError

asyncio.run(main())
