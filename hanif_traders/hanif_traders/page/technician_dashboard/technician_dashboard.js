frappe.pages['technician-dashboard'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Technician Dashboard',
        single_column: true
    });

    // Load Leaflet from CDNs for reliability if local assets path is uncertain
    Promise.all([
        frappe.require("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"),
        frappe.require("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js")
    ]).then(() => {
        wrapper.dashboard = new TechnicianDashboard(wrapper);
    });
}

class TechnicianDashboard {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.body = $(this.wrapper).find('.layout-main-section');
        this.make_ui();
        this.refresh();

        // Auto refresh every 60 seconds
        setInterval(() => this.refresh(), 60000);
    }

    make_ui() {
        this.body.html(`
            <div class="technician-dashboard">
                <style>
                    .kpi-row { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
                    .kpi-card { 
                        background: var(--card-bg, #fff); 
                        border: 1px solid var(--border-color, #d1d8dd); 
                        border-radius: 8px; 
                        padding: 20px; 
                        flex: 1; 
                        min-width: 200px;
                        text-align: center;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                        display: flex; flex-direction: column; justify-content: center;
                    }
                    .kpi-value { font-size: 2.5rem; font-weight: 700; color: var(--text-color); }
                    .kpi-label { font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; margin-top: 5px; }
                    .dashboard-section { margin-bottom: 30px; }
                    .section-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 10px; color: var(--text-color); }
                    #technician-map { height: 450px; width: 100%; border-radius: 8px; border: 1px solid var(--border-color); background: #eee; }
                    .leaderboard-item { padding: 10px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
                    .leaderboard-item:last-child { border-bottom: none; }
                    .leaderboard-container { background: var(--card-bg, #fff); border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }
                </style>
                
                <!-- 1. KPI Summary -->
                <div class="kpi-row">
                    <div class="kpi-card">
                        <div class="kpi-value" id="total-techs">-</div>
                        <div class="kpi-label">Total Technicians</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value" id="active-techs">-</div>
                        <div class="kpi-label">Active (On Duty)</div>
                    </div>
                </div>

                <!-- 2. Live Map -->
                <div class="dashboard-section">
                    <div class="section-title">Live Technician Map</div>
                    <div id="technician-map"></div>
                </div>

                <!-- 3. Complaints & Metrics -->
                <div class="row">
                    <div class="col-md-8">
                        <div class="section-title">Complaint Status</div>
                        <div class="kpi-row">
                            <div class="kpi-card">
                                <div class="kpi-value" id="open-complaints">-</div>
                                <div class="kpi-label">Open Complaints</div>
                            </div>
                            <div class="kpi-card">
                                <div class="kpi-value" id="assigned-complaints">-</div>
                                <div class="kpi-label">Assigned Complaints</div>
                            </div>
                            <div class="kpi-card">
                                <div class="kpi-value" id="avg-res-time">-</div>
                                <div class="kpi-label">Avg Res Time (Hrs)</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="section-title">Leaderboard (This Month)</div>
                        <div class="leaderboard-container" id="leaderboard-list">
                            <div style="padding:20px;text-align:center;color:var(--text-muted)">Loading...</div>
                        </div>
                    </div>
                </div>
            </div>
        `);

        try {
            this.init_map();
        } catch (e) {
            console.error("Map init failed", e);
            $('#technician-map').html('<div style="display:flex;align-items:center;justify-content:center;height:100%;color:red">Map failed to load</div>');
        }
    }

    init_map() {
        if (!window.L) {
            console.log("Leaflet not ready, retrying...");
            setTimeout(() => this.init_map(), 500);
            return;
        }

        // Default to a central location, will fitBounds later
        this.map = L.map('technician-map').setView([0, 0], 2);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
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
                    $('#map-status').remove();
                    this.update_map(r.message.data);
                } else {
                    // Fallback: Fetch all if no active technicians found
                    frappe.call({
                        method: "hanif_traders.api.location.get_latest_locations",
                        args: { on_duty_only: 0 },
                        callback: (r2) => {
                            if (r2.message && r2.message.status === 'success' && r2.message.data && r2.message.data.length > 0) {
                                if ($('#map-status').length === 0) {
                                    $('<div id="map-status" style="text-align:center;color:orange;margin-bottom:5px">No active technicians. Showing last known locations.</div>').insertBefore('#technician-map');
                                }
                                this.update_map(r2.message.data);
                            } else {
                                if ($('#map-status').length === 0) {
                                    $('<div id="map-status" style="text-align:center;color:gray;margin-bottom:5px">No location data available.</div>').insertBefore('#technician-map');
                                }
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
                var marker = L.marker(latlng).bindPopup(`<b>${loc.technician}</b><br>${loc.captured_at}`);
                this.markers.addLayer(marker);
                bounds.push(latlng);
            });
            // Add a little padding
            this.map.fitBounds(bounds, { padding: [50, 50] });
        } else {
            // If no locations, maybe set a default view or do nothing
        }
    }

    fetch_leaderboard() {
        frappe.call({
            method: "hanif_traders.hanif_traders.page.technician_dashboard.technician_dashboard.get_leaderboard",
            callback: (r) => {
                if (r.message && Array.isArray(r.message)) {
                    let html = '';
                    r.message.forEach((item, index) => {
                        let icon = index < 3 ? '🏆' : '#' + (index + 1);
                        html += `<div class="leaderboard-item">
                            <div><span style="margin-right:8px;font-weight:bold">${icon}</span> <span>${item.technician}</span></div>
                            <strong style="font-size:1.1em">${item.count}</strong>
                        </div>`;
                    });

                    if (html === '') html = '<div style="padding:20px;text-align:center">No data</div>';

                    $('#leaderboard-list').html(html);
                } else {
                    $('#leaderboard-list').html('<div style="padding:20px;text-align:center">No data available</div>');
                }
            }
        });
    }
}
