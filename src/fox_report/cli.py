from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from .report_generator import (
    generate_fox_report,
    get_last_n_nights_data,
)
from .email.sender import EmailSender

app = typer.Typer(help="Generate Fox reports")


@app.command(help="Generate a fox detection report and optionally email it.")
def report(
    nights: Annotated[
        int,
        typer.Option("-n", "--nights", help="Number of most recent nights to include"),
    ] = 3,
    email: Annotated[
        Optional[str],
        typer.Option("-e", "--email", help="Email address to send the report to"),
    ] = None,
    json_out: Annotated[
        Optional[Path],
        typer.Option(
            "--json-out",
            help="Optional path to write the JSON report (defaults to /tmp/fox_report_YYYYMMDD.json)",
        ),
    ] = None,
    html: Annotated[
        bool,
        typer.Option(
            "--html/--text",
            help="Email format when sending (HTML with thumbnails vs. plain text)",
        ),
    ] = True,
) -> None:
    """Generate and optionally e-mail the report."""

    # Resolve time ranges for the requested number of nights
    nights_list, dusk_dawn_ranges = get_last_n_nights_data(nights)
    if not nights_list:
        typer.secho("Could not determine night ranges. Aborting.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Generate the report (optionally writing JSON to disk)
    output_file = str(json_out) if json_out else None
    report, markdown = generate_fox_report(nights_list, dusk_dawn_ranges, output_file)

    # If email address provided, send the report
    if email:
        config = {
            "email": {
                "recipient": email,
                "format": "html" if html else "text",
                # SMTP settings are taken from env or your config file inside EmailSender
                "smtp": {
                    # Leave as-is; EmailSender will validate/use env like GMAIL_APP_PASSWORD
                    "enabled": True,
                    "server": "smtp.gmail.com",
                    "port": 587,
                    "use_tls": True,
                    # username is typically the sender address
                    "username": email,
                },
            }
        }
        sender = EmailSender(config)
        success, _stdout, stderr = sender.send_email(
            report, markdown, json_out and str(json_out)
        )
        if success:
            typer.secho("Email sent successfully.", fg=typer.colors.GREEN)
        else:
            typer.secho(f"Email send failed: {stderr}", fg=typer.colors.RED)
            raise typer.Exit(code=2)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
