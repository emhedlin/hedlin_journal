# Minimal UI Refinement Plan

Based on current_state.png review.

## Issues to Fix

### 1. Remove Title
- **Current**: "A Hedlin Family Journal" displayed at top
- **Fix**: Remove header entirely, content starts immediately at top

### 2. Remove Footer
- **Current**: "Hedlin Family Journal" at bottom
- **Fix**: Remove footer entirely

### 3. Remove Box/Border Around Years
- **Current**: Year buttons have borders (from `.nav-item` styling)
- **Fix**: Remove all borders, only show underline on hover (or no hover effect)

### 4. Show All Years (1983 → Current)
- **Current**: Only shows 1983 (the only year with entries)
- **Fix**: Show all years from 1983 to current year (2026)
  - Years WITH entries: black/dark text
  - Years WITHOUT entries: grey/muted text
  - All years are clickable (even grey ones - they just show no months)

---

## Implementation

### Step 1: Update Base Template
**File**: `templates/base.html`

Remove header and footer blocks:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Journal{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_path }}/static/css/styles.css">
    <style>
        :root {
            {{ config_css }}
        }
    </style>
    {% block extra_head %}{% endblock %}
</head>
<body>
    <div class="journal-container">
        {% block content %}{% endblock %}
    </div>

    {% block scripts %}{% endblock %}
</body>
</html>
```

### Step 2: Update Entry Page Template
**File**: `templates/entry.html`

Add back minimal nav for entry pages:

```html
{% extends "base.html" %}

{% block title %}{{ entry.date_display }}{% endblock %}

{% block content %}
<nav class="entry-page-nav">
    <a href="{{ url_path }}/index.html">← Back</a>
</nav>

<article class="entry">
    <header class="entry-header">
        <h1 class="entry-date">{{ entry.date_display }}</h1>

    {% if entry.prev or entry.next %}
    <div class="entry-nav">
        {% if entry.prev %}
        <a href="{{ url_path }}{{ entry.prev }}">← Previous</a>
        {% endif %}
        {% if entry.next %}
        <a href="{{ url_path }}{{ entry.next }}" style="margin-left: auto;">Next →</a>
        {% endif %}
    </div>
    {% endif %}
    </header>

    {% if entry.images %}
    <div class="entry-images">
        {% for image in entry.images %}
        <img src="{{ url_path }}{{ image }}" alt="" loading="lazy">
        {% endfor %}
    </div>
    {% endif %}

    <div class="entry-content">
        {{ entry.content_html | safe }}
    </div>
</article>
{% endblock %}
```

### Step 3: Update CSS
**File**: `static/css/styles.css`

Changes:
- Remove `.journal-header` and `.journal-footer` styles
- Remove `border-bottom` from `.nav-item` and `.entry-item`
- Remove padding/border from hover states
- Add styles for entry page nav
- Update layout to start at top of page

```css
/* Remove header/footer padding */
.journal-container {
    padding: 2rem 1rem 1rem;  /* reduced bottom padding */
}

/* Remove borders from nav items */
.nav-item,
.entry-item {
    border-bottom: none;  /* remove this line */
}

/* Add subtle hover indicator */
.nav-item:hover:not(.muted) {
    text-decoration: underline;
    text-decoration-color: var(--color-muted);
}

/* Entry page nav */
.entry-page-nav {
    margin-bottom: 2rem;
}

.entry-page-nav a {
    color: var(--color-muted);
    font-size: 0.9rem;
}

.entry-page-nav a:hover {
    color: var(--color-text);
}
```

### Step 4: Update Year Range Logic
**File**: `scripts/generate_html.py`

Change `build_year_hierarchy()` to show ALL years from 1983 to current:

```python
from datetime import datetime

def build_year_hierarchy(entries: List[Dict]) -> tuple:
    if not entries:
        return [], []

    # Find min year from entries (or default to 1983)
    min_year_from_entries = min(e['year'] for e in entries)
    start_year = min(1983, min_year_from_entries)

    # Current year
    current_year = datetime.now().year

    # Group entries by year-month
    year_month_entries = {}
    for entry in entries:
        year = entry['year']
        month = entry['month']
        key = (year, month)
        if key not in year_month_entries:
            year_month_entries[key] = []
        year_month_entries[key].append(entry)

    # Build years list (full range 1983 → current year)
    years = []
    for year in range(start_year, current_year + 1):
        year_entries = [e for e in entries if e['year'] == year]
        years.append({
            'year': year,
            'has_entries': len(year_entries) > 0
        })

    # Build months_by_year structure
    months_by_year = []
    for year in range(start_year, current_year + 1):
        year_data = {
            'year': year,
            'months': []
        }

        for month in range(1, 13):
            month_entries = year_month_entries.get((year, month), [])
            has_entries = len(month_entries) > 0
            month_name = MONTH_NAMES[month - 1]

            year_data['months'].append({
                'name': month_name,
                'number': month,
                'has_entries': has_entries,
                'entries': month_entries
            })

        months_by_year.append(year_data)

    return years, months_by_year
```

### Step 5: Update Index Template
**File**: `templates/index.html`

Remove `muted` class and `disabled` attributes - all years clickable:

```html
<div class="nav-level" data-level="years">
    {% for year in years %}
    <button class="nav-item{% if not year.has_entries %} muted{% endif %}"
            data-year="{{ year.year }}">
        {{ year.year }}
    </button>
    {% endfor %}
</div>
```

Note: Keep `muted` class for styling (grey color) but remove `disabled` attribute so all years are clickable.

---

## File Checklist

| File | Change |
|------|--------|
| `templates/base.html` | Remove header & footer blocks |
| `templates/entry.html` | Add entry page nav |
| `templates/index.html` | Remove disabled attribute |
| `static/css/styles.css` | Remove borders, simplify styles |
| `scripts/generate_html.py` | Update year range logic |

---

## Visual Result

```
┌─────────────────────────────┐
│                             │
│         1983                │  ← black, clickable
│         1984                │  ← grey, clickable
│         1985                │  ← grey, clickable
│         1986                │  ← grey, clickable
│         1987                │  ← grey, clickable
│         1988                │  ← grey, clickable
│         ...                  │
│         2025                │  ← grey, clickable
│         2026                │  ← grey, clickable
│                             │
└─────────────────────────────┘
```

No title, no footer, no borders - just the list of years.
