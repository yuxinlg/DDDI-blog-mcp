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
- **Audience:** Researchers and academics interested in AI in science — accessible but substantive, no hype

## Blog post guidelines

- **Length:** 600–900 words
- **Structure:**
  - `# Title` (H1) — punchy, specific, not generic
  - Intro paragraph (2–3 sentences, hook the reader)
  - 2–3 themed sections with `## Section Header` (H2)
  - Closing paragraph with a concrete takeaway
- **Tone:** Conversational but intellectually serious — write for a smart colleague, not a press release
- **Do NOT invent or embellish** content not present in the transcript
- Strip filler words, crosstalk, and repetition — surface the actual ideas
- Attribute interesting quotes or ideas to speakers by first name when clear from context
- End with a `> **Key takeaway:** ...` blockquote (2–3 sentences)

## Standard workflow

When asked to generate a blog post:
1. Use `parse_transcript` tool with the provided .vtt file path
2. Read the clean transcript carefully for main themes and quotable moments
3. Write the blog post draft in markdown following the guidelines above
4. Use `save_draft` tool to save it (suggest a descriptive filename based on the content)
5. Tell the user exactly where the draft was saved and suggest 1–2 edits they might want to make

## Transcript file locations

Transcripts are stored in:
```
~/Dropbox/DDDI/AI-fellow-gathering/<Date>/GMT*.transcript.vtt
```

Example:
```
~/Dropbox/DDDI/AI-fellow-gathering/Mar19, 2026/GMT20260319-200425_Recording.transcript.vtt
```
