# Mobile Vertical Line Fix Plan (Revised)

## Problem Analysis

### Current Issue

The existing approach draws per-node line segments, which rely on tight vertical spacing to visually connect. On mobile, line-height and spacing differences create visible gaps.

### Revised Fix Strategy

Use a single continuous line per active level (years, months, entries) and position it based on actual bullet centers computed in JavaScript. This avoids gaps and keeps alignment consistent across device sizes.

---

## Revised Implementation (JS + CSS)

### Overview

1. Add three dedicated line elements: one for years, months, and entries.
2. Toggle a `data-active-level` attribute on the tree root based on the deepest expanded level.
3. Compute line positions from actual bullet centers and apply inline `top`/`bottom` values.
4. Show only the line for the active level.

This ensures:
- One continuous line at the currently active level.
- Precise alignment on mobile.
- No dependency on `:has()` or guessed offsets.

---

## Implementation Steps

### Stage 1: Update Template

Add dedicated line elements to `templates/index.html`:

```html
<div class="tree-nav" id="tree">
    <div class="tree-vertical-line line-years" aria-hidden="true"></div>
    <div class="tree-vertical-line line-months" aria-hidden="true"></div>
    <div class="tree-vertical-line line-entries" aria-hidden="true"></div>
    {% for year in years %}
    ...
```

### Stage 2: Update CSS

Replace per-node line CSS with level-based line elements:

```css
.tree-nav {
    position: relative;
}

.tree-vertical-line {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--color-border);
    opacity: 0.4;
    pointer-events: none;
    display: none;
}

/* Show only the active level line */
.tree-nav[data-active-level="years"] .line-years,
.tree-nav[data-active-level="months"] .line-months,
.tree-nav[data-active-level="entries"] .line-entries {
    display: block;
}
```

### Stage 3: Update `tree.js`

Add logic to:
1. Set `data-active-level` on `.tree-nav`
2. Compute and set line positions based on the bullet centers of visible nodes at that level

**Pseudo-code outline:**

```javascript
updateActiveLevel() {
    const tree = this.tree;
    const expandedMonths = tree.querySelectorAll('.month-node .tree-children:not([hidden])');
    const expandedYears = tree.querySelectorAll('.year-node .tree-children:not([hidden])');

    if (expandedMonths.length) {
        tree.dataset.activeLevel = 'entries';
        this.positionLine('.line-entries', '.month-node .tree-children:not([hidden]) .tree-entry');
    } else if (expandedYears.length) {
        tree.dataset.activeLevel = 'months';
        this.positionLine('.line-months', '.year-node .tree-children:not([hidden]) .month-node');
    } else {
        tree.dataset.activeLevel = 'years';
        this.positionLine('.line-years', '.year-node');
    }
}

positionLine(lineSelector, itemSelector) {
    const line = this.tree.querySelector(lineSelector);
    const items = Array.from(this.tree.querySelectorAll(itemSelector));
    if (!line || items.length === 0) {
        return;
    }

    const first = items[0].querySelector('.tree-toggle');
    const last = items[items.length - 1].querySelector('.tree-toggle');
    if (!first || !last) {
        return;
    }

    const treeRect = this.tree.getBoundingClientRect();
    const firstRect = first.getBoundingClientRect();
    const lastRect = last.getBoundingClientRect();

    const left = firstRect.left - treeRect.left + (firstRect.width / 2);
    const top = firstRect.top - treeRect.top + (firstRect.height / 2);
    const bottom = treeRect.bottom - (lastRect.top + (lastRect.height / 2));

    line.style.left = `${left}px`;
    line.style.top = `${top}px`;
    line.style.bottom = `${bottom}px`;
}
```

Call `updateActiveLevel()`:
- After toggling nodes in `toggleNode`
- After hash-based expansion
- On window resize (debounced)

---

## Testing Checklist

- [ ] Line appears and connects year bullets on desktop
- [ ] Line appears and connects year bullets on mobile
- [ ] Line switches to months when a year is expanded
- [ ] Line switches to entries when a month is expanded
- [ ] No gaps in the line on any screen size
- [ ] Line doesn't interfere with touch events (pointer-events: none)

---

## Files to Modify

| File | Change |
|------|--------|
| `templates/index.html` | Add three line elements inside `.tree-nav` |
| `static/css/styles.css` | Replace per-node line CSS with level-based line CSS |
| `static/js/tree.js` | Add active-level detection + line positioning updates |

---

## Rollback

If issues persist:
1. Revert template to remove `.tree-vertical-line` div
2. Revert CSS to original approach (or remove vertical line feature entirely)
3. Rebuild
