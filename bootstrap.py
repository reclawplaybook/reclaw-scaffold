#!/usr/bin/env python3
"""
bootstrap.py — ReClaw Scaffold Setup Automation
Runs interactively for humans OR non-interactively for agents.

Usage:
  python3 bootstrap.py                  # interactive (human)
  python3 bootstrap.py --agent          # non-interactive (agent, uses env vars)

Agent env vars:
  RECLAW_OWNER_NAME, RECLAW_AGENT_NAME, RECLAW_DISCORD_TOKEN,
  RECLAW_DISCORD_GUILD_ID, RECLAW_INSTALL_DIR (default: ~/my-reclaw)
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path


SCAFFOLD_URL = "https://github.com/reclawplaybook/reclaw-scaffold.git"
DEFAULT_INSTALL_DIR = Path.home() / "my-reclaw"
AGENT_SETUP_URL = "https://raw.githubusercontent.com/reclawplaybook/reclaw-scaffold/master/AGENT_SETUP.md"


def run(cmd, check=True, capture=False):
    """Run a shell command. Returns CompletedProcess."""
    kwargs = {"shell": True, "text": True}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    return subprocess.run(cmd, check=check, **kwargs)


def check_prereqs():
    """Verify Python version and required tools. Returns list of failures."""
    failures = []

    # Python version
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        failures.append(f"Python 3.10+ required, found {v.major}.{v.minor}")

    # git
    result = run("git --version", check=False, capture=True)
    if result.returncode != 0:
        failures.append("git not found — install with: sudo apt-get install git")

    # pip
    result = run("pip3 --version", check=False, capture=True)
    if result.returncode != 0:
        failures.append("pip3 not found — install with: sudo apt-get install python3-pip")

    return failures


def prompt(question, default=None, agent_env_var=None, agent_mode=False):
    """Get input from user or env var in agent mode."""
    if agent_mode and agent_env_var:
        val = os.environ.get(agent_env_var, "")
        if val:
            print(f"  {question}: {val} [from env]")
            return val

    if default:
        display = f"{question} [{default}]: "
    else:
        display = f"{question}: "

    try:
        val = input(display).strip()
        return val if val else (default or "")
    except (EOFError, KeyboardInterrupt):
        print()
        return default or ""


def clone_scaffold(install_dir: Path):
    """Clone the scaffold repo."""
    if install_dir.exists():
        print(f"  Directory {install_dir} already exists — skipping clone.")
        return True

    print(f"  Cloning scaffold to {install_dir}...")
    result = run(f"git clone {SCAFFOLD_URL} {install_dir}", check=False)
    if result.returncode != 0:
        print(f"  ERROR: Clone failed. Check network and try again.")
        return False

    main_py = install_dir / "src" / "main.py"
    if not main_py.exists():
        print(f"  ERROR: Clone appeared to succeed but src/main.py not found.")
        return False

    print("  Clone OK.")
    return True


def install_dependencies(install_dir: Path):
    """Run pip install -r requirements.txt."""
    req_file = install_dir / "requirements.txt"
    if not req_file.exists():
        print("  WARNING: requirements.txt not found — skipping pip install.")
        return

    print("  Installing dependencies...")
    result = run(f"pip3 install -r {req_file}", check=False)
    if result.returncode != 0:
        print("  WARNING: pip install had errors. Check output above.")
    else:
        print("  Dependencies installed.")


def setup_templates(install_dir: Path, owner_name: str, agent_name: str):
    """Copy templates and fill in name placeholders."""
    templates_dir = install_dir / "templates"
    workspace_dir = install_dir / "workspace"
    workspace_dir.mkdir(exist_ok=True)

    template_files = ["USER.md", "SOUL.md", "AGENTS.md", "DIRECTIVE.md"]
    for fname in template_files:
        src = templates_dir / fname
        dst = workspace_dir / fname
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)
            print(f"  Copied templates/{fname} → workspace/{fname}")

    # Fill placeholders in USER.md
    user_md = workspace_dir / "USER.md"
    if user_md.exists():
        content = user_md.read_text()
        content = content.replace("[Your Name]", owner_name)
        content = content.replace("[OWNER_NAME]", owner_name)
        user_md.write_text(content)

    # Fill placeholders in SOUL.md
    soul_md = workspace_dir / "SOUL.md"
    if soul_md.exists():
        content = soul_md.read_text()
        content = content.replace("[Your agent's name]", agent_name)
        content = content.replace("[AGENT_NAME]", agent_name)
        soul_md.write_text(content)


def setup_env(install_dir: Path, discord_token: str, guild_id: str):
    """Create .env from .env.example and write credentials."""
    env_example = install_dir / ".env.example"
    env_file = install_dir / ".env"

    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
        else:
            # Create minimal .env
            env_file.write_text(
                "DISCORD_BOT_TOKEN=\nDISCORD_GUILD_ID=\n"
                "OPENCLAW_USE_SDK=true\nOPENCLAW_PROXY_URL=http://127.0.0.1:3456\n"
            )

    content = env_file.read_text()

    def set_env_var(content, key, value):
        import re
        pattern = rf"^{key}=.*$"
        replacement = f"{key}={value}"
        if re.search(pattern, content, re.MULTILINE):
            return re.sub(pattern, replacement, content, flags=re.MULTILINE)
        return content + f"\n{key}={value}\n"

    if discord_token:
        content = set_env_var(content, "DISCORD_BOT_TOKEN", discord_token)
    if guild_id:
        content = set_env_var(content, "DISCORD_GUILD_ID", guild_id)

    env_file.write_text(content)
    env_file.chmod(0o600)  # Restrict permissions on .env
    print(f"  .env written to {env_file}")


def install_systemd_service(install_dir: Path):
    """Attempt systemd service install. Silently skip if unavailable."""
    service_src = install_dir / "systemd" / "openclaw.service"
    if not service_src.exists():
        return False

    result = run("systemctl --version", check=False, capture=True)
    if result.returncode != 0:
        return False

    service_dst = Path("/etc/systemd/system/reclaw.service")
    try:
        content = service_src.read_text()
        content = content.replace("/home/USER", str(Path.home()))
        content = content.replace("User=USER", f"User={os.environ.get('USER', 'ubuntu')}")
        content = content.replace("~/my-reclaw", str(install_dir))

        run(f"sudo tee {service_dst} > /dev/null << 'HEREDOC'\n{content}\nHEREDOC", check=False)
        run("sudo systemctl daemon-reload", check=False)
        run("sudo systemctl enable reclaw.service", check=False)
        run("sudo systemctl start reclaw.service", check=False)
        return True
    except Exception as e:
        print(f"  WARNING: systemd install failed: {e}")
        return False


def print_summary(install_dir: Path, owner_name: str, agent_name: str,
                  has_token: bool, service_installed: bool):
    """Print what was done and what manual steps remain."""
    print("\n" + "=" * 60)
    print("RECLAW SETUP SUMMARY")
    print("=" * 60)
    print(f"Install directory : {install_dir}")
    print(f"Owner name        : {owner_name or '[not set]'}")
    print(f"Agent name        : {agent_name or '[not set]'}")
    print(f"Discord token     : {'set' if has_token else 'MISSING'}")
    print(f"systemd service   : {'installed + started' if service_installed else 'not installed'}")

    print("\nMANUAL STEPS REMAINING:")

    if not has_token:
        print("  1. Create Discord bot:")
        print("     https://discord.com/developers/applications")
        print("     → New Application → Bot → Reset Token → copy token")
        print("     → Enable MESSAGE CONTENT INTENT")
        print(f"     → Add token to {install_dir}/.env as DISCORD_BOT_TOKEN")
        print(f"     → Add guild ID to {install_dir}/.env as DISCORD_GUILD_ID")
        print()

    print(f"  2. Personalize workspace files:")
    print(f"     {install_dir}/workspace/USER.md  — fill in your info")
    print(f"     {install_dir}/workspace/SOUL.md  — customize agent personality")
    print()

    if not service_installed:
        print("  3. Start the agent:")
        print(f"     cd {install_dir} && python3 src/main.py")
        print("     OR for background:")
        print(f"     nohup python3 {install_dir}/src/main.py >> {install_dir}/workspace/logs/agent.log 2>&1 &")
        print()

    print(f"  4. Verify heartbeat (wait ~2 min after start):")
    print(f"     cat {install_dir}/workspace/memory/heartbeat.log")
    print()
    print("  5. For agent-driven setup, feed this to your agent:")
    print(f"     curl -s {AGENT_SETUP_URL}")
    print()
    print("=" * 60)


def main():
    agent_mode = "--agent" in sys.argv

    print("ReClaw Scaffold Bootstrap")
    print("-" * 40)

    # Prerequisites
    print("\n[1/6] Checking prerequisites...")
    failures = check_prereqs()
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        if any("Python" in f for f in failures):
            sys.exit(1)
    else:
        print("  All prerequisites met.")

    # Install directory
    install_dir_str = os.environ.get("RECLAW_INSTALL_DIR", str(DEFAULT_INSTALL_DIR))
    if not agent_mode:
        install_dir_str = prompt(
            "Install directory", default=install_dir_str
        )
    install_dir = Path(install_dir_str).expanduser().resolve()

    # Clone
    print(f"\n[2/6] Cloning scaffold...")
    if not clone_scaffold(install_dir):
        print("Clone failed. Exiting.")
        sys.exit(1)

    # Dependencies
    print("\n[3/6] Installing dependencies...")
    install_dependencies(install_dir)

    # User info
    print("\n[4/6] Gathering configuration...")
    owner_name = prompt("Your name (for USER.md)", default="[OWNER_NAME]",
                        agent_env_var="RECLAW_OWNER_NAME", agent_mode=agent_mode)
    agent_name = prompt("Agent name (e.g. ReClaw, Hermes, Atlas)", default="ReClaw",
                        agent_env_var="RECLAW_AGENT_NAME", agent_mode=agent_mode)
    discord_token = prompt("Discord bot token (leave blank to set manually later)", default="",
                           agent_env_var="RECLAW_DISCORD_TOKEN", agent_mode=agent_mode)
    guild_id = prompt("Discord guild/server ID (leave blank to set manually later)", default="",
                      agent_env_var="RECLAW_DISCORD_GUILD_ID", agent_mode=agent_mode)

    # Templates and .env
    print("\n[5/6] Writing configuration files...")
    setup_templates(install_dir, owner_name, agent_name)
    setup_env(install_dir, discord_token, guild_id)

    # Service
    print("\n[6/6] Installing systemd service (if available)...")
    service_installed = install_systemd_service(install_dir)
    if not service_installed:
        print("  systemd not available or install skipped — start manually (see summary).")

    # Summary
    print_summary(
        install_dir=install_dir,
        owner_name=owner_name,
        agent_name=agent_name,
        has_token=bool(discord_token),
        service_installed=service_installed,
    )


if __name__ == "__main__":
    main()
