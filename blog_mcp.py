from mcp.server.fastmcp import FastMCP
import re, pathlib, datetime, subprocess

mcp = FastMCP("blog-generator")

BLOG_REPO = pathlib.Path.home() / "DDDI_DP_Blog"


def _parse_vtt(vtt_path: str) -> str:
    """Internal helper: parse a single .vtt file into clean text."""
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


def _date_from_path(vtt_path: str) -> str:
    """Extract ISO date from a VTT filename like GMT20260319-*.vtt → '2026-03-19'."""
    name = pathlib.Path(vtt_path).name
    m = re.search(r"GMT(\d{4})(\d{2})(\d{2})", name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return pathlib.Path(vtt_path).parent.name  # fall back to folder name


@mcp.tool()
def parse_transcript(vtt_path: str, vtt_path2: str = "") -> str:
    """Parse one or two Zoom .vtt transcript files into clean labeled text.

    When two paths are provided the output is clearly separated by date so
    Claude can identify overlapping topics and distribute content evenly:
    Date1 content fully included; Date2 contributes only what is new
    (Date2 \\ Date1 in topic space).

    Args:
        vtt_path:  Absolute path to the first .vtt transcript file.
        vtt_path2: Optional absolute path to a second .vtt transcript file.
                   When supplied, both transcripts are returned labeled by date.
    """
    date1 = _date_from_path(vtt_path)
    text1 = _parse_vtt(vtt_path)

    if not vtt_path2:
        return text1

    date2 = _date_from_path(vtt_path2)
    text2 = _parse_vtt(vtt_path2)

    separator = "=" * 60
    return (
        f"{separator}\n"
        f"TRANSCRIPT 1 — {date1}\n"
        f"{separator}\n"
        f"{text1}\n\n"
        f"{separator}\n"
        f"TRANSCRIPT 2 — {date2}\n"
        f"{separator}\n"
        f"{text2}"
    )


@mcp.tool()
def save_draft(content: str, filename: str = "", meeting_date: str = "", save_raw: bool = True) -> str:
    """Save a blog post draft as a markdown file in the drafts/ folder.
    Always overwrites the working copy. Optionally saves a raw reference copy
    that is never overwritten on re-runs (for side-by-side comparison).

    Args:
        content: The full markdown content of the blog post.
        filename: Optional filename (e.g. "2026-03-20-agentic-coding.md").
                  If omitted, defaults to meeting_date (or today) + "-draft.md".
        meeting_date: Optional ISO date of the meeting (e.g. "2026-03-19").
                      Used as the filename prefix when no filename is given,
                      so re-runs of the same meeting always overwrite the same file.
        save_raw: If True (default), also saves an untouched copy to drafts/raw/
                  the first time — never overwritten, for reference/comparison.
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
    msg = f"Draft saved: {out}"

    if save_raw:
        raw_dir = drafts / "raw"
        raw_dir.mkdir(exist_ok=True)
        raw_out = raw_dir / filename
        if not raw_out.exists():  # never overwrite raw — it's the reference copy
            raw_out.write_text(content, encoding="utf-8")
            msg += f"\nRaw reference copy saved: {raw_out}"
        else:
            msg += f"\nRaw reference copy already exists (not overwritten): {raw_out}"

    return msg


@mcp.tool()
def publish_to_blog(
    draft_filename: str,
    post_slug: str,
    post_title: str,
    post_subtitle: str = "",
    author_name: str = "DDDI AI Fellow Gathering",
    author_url: str = "",
    author_pic: str = "/assets/images/authors/dddi.png",
    author_title: str = "Postdoctoral Researchers, DDDI",
    summary: str = "",
    meeting_date: str = "",
) -> str:
    """Copy a reviewed draft to DDDI_DP_Blog, inject Jekyll frontmatter,
    create a post/YYYY-MM-DD-slug branch, push, and open a draft PR.

    Args:
        draft_filename: Filename in drafts/ (e.g. "2026-03-19-draft.md")
        post_slug: URL-friendly slug (e.g. "agentic-coding-postdocs")
        post_title: Full post title
        post_subtitle: Optional subtitle
        author_name: Display name — use "DDDI AI Fellow Gathering" for group posts
        author_url: URL for author link (leave blank if none)
        author_pic: Path to author photo in assets/images/authors/
        author_title: Author credentials line
        summary: 1-2 sentence summary for the homepage card
        meeting_date: ISO date of the meeting (e.g. "2026-03-19"), used for branch/filename
    """
    drafts = pathlib.Path(__file__).parent / "drafts"
    draft_path = drafts / draft_filename
    content = draft_path.read_text(encoding="utf-8")

    # Strip existing H1 title from draft (Jekyll renders title from frontmatter)
    lines = content.splitlines()
    if lines and lines[0].startswith("# "):
        content = "\n".join(lines[1:]).lstrip("\n")

    date_prefix = meeting_date if meeting_date else datetime.date.today().isoformat()
    post_filename = f"{date_prefix}-{post_slug}.md"
    branch = f"post/{date_prefix}-{post_slug}"

    # Guard: refuse to proceed if the branch already exists locally or remotely
    existing_local = subprocess.run(
        ["git", "-C", str(BLOG_REPO), "branch", "--list", branch],
        capture_output=True, text=True
    ).stdout.strip()
    existing_remote = subprocess.run(
        ["git", "-C", str(BLOG_REPO), "ls-remote", "--heads", "origin", branch],
        capture_output=True, text=True
    ).stdout.strip()
    if existing_local or existing_remote:
        return (
            f"⛔ Branch '{branch}' already exists "
            f"({'locally' if existing_local else ''}{'and ' if existing_local and existing_remote else ''}{'on remote' if existing_remote else ''}).\n"
            f"This post has already been published. To avoid duplicates, no action was taken.\n"
            f"If you want to update the post, edit the file directly on that branch and push:\n"
            f"  git -C ~/DDDI_DP_Blog checkout {branch}\n"
            f"  # edit _posts/{post_filename}, then:\n"
            f"  git add _posts/{post_filename} && git commit -m 'Update draft' && git push"
        )

    author_link = f"[{author_name}]({author_url})" if author_url else author_name

    frontmatter = f"""---
layout: blog
title: "{post_title}"
subtitle: "{post_subtitle}"
authors: ["{author_link}"]
author_pic: ["{author_pic}"]
author_title: ["{author_title}"]
date: {date_prefix}
permalink: /{post_slug}/
summary: "{summary}"
---
"""
    final_content = frontmatter + "\n" + content
    post_path = BLOG_REPO / "_posts" / post_filename

    def git(args):
        subprocess.run(["git", "-C", str(BLOG_REPO)] + args, check=True)

    git(["checkout", "main"])
    git(["pull", "origin", "main"])
    git(["checkout", "-b", branch])
    post_path.write_text(final_content, encoding="utf-8")
    git(["add", str(post_path)])
    git(["commit", "-m", f"Draft post: {post_title}"])
    git(["push", "-u", "origin", branch])

    result = subprocess.run(
        [
            "gh", "pr", "create",
            "--title", f"Post: {post_title}",
            "--body", f"Auto-generated from Zoom transcript ({meeting_date}). Ready for editing.\n\n**Checklist before merging:**\n- [ ] Review and edit content\n- [ ] Add author photo to `assets/images/authors/` if needed\n- [ ] Add cover image to `assets/images/posts/`\n- [ ] Update `permalink` and `summary` in frontmatter\n- [ ] Update homepage `featured_posts` in `index.md` if featuring this post",
            "--draft",
            "--repo", "dddiscovery/datapoints",
        ],
        capture_output=True, text=True, cwd=str(BLOG_REPO)
    )
    pr_url = result.stdout.strip()
    return (
        f"Branch created: {branch}\n"
        f"Post file: {post_path}\n"
        f"Draft PR: {pr_url}\n\n"
        f"Next steps:\n"
        f"  1. Open the PR and edit the post in Cursor on branch '{branch}'\n"
        f"  2. Add cover image to DDDI_DP_Blog/assets/images/posts/\n"
        f"  3. Mark PR ready → merge to main when satisfied"
    )


if __name__ == "__main__":
    mcp.run()
