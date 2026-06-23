from mcp.server.fastmcp import FastMCP
import re, pathlib, datetime, subprocess, concurrent.futures
from pypdf import PdfReader

mcp = FastMCP("blog-generator")

BLOG_REPO = pathlib.Path.home() / "DDDI_DP_Blog"
EVENTS_ROOT = pathlib.Path.home() / "Dropbox" / "DDDI" / "Events"


# Stop words: standard English function words + speech fillers/connectors.
# Content words (nouns, main verbs, adjectives, domain terms) are always kept.
STOP_WORDS = frozenset({
    # Articles & determiners
    "a", "an", "the", "this", "that", "these", "those", "some", "any", "each",
    "every", "all", "both", "few", "more", "most", "other", "such", "no",
    # Prepositions
    "in", "on", "at", "by", "for", "with", "about", "against", "between",
    "into", "through", "during", "before", "after", "above", "below",
    "to", "from", "up", "down", "out", "off", "over", "under", "of", "as",
    "per", "via", "upon", "within", "without", "among", "along", "across",
    "behind", "beyond", "beside", "towards", "toward", "onto", "except",
    # Coordinating & subordinating conjunctions
    "and", "but", "or", "nor", "so", "yet", "either", "neither",
    "although", "because", "since", "while", "if", "unless", "until",
    "when", "where", "whereas", "whether", "though", "even",
    # Relative & interrogative pronouns (function use)
    "who", "whom", "which", "what", "whose",
    # Personal pronouns
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    # Auxiliary & modal verbs
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    # Contractions
    "it's", "that's", "there's", "here's", "i'm", "i've", "i'd", "i'll",
    "we're", "we've", "we'd", "we'll", "they're", "they've", "they'd",
    "you're", "you've", "you'd", "you'll", "he's", "she's", "isn't",
    "aren't", "wasn't", "weren't", "haven't", "hasn't", "hadn't",
    "don't", "doesn't", "didn't", "won't", "wouldn't", "couldn't",
    "shouldn't", "can't", "let's",
    # Common function adverbs & discourse connectors
    "very", "too", "quite", "just", "also", "here", "there", "then",
    "than", "further", "once", "own", "same", "however", "therefore",
    "thus", "hence", "accordingly", "consequently", "meanwhile",
    "moreover", "furthermore", "nevertheless", "nonetheless",
    "not", "only", "already", "still", "yet", "now", "again",
    "always", "never", "often", "usually", "sometimes", "perhaps",
    "maybe", "certainly", "indeed", "instead", "otherwise", "rather",
    # Speech fillers & hedges (no semantic content in transcripts)
    "um", "uh", "ah", "oh", "hmm", "mm", "mhm", "huh",
    "yeah", "yep", "yup", "nope", "okay", "ok", "alright", "right",
    "well", "anyway", "so", "like", "actually", "basically", "literally",
    "essentially", "generally", "really", "totally", "absolutely",
    "honestly", "obviously", "clearly", "certainly", "exactly", "precisely",
    "kind", "sort",   # as in "kind of", "sort of"
    "mean",           # as in "I mean"
    "know",           # as in "you know"
    "going", "gonna", "wanna",
})


def _filter_words(text: str) -> str:
    """Strip stop words from a string, preserving original word forms."""
    words = text.split()
    kept = [w for w in words
            if w.lower().strip('.,!?;:"\'''`()-–—[]{}') not in STOP_WORDS
            and w.lower().strip('.,!?;:"\'''`()-–—[]{}')]
    return " ".join(kept)


