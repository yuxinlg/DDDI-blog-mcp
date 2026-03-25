from mcp.server.fastmcp import FastMCP
import re, pathlib, datetime

mcp = FastMCP("blog-generator")


@mcp.tool()
def parse_transcript(vtt_path: str) -> str:
    """Parse a Zoom .vtt transcript file into clean speaker-labeled text.

    Args:
        vtt_path: Absolute path to a .vtt transcript file from Zoom.
    """
    text = pathlib.Path(vtt_path).expanduser().read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^\d+$", stripped):
            continue  # sequence numbers
        if re.match(r"[\d:.]+ --> ", stripped):
            continue  # timestamps
        if stripped in ("", "WEBVTT"):
            continue
        lines.append(stripped)
    return "\n".join(lines)


@mcp.tool()
def save_draft(content: str, filename: str = "") -> str:
    """Save a blog post draft as a markdown file in the drafts/ folder.

    Args:
        content: The full markdown content of the blog post.
        filename: Optional filename (e.g. "2026-03-20-agentic-coding.md").
                  Defaults to today's date + "-draft.md".
    """
    drafts = pathlib.Path(__file__).parent / "drafts"
    drafts.mkdir(exist_ok=True)
    if not filename:
        filename = datetime.date.today().isoformat() + "-draft.md"
    if not filename.endswith(".md"):
        filename += ".md"
    out = drafts / filename
    out.write_text(content, encoding="utf-8")
    return f"Draft saved to: {out}"


if __name__ == "__main__":
    mcp.run()
