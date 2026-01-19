/**
 * Hedlin Family Journal - Tree Navigation
 *
 * Nested expandable tree: Years → Months → Entries → Content
 */

class JournalTree {
    constructor() {
        this.tree = document.getElementById('tree');
        this.init();
    }

    init() {
        // Attach click handlers to all toggle buttons
        const toggles = this.tree.querySelectorAll('.tree-toggle');
        toggles.forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleNode(toggle);
            });
        });

        // Allow clicking on the label to toggle as well
        const labels = this.tree.querySelectorAll('.tree-label');
        labels.forEach(label => {
            label.addEventListener('click', (e) => {
                const node = label.parentElement;
                const toggle = node.querySelector('.tree-toggle');
                if (toggle) {
                    this.toggleNode(toggle);
                }
            });
        });

        // Allow clicking on entry preview row to toggle
        const previewRows = this.tree.querySelectorAll('.entry-preview-row');
        previewRows.forEach(row => {
            row.addEventListener('click', () => {
                const node = row.parentElement;
                const toggle = node.querySelector('.tree-toggle');
                if (toggle) {
                    this.toggleNode(toggle);
                }
            });
            row.style.cursor = 'pointer';
        });

        // Handle URL hash on load to restore expanded state
        this.handleHashOnLoad();

        // Handle hash changes (browser back/forward)
        window.addEventListener('hashchange', () => {
            this.handleHashOnLoad();
        });
    }

    toggleNode(toggle) {
        const node = toggle.parentElement;
        const children = node.querySelector('.tree-children');

        if (!children) {
            return; // Leaf node, nothing to toggle
        }

        const isExpanded = !children.hidden;

        if (isExpanded) {
            // Collapse
            children.hidden = true;
            toggle.textContent = '○';
            toggle.setAttribute('aria-expanded', 'false');
        } else {
            // Expand
            children.hidden = false;
            toggle.textContent = '●';
            toggle.setAttribute('aria-expanded', 'true');

            // Update URL hash to reflect the newly expanded node
            this.updateHash(node);
        }
    }

    updateHash(node) {
        let hash = '';

        if (node.classList.contains('entry-node')) {
            const entryId = node.dataset.entry;
            hash = `#${entryId}`;
        } else if (node.classList.contains('month-node')) {
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
            return;
        }

        // Parse hash formats:
        // #year-month-day (entry)
        // #year-month (month)
        // #year (year)
        const matchEntry = hash.match(/^#(\d+)-(\d+)-(\d+)$/);
        const matchMonth = hash.match(/^#(\d+)-(\d+)$/);
        const matchYear = hash.match(/^#(\d+)$/);

        if (matchEntry) {
            const year = parseInt(matchEntry[1]);
            const month = parseInt(matchEntry[2]);
            const day = parseInt(matchEntry[3]);
            this.expandToEntry(year, month, day);
        } else if (matchMonth) {
            const year = parseInt(matchMonth[1]);
            const month = parseInt(matchMonth[2]);
            this.expandToMonth(year, month);
        } else if (matchYear) {
            const year = parseInt(matchYear[1]);
            this.expandToYear(year);
        }
    }

    expandToYear(year) {
        const yearNode = this.tree.querySelector(`.year-node[data-year="${year}"]`);
        if (yearNode) {
            const toggle = yearNode.querySelector('.tree-toggle');
            const children = yearNode.querySelector('.tree-children');
            if (toggle && children) {
                children.hidden = false;
                toggle.textContent = '●';
                toggle.setAttribute('aria-expanded', 'true');
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
            if (toggle && children) {
                children.hidden = false;
                toggle.textContent = '●';
                toggle.setAttribute('aria-expanded', 'true');
            }
        }
    }

    expandToEntry(year, month, day) {
        this.expandToMonth(year, month);
        const entryNode = this.tree.querySelector(
            `.year-node[data-year="${year}"] .month-node[data-month="${month}"] ` +
            `.entry-node[data-entry="${year}-${month}-${day}"]`
        );
        if (entryNode) {
            const toggle = entryNode.querySelector('.tree-toggle');
            const children = entryNode.querySelector('.tree-children');
            if (toggle && children) {
                children.hidden = false;
                toggle.textContent = '●';
                toggle.setAttribute('aria-expanded', 'true');

                // Scroll the entry into view
                setTimeout(() => {
                    entryNode.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new JournalTree();
});
