# Contributing

## Development checks

Run the Python tests, JavaScript tests, and Ruff commands from the repository root.

```powershell
uv run --no-project --with pytest --with aiohttp python -m pytest -q
node --test
uvx ruff check .
```

## Comfy Registry publishing

Maintainers publish with Publisher ID `watarika`. Configure the repository secret `REGISTRY_ACCESS_TOKEN` with the Comfy Registry API key; never commit or document its value.

Before publishing, bump the semantic version in `pyproject.toml`. Publishing runs automatically when that file changes on `main`, or maintainers can start it manually through the `Publish to Comfy registry` workflow.
