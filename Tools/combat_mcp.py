from mcp.server.fastmcp import FastMCP
import combat_remote

mcp = FastMCP('Combat UE Editor')

@mcp.tool()
def status() -> dict:
    """Report project identity, engine version and PIE state of this Combat editor."""
    return combat_remote.status()

@mcp.tool()
def run_python(code: str) -> dict:
    """Execute Python in the matching local Combat editor. Mutates the project if the script requests it."""
    return combat_remote.execute(code)

@mcp.tool()
def list_assets(path: str = '/Game') -> dict:
    """List Unreal assets recursively below a package path."""
    return combat_remote.list_assets(path)

@mcp.tool()
def pie(action: str = 'status') -> dict:
    """Start, stop, or query play in editor."""
    return combat_remote.pie(action)

if __name__ == '__main__':
    mcp.run(transport='stdio')
