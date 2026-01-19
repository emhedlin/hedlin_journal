# Vertical Connecting Line Implementation Plan

## Overview

Add a vertical line connecting the bullets (○/●) at the currently expanded level:
- Years collapsed → vertical line connects years
- Year expanded → vertical line connects months within that year
- Month expanded → vertical line connects entries within that month

## Visual Mockup

```
Before:                          After:
○ 1983                           │○ 1983
  ○ July                         │  ○ July
  ● August                       │  ● August
    ○ 8    We went...            │    │○ 8    We went...
    ○ 9    The weather...        │    │○ 9    The weather...
○ 1984                           │○ 1984
```

The vertical line (│) appears to the left of the bullets, connecting items at the same level.

---

## Implementation Approach: CSS + JavaScript

### Why Both?

- **Pure CSS `:has()` selector** would be ideal but has limited browser support (Chrome 105+, Safari 15.4+, Firefox 121+)
- **JavaScript class toggle** + CSS gives broader compatibility and more control

### Strategy

1. **JavaScript**: When expanding/collapsing a node, toggle a class `expanded` on the parent
2. **CSS**: Use `.expanded > .tree-children::before` to draw the vertical line

---

## Stage 1: Update `tree.js`

### Understanding the Current Code

The current `toggleNode` receives a `node` (the `.tree-node` div), but the toggle symbol selector is wrong:
```javascript
// WRONG - this won't match anything
const toggle = node.querySelector('.tree-toggle > .tree-toggle');
```

The actual markup is:
```html
<div class="tree-label">
    <span class="tree-toggle">○</span>
    <span class="tree-text">1983</span>
</div>
```

So the correct selector is: `node.querySelector('.tree-toggle')`

### Corrected Implementation

**1. Update `toggleNode` to add `expanded` class and manage single visible line:**

```javascript
toggleNode(node) {
    const children = node.querySelector('.tree-children');
    const toggle = node.querySelector('.tree-toggle');  // FIXED: removed nested selector

    if (!children) {
        return; // Leaf node, nothing to toggle
    }

    const isExpanded = !children.hidden;

    if (isExpanded) {
        // Collapse
        children.hidden = true;
        if (toggle) toggle.textContent = '○';
        node.classList.remove('expanded');
        node.classList.remove('show-line');  // REMOVE LINE
    } else {
        // Expand
        children.hidden = false;
        if (toggle) toggle.textContent = '●';
        node.classList.add('expanded');
        node.classList.add('show-line');     // SHOW LINE for this node

        // Remove line from siblings (only one expanded level shows line)
        const parent = node.parentElement;
        if (parent) {
            parent.querySelectorAll('.show-line').forEach(n => {
                if (n !== node) n.classList.remove('show-line');
            });
        }

        this.updateHash(node);
    }
}
```

**2. Update `expandToYear` to add `expanded` and `show-line`:**

```javascript
expandToYear(year) {
    const yearNode = this.tree.querySelector(`.year-node[data-year="${year}"]`);
    if (yearNode) {
        const toggle = yearNode.querySelector('.tree-toggle');
        const children = yearNode.querySelector('.tree-children');
        if (children) {
            children.hidden = false;
            if (toggle) toggle.textContent = '●';
            yearNode.classList.add('expanded');
            yearNode.classList.add('show-line');  // ADD THIS

            // Remove line from other years
            this.tree.querySelectorAll('.year-node.show-line').forEach(n => {
                if (n !== yearNode) n.classList.remove('show-line');
            });
        }
    }
}
```

**3. Update `expandToMonth` similarly:**

```javascript
expandToMonth(year, month) {
    this.expandToYear(year);
    const monthNode = this.tree.querySelector(
        `.year-node[data-year="${year}"] .month-node[data-month="${month}"]`
    );
    if (monthNode) {
        const toggle = monthNode.querySelector('.tree-toggle');
        const children = monthNode.querySelector('.tree-children');
        if (children) {
            children.hidden = false;
            if (toggle) toggle.textContent = '●';
            monthNode.classList.add('expanded');
            monthNode.classList.add('show-line');  // ADD THIS

            // Remove line from other months in this year
            const yearNode = monthNode.closest('.year-node');
            yearNode.querySelectorAll('.month-node.show-line').forEach(n => {
                if (n !== monthNode) n.classList.remove('show-line');
            });
        }
    }
}
```

