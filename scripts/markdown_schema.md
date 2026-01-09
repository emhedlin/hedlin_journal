# Markdown Frontmatter Schema

Journal entries are stored as Markdown files with YAML frontmatter.

## File Naming Convention

```
content/YYYY/MM/YYYY-MM-DD-slug.md
```

Example: `content/1983/07/1983-07-23-journal-entry.md`

## Frontmatter Schema

```yaml
---
title: "Optional entry title"
date: "1983-07-23"
date_display: "Saturday, July 23, 1983"
tags: []
people: []
images: []
source_file: "example.docx"
---
```

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | No | Optional title for the entry |
| date | string (ISO) | Yes | Entry date in YYYY-MM-DD format |
| date_display | string | Yes | Original date text from source |
| tags | list of strings | No | Categorization tags (e.g., family, travel) |
| people | list of strings | No | People mentioned in the entry |
| images | list of strings | No | Paths to images (relative to content/) |
| source_file | string | Yes | Original DOCX filename |

## Content Body

The body content is written in Markdown format. Paragraphs from the source are separated by blank lines.

## Example Entry

```markdown
---
date: "1983-07-23"
date_display: "Saturday, July 23, 1983"
tags: []
people: []
source_file: "example.docx"
---

In order to make future recordings more meaningful, today's entry will lay out some of the more important events since our marriage on August 16, 1975.

Peter David Skarsgard was born June 21 1978 at City Hospital, Matthew Paul Skarsgard on September 23 1982 at St. Paul's, (*and Erik Mitchell Skarsgard on August 27 1986). These are our big-bang events. They unleashed everything else that comprise our life.
```
