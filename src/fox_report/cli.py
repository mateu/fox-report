from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from .email.sender import EmailSender
from .report_generator import (
    generate_fox_report,
    get_last_n_nights_data,
)

app = typer.Typer(help="Generate Fox reports")


@app.command(help="Generate a fox detection report and optionally email it.")
def report(
    nights: Annotated[
        int,
        typer.Option("-n", "--nights", help="Number of most recent nights to include"),
    ] = 3,
    email: Annotated[
        str | None,
        typer.Option("-e", "--email", help="Email address to send the report to"),
    ] = None,
    json_out: Annotated[
        Path | None,
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
        # Use simplified EmailSender with optional recipient override
        sender = EmailSender(recipient_override=email)
        # Ensure the optional attachment path is typed as str | None
        attachment: str | None = str(json_out) if json_out else None
        success, _stdout, stderr = sender.send_email(report, markdown, attachment)
        if success:
            typer.secho("Email sent successfully.", fg=typer.colors.GREEN)
        else:
            typer.secho(f"Email send failed: {stderr}", fg=typer.colors.RED)
            raise typer.Exit(code=2)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
