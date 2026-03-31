# Blog Post Generator — Context for Claude Code

This project converts Zoom meeting transcripts (.vtt files) into blog post drafts.

## Meeting context

- **Group:** Postdoctoral researchers (DataPoints / DDDI AI Fellow Gathering)
- **Format:** Informal discussion workshops, ~90 minutes, multiple speakers
- **Recurring topics:**
  - AI/agentic coding for scientific research
  - Model comparisons (Claude, Gemini, GPT) in research workflows
  - Practical failures and lessons learned using LLMs
  - AI ethics in research contexts
  - Interdisciplinary applications (astrophysics, health communication, etc.)
  - Doing research with Claude Code & other models
  - What’s new in AI?
  - Preparing for careers in academia and tech
  - Pair “journal club”
  - How best to teach AI
  - Best practices in using AI
- **Audience:** Researchers and academics interested in AI in science — accessible but substantive, no hype

## Blog post guidelines

- **Length:** 750–1250 words (target reading time: 3–9 minutes at ~200 wpm)
- **Structure:**
  1. `# Title` (H1) — punchy, specific, not generic
  2. Intro paragraph (2–3 sentences, hook the reader — what was this meeting about and why does it matter?)
  3. `## Key Takeaways` — a bullet list of 4–7 concrete takeaways from the meeting. Takeaways must be things readers can **immediately try, apply, or find insightful** — not vague summaries. Write each as a single crisp sentence.
  4. Chronological narrative sections with `## Section Header` (H2) — follow the arc of the discussion in the order it happened. Each section covers a distinct topic or moment in the meeting. Use `### Sub-section` (H3) within a section only when a topic naturally branches into distinct sub-threads — don't force H3s into every post.
  5. Closing 2–3 paragraph summary — reflect on the session as a whole, what it signals for the field, and what the group might explore next. No blockquote, no "Key takeaway:" label.
- **Tone:** Conversational but intellectually serious — write for a smart colleague, not a press release
- **Do NOT invent or embellish** content not present in the transcript
- Strip filler words, crosstalk, and repetition — surface the actual ideas
- **Do NOT quote or attribute any statement to a named speaker.** The meeting is recorded in a shared room with one microphone under one Zoom host account — speaker identity cannot be reliably determined from the transcript. Write all ideas and observations in third person ("the group discussed…", "one perspective raised was…", "a recurring concern was…")

## Standard workflow

When asked to generate a blog post:

1. Use `parse_transcript` tool with the provided .vtt file path
2. Read the clean transcript carefully for main themes, the chronological flow of discussion, and concrete takeaways
3. Write the blog post draft in markdown following the guidelines above
4. Use `save_draft` tool to save it — always pass `meeting_date` (ISO format, e.g. `"2026-03-19"`) extracted from the VTT filename, so re-running always overwrites the same file instead of creating a new one. Use a descriptive `filename` if the user specifies one.
5. Tell the user exactly where the draft was saved and suggest 1–2 edits they might want to make

## Publishing workflow

When asked to publish a draft to the blog:

1. Use `publish_to_blog` tool with:
   - `draft_filename`: the file in `drafts/` (e.g. `"2026-03-19-draft.md"`)
   - `post_slug`: short URL-friendly slug from the title (e.g. `"agentic-coding-postdocs"`)
   - `post_title`: the H1 title from the draft
   - `post_subtitle`: subtitle if present in the draft
   - `summary`: 1–2 sentence summary for the homepage card
   - `meeting_date`: ISO date extracted from the VTT filename (e.g. `"2026-03-19"`)
   - Leave `author_name`, `author_pic`, `author_title` as defaults for group/AI-fellow posts
2. The tool creates branch `post/YYYY-MM-DD-slug` in `~/DDDI_DP_Blog`, writes the post with Jekyll frontmatter, pushes, and opens a draft PR at `github.com/dddiscovery/datapoints`
3. Tell the user the PR URL and remind them to:
   - Edit the post in Cursor on the new branch
   - Add a cover image to `assets/images/posts/`
   - Update `index.md` homepage `featured_posts` if this post should be featured
   - Mark the PR as ready and merge to `main` when done

## Transcript file locations

Transcripts are stored in:

```
~/Dropbox/DDDI/AI-fellow-gathering/<Date>/GMT*.transcript.vtt
```

Example:

```
~/Dropbox/DDDI/AI-fellow-gathering/Mar19, 2026/GMT20260319-200425_Recording.transcript.vtt
```

