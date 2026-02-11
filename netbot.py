
import typer
import logging
import json
import os
import sys
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import db

app = typer.Typer(
    help="NetBot CLI - Your second brain and social automation.",
    no_args_is_help=True
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("CLI")

@app.command()
def add_insight(
    text: str = typer.Argument(..., help="The insight or idea text to store.")
):
    """Quickly add an insight or idea to the content pool."""
    try:
        data = {
            "source_url": "cli",
            "title": f"Insight: {text[:50]}...",
            "original_content": text,
            "type": "insight",
            "status": "pending",
            "metadata": {"source": "cli"}
        }
        db.client.table("content_ideas").insert(data).execute()
        typer.echo(f"✅ Insight saved to pool.")
    except Exception as e:
        logger.error(f"Failed to save insight: {e}")

@app.command()
def add_project(
    name: str = typer.Option(..., "--name", "-n", prompt=True),
    stack: str = typer.Option(..., "--stack", "-s", prompt=True),
    phase: str = typer.Option(..., "--phase", "-p", prompt=True),
    challenge: str = typer.Option(..., "--challenge", "-c", prompt=True)
):
    """Add a new project to the database registry."""
    try:
        data = {
            "name": name,
            "stack": stack,
            "phase": phase,
            "recent_challenge": challenge,
            "enabled": True
        }
        db.client.table("projects").insert(data).execute()
        typer.echo(f"✅ Project '{name}' added to database.")
    except Exception as e:
        logger.error(f"Failed to add project: {e}")

@app.command()
def list_projects():
    """List all projects in the database."""
    try:
        res = db.client.table("projects").select("*").execute()
        if not res.data:
            typer.echo("No projects found.")
            return
        
        for p in res.data:
            status = "✅" if p['enabled'] else "❌"
            typer.echo(f"{status} {p['name']} ({p['stack']})")
            typer.echo(f"   Phase: {p['phase']}")
            typer.echo(f"   Challenge: {p['recent_challenge']}")
            typer.echo("-" * 20)
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")

@app.command()
def project_updates(
    force: bool = typer.Option(False, "--force", "-f", help="Force generation even if already done this week.")
):
    """Generate a social media update based on current projects."""
    from scripts.generate_project_updates import ProjectUpdateGenerator
    generator = ProjectUpdateGenerator()
    generator.run(force=force)
    typer.echo("✅ Project update flow completed.")

if __name__ == "__main__":
    app()
