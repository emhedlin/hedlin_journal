# Minimal UI Implementation Plan

## Goal
Redesign the journal with a minimal, monochrome accordion-style navigation inspired by the home_schematic.png sketch.

## Design Requirements

### Theme
- Off-white background: `#f5f5f5`
- Near-black text: `#131313`
- Greyscale only (no colors)
- Clean, minimal aesthetic
- Colors configurable via `config.toml`

### Navigation Pattern (3-level accordion)
1. **Level 1 - Years**: List of years (grey = no entries, black = has entries)
2. **Level 2 - Months**: When year clicked, show months (grey = no entries, black = has entries)
3. **Level 3 - Entries**: When month clicked, show entries (day number + preview text)

### Transitions
- Click year → other years fade out, months fade in
- Click month → months fade out, entries fade in
- Back navigation to return to previous level

---

## Implementation Steps

### Step 1: Configuration System
**File**: `config.toml`

```toml
[theme]
background = "#f5f5f5"
text = "#131313"
muted = "#999999"
border = "#e0e0e0"

[preview]
length = 50  # words to show in entry preview
```

**Tasks**:
- Create `config.toml`
- Add Python config loader
- Pass config to Jinja2 templates

---

### Step 2: Minimal CSS Theme
**File**: `static/css/styles.css`

**Changes**:
- Remove all colors (accent colors, link colors, etc.)
- Use CSS custom properties for theme colors from config
- Simplify typography
- Remove decorative elements
- Minimal borders and spacing

**CSS Variables**:
```css
:root {
    --color-bg: #f5f5f5;
    --color-text: #131313;
    --color-muted: #999999;
    --color-border: #e0e0e0;
}
```

---

### Step 3: Remove Timeline
**Files to update**:
- Remove `templates/timeline.html`
- Remove timeline link from `templates/base.html`
- Remove `static/js/timeline.js`
- Remove embeddings generation from build (optional)

---

### Step 4: New Home Page Template
**File**: `templates/index.html` (rewrite)

**Structure**:
```html
<div class="accordion-nav">
    <!-- Years level -->
    <div class="nav-level" data-level="years">
        {% for year in years %}
        <button class="nav-item {{ 'active' if year.has_entries else 'muted' }}"
                data-year="{{ year.year }}"
                {{ 'disabled' if not year.has_entries }}>
            {{ year.year }}
        </button>
        {% endfor %}
    </div>

    <!-- Months level (hidden by default) -->
    <div class="nav-level" data-level="months" hidden>
        <button class="nav-back">← {{ current_year }}</button>
        {% for month in months %}
        <button class="nav-item {{ 'active' if month.has_entries else 'muted' }}"
                data-month="{{ month.number }}">
            {{ month.name }}
        </button>
        {% endfor %}
    </div>

    <!-- Entries level (hidden by default) -->
    <div class="nav-level" data-level="entries" hidden>
        <button class="nav-back">← {{ current_month }} {{ current_year }}</button>
        {% for entry in entries %}
        <a href="{{ entry.url }}" class="entry-item">
            <span class="entry-day">{{ entry.day }}</span>
            <span class="entry-preview">{{ entry.preview }}</span>
        </a>
        {% endfor %}
    </div>
</div>
```

---

### Step 5: JavaScript Interactions
**File**: `static/js/accordion.js`

**Features**:
- Handle year clicks → show months
- Handle month clicks → show entries
- Handle back button → return to previous level
- Smooth fade transitions between levels
- Keyboard navigation support

**Pseudo-code**:
```javascript
const levels = { years, months, entries };

function showLevel(levelName, data) {
    // Hide all levels
    // Populate target level with data
    // Fade in target level
}

function handleYearClick(year) {
    fetch(`/api/months/${year}`)
        .then(data => showLevel('months', data));
}

function handleMonthClick(year, month) {
    fetch(`/api/entries/${year}/${month}`)
        .then(data => showLevel('entries', data));
}
```

---

### Step 6: Data Structure Updates
**File**: `scripts/generate_html.py`

**Changes**:
- Pre-compute year/month/entry hierarchy
- Generate JSON data for each level
- Create API endpoints (or inline JSON in HTML)

**Data Structure**:
```json
{
    "years": [
        {"year": 1983, "has_entries": true, "count": 101},
        {"year": 1984, "has_entries": false, "count": 0}
    ],
    "months": {
        "1983": [
            {"name": "July", "number": 7, "has_entries": true, "count": 9},
            {"name": "August", "number": 8, "has_entries": true, "count": 31}
        ]
    },
    "entries": {
        "1983-07": [
            {"day": 23, "url": "/entries/1983/07/...", "preview": "In order to make..."},
            ...
        ]
    }
}
```

---

## Visual Mockup (text version)

```
┌─────────────────────────────┐
│                             │
│        A HEDLIN FAMILY       │
│          JOURNAL             │
│                             │
├─────────────────────────────┤
│                             │
│         1978                │  ← black, clickable
│         1979                │  ← black, clickable
│         1980                │  ← black, clickable
│         1981                │  ← grey, not clickable
│         1982                │  ← black, clickable
│         1983                │  ← black, clickable
│         1984                │  ← grey, not clickable
│         1985                │  ← grey, not clickable
│         ...                  │
│                             │
└─────────────────────────────┘

[Click 1983]

┌─────────────────────────────┐
│                             │
│  ← 1983                     │  ← back button
│                             │
│         January             │  ← grey
│         February            │  ← grey
│         March               │  ← grey
│         April               │  ← grey
│         May                 │  ← grey
│         June                │  ← grey
│         July                │  ← black
│         August              │  ← black
│         September           │  ← grey
│         ...                  │
│                             │
└─────────────────────────────┘

[Click July]

┌─────────────────────────────┐
│                             │
│  ← July 1983                │  ← back button
│                             │
│  23  In order to make...     │
│  24  Matthew slept from...    │
│  25  Sunny and warm. The...   │
│  26  We took the Toyota...    │
│  27  Cheryl will pick...      │
│  ...                         │
│                             │
└─────────────────────────────┘
```

---

## Implementation Order

1. **Config system** - Create config.toml and loader
2. **CSS update** - Apply minimal theme
3. **Remove timeline** - Clean up unused files
4. **New index template** - Build accordion HTML structure
5. **JavaScript** - Add interaction handlers
6. **Data generation** - Update build script to create hierarchy
7. **Testing** - Test navigation flow

---

## Files to Modify

| File | Action |
|------|--------|
| `config.toml` | CREATE |
| `scripts/load_config.py` | CREATE |
| `static/css/styles.css` | MODIFY |
| `templates/base.html` | MODIFY (remove timeline link) |
| `templates/index.html` | REWRITE |
| `static/js/accordion.js` | CREATE |
| `scripts/generate_html.py` | MODIFY (add hierarchy data) |
| `templates/timeline.html` | DELETE |
| `static/js/timeline.js` | DELETE (or keep for later) |
