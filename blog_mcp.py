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
def save_draft(content: str, filename: str = "", meeting_date: str = "") -> str:
    """Save a blog post draft as a markdown file in the drafts/ folder.
    Always overwrites any existing file with the same name.

    Args:
        content: The full markdown content of the blog post.
        filename: Optional filename (e.g. "2026-03-20-agentic-coding.md").
                  If omitted, defaults to meeting_date (or today) + "-draft.md".
        meeting_date: Optional ISO date of the meeting (e.g. "2026-03-19").
                      Used as the filename prefix when no filename is given,
                      so re-runs of the same meeting always overwrite the same file.
    """
    drafts = pathlib.Path(__file__).parent / "drafts"
    drafts.mkdir(exist_ok=True)
    if not filename:
        date_prefix = meeting_date if meeting_date else datetime.date.today().isoformat()
        filename = date_prefix + "-draft.md"
    if not filename.endswith(".md"):
        filename += ".md"
    out = drafts / filename
    out.write_text(content, encoding="utf-8")
    action = "Overwritten" if out.exists() else "Saved"
    return f"{action}: {out}"


if __name__ == "__main__":
    mcp.run()
