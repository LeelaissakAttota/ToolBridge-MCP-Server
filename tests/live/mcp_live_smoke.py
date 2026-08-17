import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    url = "http://127.0.0.1:8000/mcp/"

    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]

            print("MCP_INITIALIZE=SUCCESS")
            print(f"TOOL_COUNT={len(names)}")
            print("TOOLS=" + ",".join(names))

            target = next(tool for tool in tools.tools if tool.name == "hcl_curie_analysis")

            print("HCL_CURIE_DISCOVERED=YES")
            print("INPUT_SCHEMA=")
            print(target.inputSchema)

            result = await session.call_tool(
                "hcl_curie_analysis",
                arguments={
                    "operation": "summarize",
                    "text": (
                        "ToolBridge is an MCP server that exposes validated tools "
                        "and routes LLM analysis through configurable providers."
                    ),
                    "instructions": "Reply in one short sentence.",
                },
            )

            print("TOOL_CALL_IS_ERROR=" + str(result.isError))
            print("TOOL_RESULT=")

            for item in result.content:
                text = getattr(item, "text", None)
                if text:
                    print(text)


if __name__ == "__main__":
    asyncio.run(main())
