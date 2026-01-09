/**
 * Hedlin Family Journal - Accordion Navigation
 *
 * Three-level navigation: Years → Months → Entries
 */

class JournalAccordion {
    constructor() {
        this.accordion = document.getElementById('accordion');
        this.yearsLevel = this.accordion.querySelector('[data-level="years"]');
        this.monthsLevel = this.accordion.querySelector('[data-level="months"]');
        this.entriesLevel = this.accordion.querySelector('[data-level="entries"]');
        this.monthsContainer = document.getElementById('months-container');
        this.entriesContainer = document.getElementById('entries-container');
        this.monthsBack = document.getElementById('months-back');
        this.entriesBack = document.getElementById('entries-back');
        this.monthsYearSpan = document.getElementById('months-year');
        this.entriesMonthYearSpan = document.getElementById('entries-month-year');

        this.currentYear = null;
        this.currentMonth = null;

        this.init();
    }

    init() {
        // Year clicks - all years are clickable
        this.yearsLevel.querySelectorAll('.nav-item[data-year]').forEach(btn => {
            btn.addEventListener('click', () => {
                const year = parseInt(btn.dataset.year);
                this.showMonths(year);
            });
        });

        // Back button to years
        this.monthsBack.addEventListener('click', () => {
            this.showYears();
        });

        // Back button to months
        this.entriesBack.addEventListener('click', () => {
            this.showMonths(this.currentYear);
        });

        // Keyboard navigation
        this.accordion.addEventListener('keydown', (e) => this.handleKeydown(e));

        // Check URL hash for navigation state (e.g., #1983-7 for July 1983)
        this.handleHashOnLoad();
    }

    handleHashOnLoad() {
        const hash = window.location.hash;
        if (hash) {
            // Parse hash format: #year-month (e.g., #1983-7) or #year (e.g., #1983)
            const matchMonth = hash.match(/^#(\d+)-(\d+)$/);
            const matchYear = hash.match(/^#(\d+)$/);

            if (matchMonth) {
                const year = parseInt(matchMonth[1]);
                const month = parseInt(matchMonth[2]);
                // Navigate to the year and show entries for that month
                this.showMonths(year);
                setTimeout(() => {
                    this.showEntries(year, month);
                }, 50);
            } else if (matchYear) {
                const year = parseInt(matchYear[1]);
                // Just show the months for this year
                this.showMonths(year);
            }
        }
    }

    showMonths(year) {
        this.currentYear = year;
        this.monthsYearSpan.textContent = year;
        // Update hash to reflect current year
        window.location.hash = `${year}`;

        // Clear and populate months
        this.monthsContainer.innerHTML = '';

        const months = journalData.months[year] || [];
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];

        // Show all 12 months
        for (let m = 1; m <= 12; m++) {
            const monthData = months.find(mo => mo.number === m);
            const hasEntries = monthData && monthData.hasEntries;

            const btn = document.createElement('button');
            btn.className = 'nav-item';
            if (!hasEntries) {
                btn.classList.add('muted');
            }
            btn.dataset.month = m;
            btn.textContent = monthNames[m - 1];

            // All months are clickable
            btn.addEventListener('click', () => {
                this.showEntries(year, m);
            });

            this.monthsContainer.appendChild(btn);
        }

        // Transition
        this.yearsLevel.hidden = true;
        this.monthsLevel.hidden = false;
        this.entriesLevel.hidden = true;

        // Focus first month
        const firstMonth = this.monthsContainer.querySelector('.nav-item');
        if (firstMonth) {
            firstMonth.focus();
        }
    }

    showEntries(year, month) {
        this.currentMonth = month;
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        this.entriesMonthYearSpan.textContent = `${monthNames[month - 1]} ${year}`;
        // Update hash to reflect current year and month
        window.location.hash = `${year}-${month}`;

        // Clear and populate entries
        this.entriesContainer.innerHTML = '';

        const key = `${year}-${month}`;
        const entries = journalData.entries[key] || [];

        entries.forEach(entry => {
            const link = document.createElement('a');
            link.className = 'entry-item';
            link.href = entry.url;

            const daySpan = document.createElement('span');
            daySpan.className = 'entry-day';
            daySpan.textContent = entry.day;

            const previewSpan = document.createElement('span');
            previewSpan.className = 'entry-preview';
            previewSpan.textContent = entry.preview;

            link.appendChild(daySpan);
            link.appendChild(previewSpan);
            this.entriesContainer.appendChild(link);
        });

        // Transition
        this.yearsLevel.hidden = true;
        this.monthsLevel.hidden = true;
        this.entriesLevel.hidden = false;

        // Focus first entry
        const firstEntry = this.entriesContainer.querySelector('.entry-item');
        if (firstEntry) {
            firstEntry.focus();
        }
    }

    showYears() {
        this.currentYear = null;
        this.currentMonth = null;
        // Clear hash
        window.location.hash = '';

        // Transition
        this.yearsLevel.hidden = false;
        this.monthsLevel.hidden = true;
        this.entriesLevel.hidden = true;

        // Focus current year if available
        if (this.currentYear) {
            const yearBtn = this.yearsLevel.querySelector(`[data-year="${this.currentYear}"]`);
            if (yearBtn) {
                yearBtn.focus();
            }
        }
    }

    handleKeydown(e) {
        const target = e.target;
        const items = Array.from(target.parentElement.querySelectorAll('.nav-item, .entry-item'));
        const currentIndex = items.indexOf(target);

        if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
            e.preventDefault();
            const nextIndex = (currentIndex + 1) % items.length;
            items[nextIndex]?.focus();
        } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
            e.preventDefault();
            const prevIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
            items[prevIndex]?.focus();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            if (!this.entriesLevel.hidden) {
                this.showMonths(this.currentYear);
            } else if (!this.monthsLevel.hidden) {
                this.showYears();
            }
        } else if (e.key === 'Enter' || e.key === ' ') {
            if (target.classList.contains('entry-item')) {
                return; // Let default link behavior happen
            }
            e.preventDefault();
            target.click();
        }
    }
}

// Initialize when DOM is ready
if (typeof journalData !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        new JournalAccordion();
    });
}
