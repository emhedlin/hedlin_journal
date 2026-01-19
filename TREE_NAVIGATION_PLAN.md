# Tree Navigation Implementation Plan

## Overview

Convert the current multi-page accordion navigation (Years → Months → Entries) to a single-page expandable tree view where:
- Clicking a year expands to show months inline
- Clicking a month expands to show entries inline
- Clicking an entry navigates to the entry page (unchanged)

## Current State

### Existing Files

| File | Purpose |
|------|---------|
| `templates/index.html` | Uses accordion.js, shows one level at a time |
| `static/js/accordion.js` | Current navigation - hides previous level when drilling down |
| `static/js/tree.js` | **Already implements expand/collapse tree** - not currently used |
| `static/css/styles.css` | Has accordion styles, needs tree additions |

### Data Structure (already in template)

The current template embeds this data (no changes needed):

```javascript
const journalData = {
    years: [
        { year: 1983, hasEntries: true },
        { year: 1984, hasEntries: true },
        // ...
    ],
    months: {
        1983: [
            { name: "July", number: 7, hasEntries: true },
            { name: "August", number: 8, hasEntries: true },
            // ...
        ],
        // ...
    },
    entries: {
        "1983-7": [
            { day: 23, url: "/entries/1983/07/23/", preview: "In order to make..." },
            // ...
        ],
        // ...
    }
};
```

---

## Implementation Stages

### Stage 1: Update `templates/index.html` Template

**Goal**: Replace accordion HTML structure with nested tree structure

**Changes:**
1. Replace `accordion-nav` container with `tree-nav` container
2. Render nested HTML structure directly with year/month/entry nodes
3. Include `tree.js` instead of `accordion.js`
4. Keep `journalData` as-is (no changes needed)

**New HTML Structure:**

```html
{% extends "base.html" %}

{% block title %}Journal{% endblock %}

{% block content %}
<div class="tree-nav" id="tree">
    {% for year in years %}
    <div class="tree-node year-node" data-year="{{ year.year }}" data-has-entries="{{ 'true' if year.has_entries else 'false' }}">
        <div class="tree-label tree-toggle">
            <span class="tree-toggle">○</span>
            <span class="tree-text">{{ year.year }}</span>
        </div>
        <div class="tree-children" hidden>
            {% set year_data = months_by_year|selectattr('year', 'equalto', year.year)|first %}
            {% if year_data %}
                {% for month in year_data.months %}
                <div class="tree-node month-node" data-month="{{ month.number }}" data-has-entries="{{ 'true' if month.has_entries else 'false' }}">
                    <div class="tree-label">
                        <span class="tree-toggle">○</span>
                        <span class="tree-text">{{ month.name }}</span>
                    </div>
                    <div class="tree-children" hidden>
                        {% if month.has_entries %}
                        {% for entry in month.entries %}
                        <a class="tree-entry" href="{{ url_path }}{{ entry.url }}">
                            <span class="entry-day">{{ entry.day }}</span>
                            <span class="entry-preview">{{ entry.preview }}</span>
                        </a>
                        {% endfor %}
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            {% endif %}
        </div>
    </div>
    {% endfor %}
</div>

<script src="{{ url_path }}/static/js/tree.js"></script>
{% endblock %}
```

---

### Stage 2: Add Tree Navigation CSS

**Goal**: Style the expandable tree with proper indentation and visual feedback

**Add to `static/css/styles.css`:**

