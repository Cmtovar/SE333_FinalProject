from fastmcp import FastMCP

from test_tools import (
    analyze_java_file,
    generate_junit_test,
    write_test_file,
    run_maven_tests,
    analyze_coverage_gaps,
    str_replace
)

from git_tools import (
    git_status,
    git_add_all,
    git_commit,
    git_push,
    git_pull_request
)


mcp = FastMCP("Config Example Server")

# Register Maven tools
mcp.tool(analyze_java_file)
mcp.tool(generate_junit_test)
mcp.tool(write_test_file)
mcp.tool(run_maven_tests)
mcp.tool(analyze_coverage_gaps)
mcp.tool(str_replace)

# Register Git tools
mcp.tool(git_status)
mcp.tool(git_add_all)
mcp.tool(git_commit)
mcp.tool(git_push)
mcp.tool(git_pull_request)

# Example custom tool
@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

if __name__ == "__main__":
    mcp.run(transport="sse")