def _remove_stop_words(text: str) -> tuple[str, int, int]:
    """Remove stop words and fillers from transcript text.

    Also merges consecutive lines from the same speaker into a single paragraph —
    Zoom transcripts often split one person's speech across many short lines.
    Merging dramatically reduces line count without losing any content.

    Preserves speaker name labels (e.g. "Mike: ...").
    Returns: (compressed_text, original_word_count, compressed_word_count)
    """
    original_word_count = len(text.split())

    # Parse each line into (speaker, content) pairs
    parsed = []
    for line in text.splitlines():
        m = re.match(r"^([A-Za-z][^:]{0,40}):\s+", line)
        if m:
            parsed.append((m.group(1).strip(), line[len(m.group(0)):]))
        else:
            parsed.append(("", line))

    # Merge consecutive lines from the same speaker, capped at ~80 words per paragraph
    # so the output stays structured and Claude can follow topic shifts.
    MAX_PARA_WORDS = 80
    merged = []
    for speaker, content in parsed:
        if (merged and merged[-1][0] == speaker
                and len(merged[-1][1].split()) < MAX_PARA_WORDS):
            merged[-1] = (speaker, merged[-1][1] + " " + content)
        else:
            merged.append([speaker, content])

    # Apply stop word filter to each merged utterance
    result_lines = []
    for speaker, content in merged:
        filtered = _filter_words(content)
        if filtered:
            prefix = f"{speaker}: " if speaker else ""
            result_lines.append(prefix + filtered)

    compressed = "\n".join(result_lines)
    compressed_word_count = len(compressed.split())
    return compressed, original_word_count, compressed_word_count


def _parse_vtt(vtt_path: str) -> str:
    """Parse a .vtt file into clean, stop-word-compressed text.

    Step 1: Strip VTT markup (sequence numbers, timestamps, blank lines).
    Step 2: Remove stop words, fillers, and connectors from every line —
            preserving all content words, speaker labels, and line structure.
            No lines are dropped or reordered; no information is sampled away.
    """
    text = pathlib.Path(vtt_path).expanduser().read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^\d+$", stripped):
            continue
        if re.match(r"[\d:.]+ --> ", stripped):
            continue
        if stripped in ("", "WEBVTT"):
            continue
        lines.append(stripped)

    raw_text = "\n".join(lines)
    compressed, orig_words, comp_words = _remove_stop_words(raw_text)
    reduction_pct = int(100 * (1 - comp_words / orig_words)) if orig_words else 0

    note = (
        f"[TRANSCRIPT STATS: {orig_words:,} words → {comp_words:,} words after stop-word removal "
        f"({reduction_pct}% reduction). All content words and speaker turns preserved.]\n\n"
    )
    return note + compressed