```css
/* Tree Navigation */
.tree-nav {
    display: flex;
    flex-direction: column;
}

.tree-node {
    display: flex;
    flex-direction: column;
}

.tree-label {
    display: flex;
    align-items: center;
    padding: 0.75rem 0;
    cursor: pointer;
    user-select: none;
}

.tree-toggle {
    width: 1.5rem;
    text-align: center;
    color: var(--color-muted);
    font-size: 0.8rem;
    transition: color 0.2s;
}

.tree-label:hover .tree-toggle {
    color: var(--color-text);
}

.tree-text {
    font-size: 1rem;
}

.tree-children {
    display: flex;
    flex-direction: column;
    padding-left: 1.5rem;  /* Indentation for nested levels */
}

.tree-children[hidden] {
    display: none;
}

/* Entry items within tree */
.tree-entry {
    display: flex;
    gap: 1rem;
    padding: 0.5rem 0 0.5rem 1.5rem; /* Indent past toggle */
    text-decoration: none;
    color: var(--color-text);
    transition: opacity 0.2s;
}

.tree-entry:hover {
    opacity: 0.7;
}

.tree-entry .entry-day {
    font-variant-numeric: tabular-nums;
    min-width: 2rem;
}

.tree-entry .entry-preview {
    color: var(--color-muted);
    font-size: 0.9rem;
}

/* Muted (no entries) */
.tree-node[data-has-entries="false"] .tree-text {
    color: var(--color-muted);
}
```

---

### Stage 3: Update `tree.js` (Minor Tweaks)

**Goal**: Ensure tree.js works with the new HTML structure

**Current `tree.js` is mostly compatible, but needs:**

1. Make toggle lookups use the closest `.tree-node` so `.tree-children` is found
2. Treat `.tree-entry` as leaf navigation (no expand/collapse)
3. Keep hash behavior to `#year` and `#year-month` only

**Update `tree.js`:**

```javascript
// Use closest tree-node when toggling from inner elements
const node = toggle.closest('.tree-node');
const children = node?.querySelector('.tree-children');

// Entry clicks should navigate, not toggle
const entries = this.tree.querySelectorAll('.tree-entry');
entries.forEach(entry => {
    entry.addEventListener('click', () => {
        // Let default link behavior happen
    });
});

// Hash parsing: support #year and #year-month only
const matchMonth = hash.match(/^#(\d+)-(\d+)$/);
const matchYear = hash.match(/^#(\d+)$/);
```

---

### Stage 4: Rebuild and Test

**Commands:**

```bash
# Regenerate HTML
source .venv/bin/activate
python scripts/generate_html.py -c content -o output -t templates -s static

# Preview
python -m http.server 8000 --directory output
```

**Test Checklist:**

- [ ] Click year → months expand inline (year doesn't disappear)
- [ ] Click another year → both can be expanded simultaneously
- [ ] Click month → entries expand inline (month doesn't disappear)
- [ ] Click entry → navigates to entry page
- [ ] URL hash works (e.g., `#1984-7` opens July 1984)
- [ ] Browser back/forward works with hash changes
- [ ] Keyboard navigation (Tab, Enter, Escape)
- [ ] Mobile touch works
- [ ] Empty years/months show muted
- [ ] Toggle symbols change: ○ (collapsed) → ● (expanded)

---

## Visual Mockup

```
Hedlin Family Journal

○ 1983                   ○ = collapsed
○ 1984                   ● = expanded
  ○ January
  ● July                  ▼ Click to expand/collapse
    ○ 8    We went to the beach...
    ○ 9    The weather was perfect...
    ○ 23    In order to make...
○ 1985
  ○ January
  ○ February
```

---

## Files Summary

| File | Action | Changes |
|------|--------|---------|
| `templates/index.html` | Modify | Replace accordion with tree structure |
| `static/css/styles.css` | Modify | Add tree navigation styles |
| `static/js/tree.js` | Review | Minor tweaks if needed |
| `static/js/accordion.js` | Delete | No longer needed (after testing) |

---

## Rollback Plan

If issues arise:
1. Keep `accordion.js` until tree is fully tested
2. Git commit before changes: `git commit -am "Pre-tree navigation backup"`
3. To revert: `git checkout HEAD~1 -- templates/index.html static/css/styles.css`

---

## Success Criteria

- [ ] All navigation works via tree expansion on single page
- [ ] Entry pages still load correctly
- [ ] URL hash navigation works for deep linking
- [ ] Visual design matches current aesthetic (minimal grayscale)
- [ ] No JavaScript errors in console
- [ ] Works on mobile devices
