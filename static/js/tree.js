/**
 * Hedlin Family Journal - Tree Navigation
 *
 * Nested expandable tree: Years → Months → Entries
 * With JavaScript-positioned vertical connecting lines
 */

class JournalTree {
    constructor() {
        this.tree = document.getElementById('tree');
        this.resizeTimeout = null;
        this.init();
    }

    init() {
        // Attach click handlers to all tree labels (which contain the toggle)
        const labels = this.tree.querySelectorAll('.tree-label');
        labels.forEach(label => {
            label.addEventListener('click', (e) => {
                const node = label.parentElement;
                this.toggleNode(node);
            });
        });

        // Entry clicks should navigate, not toggle
        const entries = this.tree.querySelectorAll('.tree-entry');
        entries.forEach(entry => {
            entry.addEventListener('click', (e) => {
                // Let default link behavior happen
            });
        });

        // Handle URL hash on load to restore expanded state
        this.handleHashOnLoad();

        // Handle hash changes (browser back/forward)
        window.addEventListener('hashchange', () => {
            this.handleHashOnLoad();
        });

        // Update line positions on resize (debounced)
        window.addEventListener('resize', () => {
            if (this.resizeTimeout) {
                clearTimeout(this.resizeTimeout);
            }
            this.resizeTimeout = setTimeout(() => {
                this.updateActiveLevel();
            }, 100);
        });

        // Initial line positioning
        this.updateActiveLevel();
    }

    toggleNode(node) {
        const children = node.querySelector('.tree-children');
        const toggle = node.querySelector('.tree-toggle');

        if (!children) {
            return; // Leaf node, nothing to toggle
        }

        const isExpanded = !children.hidden;

        if (isExpanded) {
            // Collapse
            children.hidden = true;
            if (toggle) toggle.textContent = '○';
            node.classList.remove('expanded');
            node.classList.remove('show-line');
        } else {
            // Expand
            children.hidden = false;
            if (toggle) toggle.textContent = '●';
            node.classList.add('expanded');

            // Remove line from siblings (only one expanded level shows line)
            const parent = node.parentElement;
            if (parent) {
                parent.querySelectorAll('.show-line').forEach(n => {
                    if (n !== node) n.classList.remove('show-line');
                });
            }

            // Update URL hash to reflect the newly expanded node
            this.updateHash(node);
        }

        // Update active level and line positions
        this.updateActiveLevel();
    }

    updateHash(node) {
        let hash = '';

        if (node.classList.contains('month-node')) {
            const yearNode = node.closest('.year-node');
            const year = yearNode?.dataset.year;
            const month = node.dataset.month;
            if (year) {
                hash = `#${year}-${month}`;
            }
        } else if (node.classList.contains('year-node')) {
            const year = node.dataset.year;
            hash = `#${year}`;
        }

        if (hash && hash !== window.location.hash) {
            history.pushState(null, null, hash);
        }
    }

    handleHashOnLoad() {
        const hash = window.location.hash;
        if (!hash) {
            this.updateActiveLevel();
            return;
        }

        // Parse hash formats:
        // #year-month (month)
        // #year (year)
        const matchMonth = hash.match(/^#(\d+)-(\d+)$/);
        const matchYear = hash.match(/^#(\d+)$/);

        if (matchMonth) {
            const year = parseInt(matchMonth[1]);
            const month = parseInt(matchMonth[2]);
            this.expandToMonth(year, month);
        } else if (matchYear) {
            const year = parseInt(matchYear[1]);
            this.expandToYear(year);
        } else {
            this.updateActiveLevel();
        }
    }

    expandToYear(year) {
        const yearNode = this.tree.querySelector(`.year-node[data-year="${year}"]`);
        if (yearNode) {
            const toggle = yearNode.querySelector('.tree-toggle');
            const children = yearNode.querySelector('.tree-children');
            if (children) {
                children.hidden = false;
                if (toggle) toggle.textContent = '●';
                yearNode.classList.add('expanded');

                // Remove line from other years
                this.tree.querySelectorAll('.year-node.show-line').forEach(n => {
                    if (n !== yearNode) n.classList.remove('show-line');
                });

                // Update active level and line positions
                this.updateActiveLevel();
            }
        }
    }

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

                // Remove line from other months in this year
                const yearNode = monthNode.closest('.year-node');
                if (yearNode) {
                    yearNode.querySelectorAll('.month-node.show-line').forEach(n => {
                        n.classList.remove('show-line');
                    });
                }

                // Update active level and line positions
                this.updateActiveLevel();
            }
        }
    }

    updateActiveLevel() {
        const tree = this.tree;

        // Determine the deepest expanded level
        const hasExpandedEntries = tree.querySelector('.month-node.expanded');
        const hasExpandedMonths = tree.querySelector('.year-node.expanded');

        if (hasExpandedEntries) {
            tree.dataset.activeLevel = 'entries';
            this.positionLine('.line-entries', '.month-node.expanded .tree-entry');
        } else if (hasExpandedMonths) {
            tree.dataset.activeLevel = 'months';
            // Find the expanded year and position line for its months
            const expandedYear = tree.querySelector('.year-node.expanded');
            if (expandedYear) {
                const year = expandedYear.dataset.year;
                this.positionLine('.line-months', `.year-node[data-year="${year}"] > .tree-children > .month-node`);
            }
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

        // Find the first and last items with visible toggles
        const firstItem = items[0];
        const lastItem = items[items.length - 1];

        const firstToggle = firstItem?.querySelector('.tree-toggle');
        const lastToggle = lastItem?.querySelector('.tree-toggle');

        if (!firstToggle || !lastToggle) {
            return;
        }

        // Calculate positions using getBoundingClientRect for accuracy
        const treeRect = this.tree.getBoundingClientRect();
        const firstRect = firstToggle.getBoundingClientRect();
        const lastRect = lastToggle.getBoundingClientRect();

        // Calculate left position (center of toggle)
        const left = firstRect.left - treeRect.left + (firstRect.width / 2);

        // Calculate top position (center of first toggle)
        const top = firstRect.top - treeRect.top + (firstRect.height / 2);

        // Calculate bottom position (distance from tree bottom to center of last toggle)
        const bottom = treeRect.bottom - (lastRect.top + (lastRect.height / 2));

        // Apply positions
        line.style.left = `${left}px`;
        line.style.top = `${top}px`;
        line.style.bottom = `${bottom}px`;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new JournalTree();
});
