"""Application entrypoint."""

from configguardian.cli import app


def main() -> None:
    """Run the ConfigGuardian CLI application."""
    app()


if __name__ == "__main__":
    main()

