from fastmcp import FastMCP

mcp = FastMCP("Config Example Server")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

if __name__ == "__main__":
    mcp.run(transport="sse")