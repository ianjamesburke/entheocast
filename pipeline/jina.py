import subprocess


def fetch_text(url: str, timeout: int = 30) -> str:
    """Fetch full article text via Jina Reader."""
    result = subprocess.run(
        ["curl", "-s", "--compressed", f"https://r.jina.ai/{url}"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Jina fetch failed for {url}: {result.stderr}")
    return result.stdout
