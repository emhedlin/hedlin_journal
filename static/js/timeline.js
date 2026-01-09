/**
 * Hedlin Family Journal - Interactive Timeline
 *
 * Features:
 * - Visual timeline with year/month markers
 * - Hover tooltips with entry previews
 * - Click to navigate to entries
 * - Zoom in/out
 * - Filter by year
 */

class JournalTimeline {
    constructor(canvasId, dataUrl, options = {}) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.dataUrl = dataUrl;
        this.tooltip = document.getElementById('timeline-tooltip');

        // Configuration
        this.config = {
            padding: { top: 60, bottom: 60, left: 60, right: 60 },
            lineColor: '#8b2e2e',
            tickColor: '#666',
            entryColor: '#8b2e2e',
            entryColorImage: '#2e5a8b',
            hoverColor: '#2e5a8b',
            fontSize: 12,
            titleFontSize: 14,
            minZoom: 0.5,
            maxZoom: 3,
            ...options
        };

        // State
        this.entries = [];
        this.filteredEntries = [];
        this.zoom = 1;
        this.pan = 0;
        this.hoveredEntry = null;
        this.selectedYear = '';
        this.isLoading = false;

        // Bind methods
        this.resize = this.resize.bind(this);
        this.handleMouseMove = this.handleMouseMove.bind(this);
        this.handleClick = this.handleClick.bind(this);
        this.handleWheel = this.handleWheel.bind(this);

        // Initialize
        this.init();
    }

    async init() {
        // Setup canvas
        this.resize();
        window.addEventListener('resize', this.resize);

        // Event listeners
        this.canvas.addEventListener('mousemove', this.handleMouseMove);
        this.canvas.addEventListener('click', this.handleClick);
        this.canvas.addEventListener('mouseleave', () => this.hideTooltip());
        this.canvas.addEventListener('wheel', this.handleWheel, { passive: false });

        // Controls
        document.getElementById('zoom-in')?.addEventListener('click', () => this.zoomIn());
        document.getElementById('zoom-out')?.addEventListener('click', () => this.zoomOut());
        document.getElementById('year-filter')?.addEventListener('change', (e) => {
            this.selectedYear = e.target.value;
            this.filterEntries();
        });

        // Load data
        await this.loadData();

        // Start render loop
        this.render();
    }

    async loadData() {
        if (this.isLoading) return;
        this.isLoading = true;

        try {
            // Load embeddings data
            const response = await fetch(this.dataUrl);
            const data = await response.json();

            this.entries = data.entries || [];
            this.filterEntries();

            // Populate year filter
            this.populateYearFilter();

        } catch (error) {
            console.error('Failed to load timeline data:', error);

            // Fallback to entries.json
            try {
                const fallbackResponse = await fetch('/static/js/entries.json');
                const fallbackData = await fallbackResponse.json();
                this.entries = (fallbackData.entries || []).map(e => ({
                    date: e.date,
                    date_display: e.title,
                    title: e.title,
                    summary: e.preview,
                    url: e.url,
                    has_images: e.has_images
                }));
                this.filterEntries();
                this.populateYearFilter();
            } catch (fallbackError) {
                console.error('Failed to load fallback data:', fallbackError);
            }
        }

        this.isLoading = false;
        this.render();
    }

    populateYearFilter() {
        const select = document.getElementById('year-filter');
        if (!select) return;

        // Get unique years
        const years = [...new Set(this.entries.map(e => e.date?.substring(0, 4)))].filter(Boolean).sort();

        // Keep the "All Years" option
        select.innerHTML = '<option value="">All Years</option>';

        years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            select.appendChild(option);
        });
    }

    filterEntries() {
        if (!this.selectedYear) {
            this.filteredEntries = this.entries;
        } else {
            this.filteredEntries = this.entries.filter(e =>
                e.date?.startsWith(this.selectedYear)
            );
        }
        this.render();
    }

    resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = 400; // Fixed height
        this.render();
    }

    get timeRange() {
        if (this.filteredEntries.length === 0) {
            return { min: new Date().getFullYear(), max: new Date().getFullYear() };
        }

        const years = this.filteredEntries
            .map(e => new Date(e.date).getFullYear())
            .filter(y => !isNaN(y));

        return {
            min: Math.min(...years),
            max: Math.max(...years)
        };
    }

    dateToX(date) {
        const { min, max } = this.timeRange;
        const year = new Date(date).getFullYear();
        const range = (max - min) || 1;

        const width = this.canvas.width - this.config.padding.left - this.config.padding.right;
        const x = this.config.padding.left + ((year - min) / range) * width;

        return x * this.zoom + this.pan * (this.zoom - 1);
    }

    xToDate(x) {
        const { min, max } = this.timeRange;
        const range = (max - min) || 1;
        const width = this.canvas.width - this.config.padding.left - this.config.padding.right;

        const adjustedX = (x - this.pan * (this.zoom - 1)) / this.zoom;
        const year = min + ((adjustedX - this.config.padding.left) / width) * range;

        return Math.round(year);
    }

    render() {
        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;
        const centerY = height / 2;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        if (this.filteredEntries.length === 0) {
            ctx.fillStyle = '#999';
            ctx.font = '14px Garamond, Georgia, serif';
            ctx.textAlign = 'center';
            ctx.fillText('No entries to display', width / 2, centerY);
            return;
        }

        const { min, max } = this.timeRange;

        // Draw main timeline
        ctx.beginPath();
        ctx.strokeStyle = this.config.lineColor;
        ctx.lineWidth = 2;
        ctx.moveTo(this.config.padding.left, centerY);
        ctx.lineTo(width - this.config.padding.right, centerY);
        ctx.stroke();

        // Draw year ticks
        ctx.fillStyle = this.config.tickColor;
        ctx.font = `${this.config.fontSize}px Garamond, Georgia, serif`;
        ctx.textAlign = 'center';

        for (let year = min; year <= max; year++) {
            const x = this.dateToX(`${year}-01-01`);

            // Skip if outside visible range
            if (x < this.config.padding.left - 50 || x > width - this.config.padding.right + 50) {
                continue;
            }

            // Draw tick mark
            ctx.beginPath();
            ctx.moveTo(x, centerY - 10);
            ctx.lineTo(x, centerY + 10);
            ctx.strokeStyle = this.config.tickColor;
            ctx.lineWidth = 1;
            ctx.stroke();

            // Draw year label
            ctx.fillText(year.toString(), x, centerY + 25);
        }

        // Draw entry markers
        const entryPositions = [];

        this.filteredEntries.forEach((entry, index) => {
            const x = this.dateToX(entry.date);

            // Skip if outside visible range
            if (x < 0 || x > width) return;

            // Alternate positions above/below timeline
            const offset = (index % 2 === 0) ? -30 : 30;
            const y = centerY + offset;

            // Check if hovered
            const isHovered = this.hoveredEntry === entry;

            // Draw marker
            ctx.beginPath();
            ctx.arc(x, y, isHovered ? 8 : 5, 0, Math.PI * 2);
            ctx.fillStyle = entry.has_images ? this.config.entryColorImage : this.config.entryColor;
            ctx.fill();

            if (isHovered) {
                ctx.strokeStyle = this.config.hoverColor;
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Draw line from timeline to marker
            ctx.beginPath();
            ctx.moveTo(x, centerY);
            ctx.lineTo(x, y + (offset > 0 ? -5 : 5));
            ctx.strokeStyle = this.config.tickColor;
            ctx.lineWidth = 1;
            ctx.stroke();

            entryPositions.push({ entry, x, y });
        });

        this.entryPositions = entryPositions;
    }

    handleMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Find hovered entry
        let found = null;

        for (const pos of this.entryPositions || []) {
            const dx = x - pos.x;
            const dy = y - pos.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < 15) {
                found = pos.entry;
                break;
            }
        }

        if (found !== this.hoveredEntry) {
            this.hoveredEntry = found;
            this.render();
        }

        if (found) {
            this.showTooltip(found, e.clientX, e.clientY);
            this.canvas.style.cursor = 'pointer';
        } else {
            this.hideTooltip();
            this.canvas.style.cursor = 'default';
        }
    }

    handleClick(e) {
        if (this.hoveredEntry) {
            window.location.href = this.hoveredEntry.url;
        }
    }

    handleWheel(e) {
        e.preventDefault();

        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        const newZoom = Math.max(this.config.minZoom, Math.min(this.config.maxZoom, this.zoom + delta));

        if (newZoom !== this.zoom) {
            this.zoom = newZoom;
            this.render();
        }
    }

    zoomIn() {
        this.zoom = Math.min(this.config.maxZoom, this.zoom + 0.2);
        this.render();
    }

    zoomOut() {
        this.zoom = Math.max(this.config.minZoom, this.zoom - 0.2);
        this.render();
    }

    showTooltip(entry, x, y) {
        if (!this.tooltip) return;

        const date = entry.date_display || entry.date || '';
        const summary = entry.summary || entry.preview || '';

        this.tooltip.innerHTML = `
            <strong>${date}</strong>
            <p style="margin: 0.5rem 0 0; font-size: 0.9em;">${summary}</p>
        `;

        this.tooltip.classList.add('visible');

        // Position tooltip
        const rect = this.tooltip.getBoundingClientRect();
        let tooltipX = x + 15;
        let tooltipY = y + 15;

        // Keep tooltip on screen
        if (tooltipX + rect.width > window.innerWidth) {
            tooltipX = x - rect.width - 15;
        }
        if (tooltipY + rect.height > window.innerHeight) {
            tooltipY = y - rect.height - 15;
        }

        this.tooltip.style.left = tooltipX + 'px';
        this.tooltip.style.top = tooltipY + 'px';
    }

    hideTooltip() {
        if (this.tooltip) {
            this.tooltip.classList.remove('visible');
        }
    }
}

// Initialize timeline when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('timeline-canvas');
    if (canvas) {
        window.timeline = new JournalTimeline('timeline-canvas', '/static/js/embeddings.json');
    }
});
