"""Typer CLI for ReguTrack."""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

app = typer.Typer(
    name="regutrack",
    help="🏛️  ReguTrack — Sistema de monitoreo normativo colombiano",
    add_completion=False,
)
console = Console()


# ---------------------------------------------------------------------------
# Helper: setup logging
# ---------------------------------------------------------------------------

def _setup_logging(level: str = "INFO") -> None:
    from regutrack.config import settings
    import os

    os.makedirs(settings.log_dir, exist_ok=True)
    log_file = os.path.join(
        settings.log_dir, f"regutrack_{datetime.now().strftime('%Y%m%d')}.log"
    )
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


# ---------------------------------------------------------------------------
# DB commands
# ---------------------------------------------------------------------------

@app.command("db")
def db_cmd(
    action: str = typer.Argument(..., help="Action: init | status"),
    reset: bool = typer.Option(False, "--reset", help="Drop and recreate all tables"),
) -> None:
    """Database management commands."""
    _setup_logging()
    from regutrack.database import init_db

    if action == "init":
        if reset:
            confirm = typer.confirm(
                "⚠️  This will DELETE all data. Continue?", default=False
            )
            if not confirm:
                rprint("[yellow]Cancelled.[/yellow]")
                raise typer.Exit()
        init_db(reset=reset)
        rprint("[green]✓ Database initialized successfully.[/green]")
    elif action == "status":
        from regutrack.database import engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        rprint(f"[cyan]Database:[/cyan] {engine.url}")
        rprint(f"[cyan]Tables:[/cyan] {', '.join(tables) if tables else 'None (run db init)'}")
    else:
        rprint(f"[red]Unknown action: {action}. Use init or status.[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Run commands
# ---------------------------------------------------------------------------

@app.command("run-all")
def run_all(
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Run all configured scrapers now."""
    _setup_logging(log_level)
    from regutrack.scrapers import ALL_SCRAPERS
    from regutrack.database import get_session
    from regutrack.notifier import notify_new_documents
    from regutrack.models import Document, Entity

    async def _run():
        results = []
        for scraper_cls in ALL_SCRAPERS:
            scraper = scraper_cls()
            rprint(f"[cyan]→ Scraping:[/cyan] {scraper.entity_name}")
            with get_session() as session:
                result = await scraper.run(session)
                if result.new_documents > 0:
                    entity = session.query(Entity).filter_by(name=scraper.entity_name).first()
                    if entity:
                        new_docs = (
                            session.query(Document)
                            .filter_by(entity_id=entity.id, is_new=True)
                            .all()
                        )
                        notify_new_documents(new_docs, scraper.entity_name)
                icon = "✓" if result.status == "success" else "✗"
                color = "green" if result.status == "success" else "red"
                rprint(
                    f"  [{color}]{icon}[/{color}] {result.entity_name}: "
                    f"{result.new_documents} nuevos / {result.total_fetched} total"
                )
                results.append(result)
        return results

    results = asyncio.run(_run())

    total_new = sum(r.new_documents for r in results)
    total_ok = sum(1 for r in results if r.status == "success")
    rprint(
        f"\n[bold]Resumen:[/bold] {total_ok}/{len(results)} entidades OK, "
        f"[bold green]{total_new}[/bold green] documentos nuevos"
    )


@app.command("run")
def run_one(
    entity: str = typer.Option(..., "--entity", "-e", help="Scraper entity key (e.g. anh)"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Run a single scraper by entity key."""
    _setup_logging(log_level)
    from regutrack.scrapers import SCRAPERS_BY_KEY
    from regutrack.database import get_session
    from regutrack.notifier import notify_new_documents
    from regutrack.models import Document, Entity

    scraper_cls = SCRAPERS_BY_KEY.get(entity.lower())
    if not scraper_cls:
        available = ", ".join(sorted(SCRAPERS_BY_KEY.keys()))
        rprint(f"[red]Entity '{entity}' not found.[/red]")
        rprint(f"Available: {available}")
        raise typer.Exit(1)

    async def _run():
        scraper = scraper_cls()
        with get_session() as session:
            result = await scraper.run(session)
            if result.new_documents > 0:
                ent = session.query(Entity).filter_by(name=scraper.entity_name).first()
                if ent:
                    new_docs = (
                        session.query(Document).filter_by(entity_id=ent.id, is_new=True).all()
                    )
                    notify_new_documents(new_docs, scraper.entity_name)
        return result

    result = asyncio.run(_run())
    icon = "✓" if result.status == "success" else "✗"
    color = "green" if result.status == "success" else "red"
    rprint(
        f"[{color}]{icon}[/{color}] {result.entity_name}: "
        f"{result.new_documents} nuevos / {result.total_fetched} total"
    )
    if result.error_message:
        rprint(f"[red]Error: {result.error_message}[/red]")


# ---------------------------------------------------------------------------
# Show new documents
# ---------------------------------------------------------------------------

@app.command("show-new")
def show_new(
    days: int = typer.Option(7, "--days", "-d", help="Look back N days"),
    entity: Optional[str] = typer.Option(None, "--entity", "-e", help="Filter by entity key"),
) -> None:
    """Show new regulatory documents found in the last N days."""
    from regutrack.database import get_session
    from regutrack.models import Document, Entity

    cutoff = datetime.utcnow() - timedelta(days=days)

    with get_session() as session:
        query = session.query(Document).filter(Document.first_seen_at >= cutoff)

        if entity:
            from regutrack.scrapers import SCRAPERS_BY_KEY
            scraper_cls = SCRAPERS_BY_KEY.get(entity.lower())
            if scraper_cls:
                ent_obj = session.query(Entity).filter_by(
                    name=scraper_cls.entity_name
                ).first()
                if ent_obj:
                    query = query.filter(Document.entity_id == ent_obj.id)

        docs = query.order_by(Document.first_seen_at.desc()).all()

        if not docs:
            rprint(f"[yellow]No new documents found in the last {days} day(s).[/yellow]")
            return

        table = Table(title=f"Nuevas normas — últimos {days} día(s)", show_lines=True)
        table.add_column("Entidad", style="cyan", no_wrap=True)
        table.add_column("Tipo", style="magenta")
        table.add_column("Número")
        table.add_column("Título", max_width=50)
        table.add_column("Fecha pub.")
        table.add_column("Detectado")

        for doc in docs:
            ent = session.query(Entity).filter_by(id=doc.entity_id).first()
            table.add_row(
                ent.name if ent else "?",
                doc.doc_type or "—",
                doc.number or "—",
                doc.title[:80],
                str(doc.publication_date or "—"),
                doc.first_seen_at.strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)


# ---------------------------------------------------------------------------
# Scheduler daemon
# ---------------------------------------------------------------------------

@app.command("scheduler")
def scheduler_cmd(
    action: str = typer.Argument(..., help="Action: start"),
) -> None:
    """Start the daily scheduler daemon."""
    if action != "start":
        rprint(f"[red]Unknown action: {action}. Use 'start'.[/red]")
        raise typer.Exit(1)

    _setup_logging()
    from regutrack.scheduler import create_scheduler
    import time

    rprint("[bold green]🕐 ReguTrack Scheduler started.[/bold green]")
    rprint(f"Daily run at [cyan]{__import__('regutrack.config', fromlist=['settings']).settings.scheduler_hour:02d}:{__import__('regutrack.config', fromlist=['settings']).settings.scheduler_minute:02d}[/cyan] (America/Bogota)")
    rprint("Press Ctrl+C to stop.\n")

    scheduler = create_scheduler()
    scheduler.start()

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        rprint("\n[yellow]Scheduler stopped.[/yellow]")


# ---------------------------------------------------------------------------
# List entities
# ---------------------------------------------------------------------------

@app.command("list-entities")
def list_entities() -> None:
    """List all configured scraper entities."""
    from regutrack.scrapers import ALL_SCRAPERS

    table = Table(title="Entidades configuradas", show_lines=True)
    table.add_column("Clave", style="cyan")
    table.add_column("Entidad")
    table.add_column("Grupo", style="magenta")
    table.add_column("URL")
    table.add_column("JS?", justify="center")

    for cls in sorted(ALL_SCRAPERS, key=lambda c: (c.entity_group, c.entity_name)):
        # Derive the key from the class name
        from regutrack.scrapers import SCRAPERS_BY_KEY
        key = next((k for k, v in SCRAPERS_BY_KEY.items() if v is cls), cls.__name__)
        table.add_row(
            key,
            cls.entity_name,
            cls.entity_group,
            cls.entity_url,
            "✓" if cls.requires_js else "—",
        )

    console.print(table)


if __name__ == "__main__":
    app()