### Key Design Decisions

1. **Two classes**: `expanded` tracks state, `show-line` controls visual line
2. **Single line per level**: When expanding a node, remove `show-line` from siblings
3. **No line for entries**: Month nodes with expanded children don't get `show-line` (or CSS can hide it)

---

## Stage 2: Add CSS for Vertical Line

### Using CSS Variables for Proper Alignment

First, define the toggle width as a variable so the line can align to it:

**Add to `static/css/styles.css` (in the root variables section):**

```css
:root {
    /* ... existing variables ... */
    --toggle-width: 1.5rem;  /* Match .tree-toggle width */
}
```

**Then add the vertical line CSS:**

```css
/* Vertical connecting line - only for nodes with show-line class */
.tree-node.show-line > .tree-children {
    position: relative;
}

.tree-node.show-line > .tree-children::before {
    content: '';
    position: absolute;
    /* Center the line with the toggle: (toggle-width / 2) - (line-width / 2) */
    left: calc(var(--toggle-width) / 2 - 0.5px);
    top: 0.75rem;  /* Start below parent label's padding */
    bottom: 0.75rem;  /* End before last child's padding */
    width: 1px;
    background-color: var(--color-border);
    opacity: 0.4;
}

/* Don't show line for month entries (entries don't have bullets) */
.tree-node.month-node.show-line > .tree-children::before {
    display: none;
}
```

### Why This Works

1. **`calc(var(--toggle-width) / 2 - 0.5px)`**: Centers the 1px line within the 1.5rem toggle width
2. **`show-line` class only**: Line only appears when we explicitly add the class (via JS)
3. **`month-node` exception**: Entries don't have bullets, so no line needed at that level
4. **`top: 0.75rem` / `bottom: 0.75rem`**: Accounts for padding on labels so line connects bullets, not full height

### Visual Result

```
│○ 1983           <-- line connects year bullets
│  ○ January
│  ○ February
│● 1984           <-- expanded
│  │○ January     <-- line now connects month bullets
│  │○ February    <-- year line is replaced with month line
│  ● March
```

---

## Stage 3: Fine-tuning

### Adjustments for visual polish:

1. **Line start/end**: Start line below parent bullet, end before last item
2. **Line color**: Use `var(--color-border)` for subtlety
3. **Line opacity**: `0.5` to keep it subtle
4. **Responsive**: Adjust on mobile if needed

### Advanced: Pure CSS Alternative (future)

If browser compatibility isn't a concern, can use `:has()`:

```css
/* No JavaScript class needed - line appears when children are visible */
.tree-node:has(.tree-children:not([hidden])) > .tree-children::before {
    content: '';
    position: absolute;
    left: 0.45rem;
    top: 0;
    bottom: 0;
    width: 1px;
    background-color: var(--color-border);
    opacity: 0.5;
}
```

---

## Stage 4: Rebuild and Test

```bash
# Regenerate HTML
source .venv/bin/activate
python scripts/generate_html.py -c content -o output -t templates -s static

# Preview
python -m http.server 8000 --directory output
```

**Test Cases:**
- [ ] Line appears when year is expanded, connects months
- [ ] Line appears when month is expanded, connects entries (if enabled)
- [ ] Line disappears when collapsed
- [ ] Multiple expanded years each have their own line
- [ ] Line aligns visually with bullets
- [ ] Line looks good on mobile

---

## Files to Modify

| File | Changes |
|------|---------|
| `static/js/tree.js` | Add `node.classList.add/remove('expanded')` in toggle functions |
| `static/css/styles.css` | Add vertical line CSS using `.expanded` class |

---

## Optional Enhancements

1. **Animated line**: Could animate the line growing when expanding
2. **Color on hover**: Line could darken when hovering the expanded section
3. **Skip entry-level**: Don't show line for entries (too granular)
4. **Gradient fade**: Line fades at top and bottom for softer look

---

## Rollback

If it doesn't look good:
1. Remove the `.expanded` class logic from `tree.js`
2. Remove the vertical line CSS from `styles.css`
3. Rebuild

No template changes required = easy rollback.
