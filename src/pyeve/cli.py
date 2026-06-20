from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="pyeve", description="pyeve agent framework")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Scaffold a new agent directory")
    init_parser.add_argument("name", help="Directory name for the new agent")

    dev_parser = subparsers.add_parser("dev", help="Run agent in development mode with hot reload")
    dev_parser.add_argument("--dir", default="./agent", help="Path to agent directory")
    dev_parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    dev_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")

    args = parser.parse_args()

    if args.command == "init":
        _cmd_init(args.name)
    elif args.command == "dev":
        _cmd_dev(args.dir, args.host, args.port)
    else:
        parser.print_help()
        sys.exit(0)


def _cmd_init(name: str) -> None:
    root = Path(name)
    agent_dir = root / "agent"
    tools_dir = agent_dir / "tools"

    for d in [root, agent_dir, tools_dir]:
        d.mkdir(parents=True, exist_ok=True)

    (agent_dir / "instructions.md").write_text(
        "You are a helpful assistant.\n\n"
        "Use the tools available to you to answer questions accurately.\n"
    )

    (agent_dir / "agent.py").write_text(
        "from pyeve import define_agent\n"
        "from pyeve.adapters.anthropic import AnthropicAdapter\n\n"
        "agent = define_agent(\n"
        '    model="claude-sonnet-4-6",\n'
        "    adapter=AnthropicAdapter(),\n"
        ")\n"
    )

    (tools_dir / "example.py").write_text(
        'async def execute(query: str) -> str:\n'
        '    """Answer a question with a placeholder response."""\n'
        '    return f"You asked: {query}"\n'
    )

    print(f"Created {agent_dir}")
    print(f"  {agent_dir}/instructions.md")
    print(f"  {agent_dir}/agent.py")
    print(f"  {agent_dir}/tools/example.py")
    print(f"\nRun: cd {name} && pyeve dev")


def _run_dev_server(agent_path: str, host: str, port: int) -> None:
    from pyeve import agent
    import uvicorn
    app = agent(agent_path)
    uvicorn.run(app, host=host, port=port, log_level="info")


def _cmd_dev(agent_dir: str, host: str, port: int) -> None:
    try:
        import uvicorn  # noqa: F401
        from watchfiles import run_process
    except ImportError:
        print(
            "pyeve dev requires uvicorn and watchfiles.\n"
            "Install with: pip install uvicorn watchfiles"
        )
        sys.exit(1)

    agent_path = Path(agent_dir).resolve()
    print(f"Starting pyeve dev server on http://{host}:{port}")
    print(f"Watching {agent_path} for changes...")

    run_process(str(agent_path), target=_run_dev_server, args=(str(agent_path), host, port))


if __name__ == "__main__":
    main()
