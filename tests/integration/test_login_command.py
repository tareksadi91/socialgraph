"""Login command tests — Playwright is mocked, the command's orchestration is verified."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from socialgraph.cli.main import app

runner = CliRunner()


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])


def test_login_x_opens_browser_at_x_url(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    with patch("socialgraph.cli.login_cmd.launch_persistent_browser") as mock_launch:
        context = MagicMock()
        page = MagicMock()
        context.new_page.return_value = page
        mock_launch.return_value.__enter__.return_value = context
        result = runner.invoke(app, ["login", "x"], input="\n")
    assert result.exit_code == 0, result.stdout
    assert page.goto.called
    url_arg = page.goto.call_args[0][0]
    assert "x.com" in url_arg


def test_login_linkedin_opens_at_linkedin_url(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    with patch("socialgraph.cli.login_cmd.launch_persistent_browser") as mock_launch:
        context = MagicMock()
        page = MagicMock()
        context.new_page.return_value = page
        mock_launch.return_value.__enter__.return_value = context
        result = runner.invoke(app, ["login", "linkedin"], input="\n")
    assert result.exit_code == 0
    url_arg = page.goto.call_args[0][0]
    assert "linkedin.com" in url_arg


def test_login_unknown_platform_exits_nonzero(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    result = runner.invoke(app, ["login", "myspace"], input="\n")
    assert result.exit_code != 0


def test_login_uses_profile_dir(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    with patch("socialgraph.cli.login_cmd.launch_persistent_browser") as mock_launch:
        context = MagicMock()
        page = MagicMock()
        context.new_page.return_value = page
        mock_launch.return_value.__enter__.return_value = context
        runner.invoke(app, ["login", "x"], input="\n")
    profile_dir_arg = mock_launch.call_args[0][0]
    assert "profiles" in str(profile_dir_arg)
    assert profile_dir_arg.name == "x"