def _parse_pdf_worker(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(f"[Page {i}]\n{text}")
    return "\n\n".join(pages)


def _parse_pdf(pdf_path: str, timeout: int = 15) -> str:
    """Extract text from a PDF with a timeout, then apply stop word removal.
    Returns a warning string if the PDF hangs or fails.
    """
    p = str(pathlib.Path(pdf_path).expanduser())
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(_parse_pdf_worker, p)
        try:
            raw = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return f"[PDF parsing timed out after {timeout}s — skipped: {pathlib.Path(p).name}]"
        except Exception as e:
            return f"[PDF parsing failed: {e}]"

    # Apply stop word removal page by page to preserve page markers
    compressed_pages = []
    for block in raw.split("\n\n"):
        if block.startswith("[Page "):
            header, _, body = block.partition("\n")
            compressed_pages.append(header + "\n" + _filter_words(body))
        else:
            filtered = _filter_words(block)
            if filtered:
                compressed_pages.append(filtered)
    return "\n\n".join(compressed_pages)


def _resolve_vtt(path: str) -> pathlib.Path:
    """Accept either a .vtt file path or an event folder path.
    If a folder is given, find the first *.transcript.vtt inside it.
    Also searches one level deep (for AI-Fellow-Meetup/<Date>/ sub-structure).
    """
    p = pathlib.Path(path).expanduser()
    if p.is_file():
        return p
    # Direct match in folder
    vtts = sorted(p.glob("*.transcript.vtt"))
    if vtts:
        return vtts[0]
    # One level deeper (e.g. AI-Fellow-Meetup/Mar19, 2026/)
    vtts = sorted(p.glob("*/*.transcript.vtt"))
    if vtts:
        return vtts[0]
    raise FileNotFoundError(f"No *.transcript.vtt found in {p}")


def _find_pdfs(folder: pathlib.Path) -> list[pathlib.Path]:
    """Return all PDFs in the same folder as the transcript."""
    return sorted(folder.glob("*.pdf"))


def _date_from_path(vtt_path: pathlib.Path) -> str:
    """Extract ISO date from a VTT filename like GMT20260319-*.vtt → '2026-03-19'."""
    m = re.search(r"GMT(\d{4})(\d{2})(\d{2})", vtt_path.name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return vtt_path.parent.name  # fall back to folder name


@mcp.tool()
def list_events() -> str:
    """List all available events under the Events folder with their transcript and PDF files.

    Returns a directory listing of ~/Dropbox/DDDI/Events so Claude can show the user
    what events are available and resolve paths for parse_transcript calls.
    """
    if not EVENTS_ROOT.exists():
        return f"Events folder not found: {EVENTS_ROOT}"

    lines = [f"Events root: {EVENTS_ROOT}\n"]
    for event_dir in sorted(EVENTS_ROOT.iterdir()):
        if not event_dir.is_dir() or event_dir.name.startswith("."):
            continue
        vtts = sorted(event_dir.rglob("*.transcript.vtt"))
        pdfs = sorted(event_dir.rglob("*.pdf"))
        lines.append(f"📁 {event_dir.name}/")
        for v in vtts:
            lines.append(f"   🎙  {v.relative_to(EVENTS_ROOT)}")
        for p in pdfs:
            lines.append(f"   📄  {p.relative_to(EVENTS_ROOT)}")
        if not vtts and not pdfs:
            lines.append("   (no transcripts or PDFs)")
    return "\n".join(lines)


@mcp.tool()
def parse_transcript(vtt_path: str, vtt_path2: str = "") -> str:
    """Parse one or two Zoom .vtt transcript files into clean, compressed text.

    Stop words, fillers, and connectors are removed from every line to reduce
    token count while preserving all content words, speaker labels, and line
    order. No lines are dropped or reordered — only function words are stripped.
    A stats note is prepended showing original vs. compressed word count.

    Any PDF files (slides, handouts) found in the same folder are automatically
    appended as supplementary material. PDF content is used as-is (not compressed).

    Accepts either:
    - A path to a specific .vtt file
    - A path to an event folder — the first *.transcript.vtt inside is used

    When two paths are provided the output is clearly separated by date so
    Claude can identify overlapping topics and distribute content evenly:
    Date1 content fully included; Date2 contributes only what is new
    (Date2 \\ Date1 in topic space).

    Args:
        vtt_path:  Path to the first .vtt file or event folder.
        vtt_path2: Optional path to a second .vtt file or event folder.
    """
    vtt1 = _resolve_vtt(vtt_path)
    date1 = _date_from_path(vtt1)
    text1 = _parse_vtt(str(vtt1))

    pdfs1 = _find_pdfs(vtt1.parent)
    if pdfs1:
        pdf_sections = []
        for pdf in pdfs1:
            pdf_text = _parse_pdf(str(pdf))
            pdf_sections.append(f"--- PDF: {pdf.name} ---\n{pdf_text}")
        text1 += "\n\n" + "=" * 40 + "\nSUPPLEMENTARY MATERIAL (PDFs in same folder)\n" + "=" * 40 + "\n"
        text1 += "\n\n".join(pdf_sections)

    if not vtt_path2:
        return text1

    vtt2 = _resolve_vtt(vtt_path2)
    date2 = _date_from_path(vtt2)
    text2 = _parse_vtt(str(vtt2))

    pdfs2 = _find_pdfs(vtt2.parent)
    if pdfs2:
        pdf_sections = []
        for pdf in pdfs2:
            pdf_text = _parse_pdf(str(pdf))
            pdf_sections.append(f"--- PDF: {pdf.name} ---\n{pdf_text}")
        text2 += "\n\n" + "=" * 40 + "\nSUPPLEMENTARY MATERIAL (PDFs in same folder)\n" + "=" * 40 + "\n"
        text2 += "\n\n".join(pdf_sections)

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
