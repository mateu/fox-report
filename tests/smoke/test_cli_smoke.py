from typer.testing import CliRunner

from fox_report.cli import app


def test_cli_help_runs():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout
