frappe.pages['technician-dashboard'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Technician Dashboard',
        single_column: true
    });

    // Load Leaflet from CDNs
    Promise.all([
        frappe.require("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"),
        frappe.require("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js")
    ]).then(() => {
        wrapper.dashboard = new TechnicianDashboard(wrapper, page);
    });
}

class TechnicianDashboard {
    constructor(wrapper, page) {
        this.wrapper = wrapper;
        this.page = page;
        this.body = $(this.wrapper).find('.layout-main-section');
        this.make_ui();
        this.setup_actions();
        this.refresh();

        // Auto refresh
        setInterval(() => this.refresh(), 60000);
    }

    setup_actions() {
        this.page.add_inner_button('Full Screen', () => {
            if (!document.fullscreenElement) {
                $(this.wrapper)[0].requestFullscreen().catch(err => {
                    frappe.msgprint(`Error attempting to enable full-screen mode: ${err.message}`);
                });
            } else {
                document.exitFullscreen();
            }
        });
    }

    make_ui() {
        this.body.html(`
            <div class="technician-dashboard">
                
                <!-- 1. Top KPIs -->
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-value" id="total-techs">-</div>
                        <div class="metric-label">Total Technicians</div>
                    </div>
                    <div class="metric-card" style="border-bottom: 3px solid var(--success-color);">
                        <div class="metric-value" id="active-techs" style="color: var(--success-color)">-</div>
                        <div class="metric-label">Active (On Duty)</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="open-complaints">-</div>
                        <div class="metric-label">Open Complaints</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="assigned-complaints">-</div>
                        <div class="metric-label">Assigned</div>
                    </div>
                </div>

                <div class="dashboard-grid">
                    
                    <!-- 2. Main Map (Left - Wider) -->
                    <div class="col-two-thirds">
                        <div class="dashboard-card" style="height: 100%; padding: 0; overflow:hidden;">
                            <div id="technician-map" class="map-container" style="height: 550px; border:none; box-shadow:none;"></div>
                            <div id="map-message-overlay" style="display:none; position:absolute; top:10px; left:50%; transform:translateX(-50%); z-index:999; background:rgba(255,255,255,0.9); padding:5px 15px; border-radius:20px; font-weight:600; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                                No live data. Showing last known locations.
                            </div>
                        </div>
                    </div>

                    <!-- 3. Sidebar (Right - Leaderboard & Avg Time) -->
                    <div class="col-third" style="display: flex; flex-direction: column; gap: 24px;">
                        
                        <!-- Avg Time Card -->
                        <div class="metric-card">
                            <div class="metric-label">Avg Resolution Time</div>
                            <div class="metric-value" id="avg-res-time">-</div>
                            <div class="text-muted" style="font-size:0.8rem;">Hours (All Time)</div>
                        </div>

                        <!-- Leaderboard Card -->
                        <div class="dashboard-card" style="flex: 1;">
                            <div class="card-title" style="flex-wrap: wrap; gap: 10px;">
                                <span>🏆 Top Performers</span>
                                <div class="btn-group btn-group-xs" role="group">
                                    <button type="button" class="btn btn-default btn-xs lb-filter active" data-span="all_time">All</button>
                                    <button type="button" class="btn btn-default btn-xs lb-filter" data-span="month">Mon</button>
                                    <button type="button" class="btn btn-default btn-xs lb-filter" data-span="week">Wk</button>
                                    <button type="button" class="btn btn-default btn-xs lb-filter" data-span="today">Day</button>
                                </div>
                            </div>
                            <div id="leaderboard-list" class="leaderboard-list">
                                <div class="text-center text-muted p-4">Loading...</div>
                            </div>
                        </div>

                    </div>
                </div>

            </div>
        `);

        // Bind Filter Clicks
        this.body.find('.lb-filter').on('click', (e) => {
            this.body.find('.lb-filter').removeClass('active');
            $(e.currentTarget).addClass('active');
            this.fetch_leaderboard($(e.currentTarget).data('span'));
        });

        try {
            this.init_map();
        } catch (e) {
            console.error("Map init failed", e);
            $('#technician-map').html('<div class="text-center p-4 text-muted">Map failed to load</div>');
        }
    }

    init_map() {
        if (!window.L) {
            setTimeout(() => this.init_map(), 500);
            return;
        }

        // Centered roughly on Pakistan/Karachi default, zoom 5
        this.map = L.map('technician-map').setView([30.3753, 69.3451], 5);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(this.map);

        this.markers = L.layerGroup().addTo(this.map);
    }

    refresh() {
        this.fetch_stats();
        this.fetch_locations();
        this.fetch_leaderboard();
    }

    fetch_stats() {
        frappe.call({
            method: "hanif_traders.hanif_traders.page.technician_dashboard.technician_dashboard.get_dashboard_stats",
            callback: (r) => {
                if (r.message) {
                    $('#total-techs').text(r.message.total_technicians);
                    $('#active-techs').text(r.message.active_technicians);
                    $('#open-complaints').text(r.message.open_complaints);
                    $('#assigned-complaints').text(r.message.assigned_complaints);
                    $('#avg-res-time').text(r.message.avg_resolution_time);
                }
            }
        });
    }

    fetch_locations() {
        frappe.call({
            method: "hanif_traders.api.location.get_latest_locations",
            args: { on_duty_only: 1 },
            callback: (r) => {
                if (r.message && r.message.status === 'success' && r.message.data && r.message.data.length > 0) {
                    $('#map-message-overlay').hide();
                    this.update_map(r.message.data);
                } else {
                    // Fallback
                    frappe.call({
                        method: "hanif_traders.api.location.get_latest_locations",
                        args: { on_duty_only: 0 },
                        callback: (r2) => {
                            if (r2.message && r2.message.status === 'success' && r2.message.data && r2.message.data.length > 0) {
                                $('#map-message-overlay').show();
                                this.update_map(r2.message.data);
                            } else {
                                $('#map-message-overlay').hide();
                                // No data at all
                            }
                        }
                    });
                }
            }
        });
    }

    update_map(locations) {
        if (!this.map) return;
        this.markers.clearLayers();

        if (locations.length > 0) {
            var bounds = [];
            locations.forEach(loc => {
                var latlng = [loc.latitude, loc.longitude];

                var technician_icon = L.divIcon({
                    className: 'technician-marker',
                    html: '<div style="font-size:28px; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.2));">🧑‍🔧</div>',
                    iconSize: [30, 30],
                    iconAnchor: [15, 15]
                });

                var time_diff = this.get_time_diff(loc.captured_at);

                var marker = L.marker(latlng, { icon: technician_icon }).bindTooltip(`
                    <div style="text-align:center; line-height:1.2;">
                        <strong style="font-size:1.05em; color:#374151; display:block; margin-bottom:2px;">${loc.technician_name}</strong>
                        <span style="color:#6B7280; font-size:0.85em;">🕒 ${time_diff}</span>
                    </div>
                `, {
                    permanent: true,
                    direction: 'top',
                    className: 'tech-tooltip-card',
                    offset: [0, -15]
                });
                this.markers.addLayer(marker);
                bounds.push(latlng);
            });

            this.map.fitBounds(bounds, { padding: [50, 50] });
        }
    }

    get_time_diff(captured_at) {
        if (!captured_at) return "";
        var now = new Date();
        var captured = new Date(captured_at);
        var diff = (now - captured) / 1000; // seconds

        if (diff < 60) return Math.floor(diff) + " sec ago";
        if (diff < 3600) return Math.floor(diff / 60) + " min ago";
        if (diff < 86400) return Math.floor(diff / 3600) + " hr ago";
        return Math.floor(diff / 86400) + " days ago";
    }

    fetch_leaderboard(timespan = "all_time") {
        frappe.call({
            method: "hanif_traders.hanif_traders.page.technician_dashboard.technician_dashboard.get_leaderboard",
            args: { timespan: timespan },
            callback: (r) => {
                if (r.message && Array.isArray(r.message)) {
                    let html = '';
                    r.message.forEach((item, index) => {
                        let rankClass = `rank-${index + 1}`;
                        let rankDisplay = index + 1;

                        html += `
                        <div class="leaderboard-item ${rankClass}">
                            <div class="rank-badge">${rankDisplay}</div>
                            <div class="tech-info">
                                <div class="tech-name">${item.technician}</div>
                            </div>
                            <div class="tech-score-badge">${item.count} Points</div>
                        </div>`;
                    });

                    if (html === '') html = '<div class="text-center text-muted p-4">No data available</div>';

                    $('#leaderboard-list').html(html);
                } else {
                    $('#leaderboard-list').html('<div class="text-center text-muted p-4">No data available</div>');
                }
            }
        });
    }
}
