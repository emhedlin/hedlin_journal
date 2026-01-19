/**
 * Hedlin Family Journal - Tree Navigation
 *
 * Nested expandable tree: Years → Months → Entries
 */

class JournalTree {
    constructor() {
        this.tree = document.getElementById('tree');
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
    }

    updateHasExpandedClass() {
        // Check if any year or month nodes are expanded
        const hasExpanded = this.tree.querySelector('.tree-node.expanded');
        if (hasExpanded) {
            this.tree.classList.add('has-expanded');
        } else {
            this.tree.classList.remove('has-expanded');
        }
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
            node.classList.add('show-line');

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

        // Update has-expanded class on tree container
        this.updateHasExpandedClass();
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
                yearNode.classList.add('show-line');

                // Remove line from other years
                this.tree.querySelectorAll('.year-node.show-line').forEach(n => {
                    if (n !== yearNode) n.classList.remove('show-line');
                });

                // Update has-expanded class
                this.updateHasExpandedClass();
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
                // Note: Don't add show-line to months - entries don't have bullets

                // Remove line from other months in this year
                const yearNode = monthNode.closest('.year-node');
                if (yearNode) {
                    yearNode.querySelectorAll('.month-node.show-line').forEach(n => {
                        n.classList.remove('show-line');
                    });
                }
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new JournalTree();
});
