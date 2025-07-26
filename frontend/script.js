class FlightTracker {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8080/api';
        this.currentPage = 1;
        this.flightsPerPage = 20;
        this.allFlights = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadData();
        this.startAutoRefresh();
    }

    bindEvents() {
        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadData();
        });



        // Filter controls
        document.getElementById('apply-filters').addEventListener('click', () => {
            this.applyFilters();
        });

        document.getElementById('clear-filters').addEventListener('click', () => {
            this.clearFilters();
        });

        // Allow Enter key to apply filters
        const filterInputs = document.querySelectorAll('.filter-group input');
        filterInputs.forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.applyFilters();
                }
            });
        });



        // Pagination controls
        document.getElementById('prev-page').addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.displayCurrentPage();
            }
        });

        document.getElementById('next-page').addEventListener('click', () => {
            const totalPages = Math.ceil(this.allFlights.length / this.flightsPerPage);
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this.displayCurrentPage();
            }
        });

        document.getElementById('flights-per-page').addEventListener('change', (e) => {
            this.flightsPerPage = parseInt(e.target.value);
            this.currentPage = 1;
            this.displayCurrentPage();
        });


    }

    showLoading() {
        document.getElementById('loading').classList.add('show');
    }

    hideLoading() {
        document.getElementById('loading').classList.remove('show');
    }

    async loadData() {
        this.showLoading();
        
        try {
            // Load stats and flights
            const [stats, flights] = await Promise.all([
                this.fetchStats(),
                this.fetchFlights()
            ]);

            this.updateStats(stats);
            this.allFlights = flights;
            this.currentPage = 1;
            this.displayCurrentPage();
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Failed to load flight data. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    displayCurrentPage() {
        const startIndex = (this.currentPage - 1) * this.flightsPerPage;
        const endIndex = startIndex + this.flightsPerPage;
        const currentPageFlights = this.allFlights.slice(startIndex, endIndex);
        
        this.updateFlightsTable(currentPageFlights);
        this.updateSpecialAircraft(this.allFlights); // Use all flights for special aircraft stats
        this.updatePaginationControls();
    }

    updatePaginationControls() {
        const totalPages = Math.ceil(this.allFlights.length / this.flightsPerPage);
        const pageInfo = document.getElementById('page-info');
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        
        pageInfo.textContent = `Page ${this.currentPage} of ${totalPages} (${this.allFlights.length} flights)`;
        prevBtn.disabled = this.currentPage === 1;
        nextBtn.disabled = this.currentPage === totalPages || totalPages === 0;
    }

    async fetchStats() {
        const response = await fetch(`${this.apiBaseUrl}/stats`);
        if (!response.ok) {
            throw new Error('Failed to fetch stats');
        }
        return await response.json();
    }

    async fetchFlights() {
        const filters = this.getActiveFilters();
        const hasFilters = Object.values(filters).some(value => value !== null);
        
        let endpoint = '/flights';
        
        // Use filtered endpoint if any filters are active
        if (hasFilters) {
            endpoint = '/flights/filtered';
            const params = new URLSearchParams();
            
            if (filters.altitudeMin !== null) params.append('altitude_min', filters.altitudeMin);
            if (filters.altitudeMax !== null) params.append('altitude_max', filters.altitudeMax);
            if (filters.distanceMin !== null) params.append('distance_min', filters.distanceMin);
            if (filters.distanceMax !== null) params.append('distance_max', filters.distanceMax);
            if (filters.speedMin !== null) params.append('speed_min', filters.speedMin);
            if (filters.speedMax !== null) params.append('speed_max', filters.speedMax);
            if (filters.trackingNumber) params.append('tracking_number', filters.trackingNumber);
            
            endpoint += '?' + params.toString();
        }
        
        const response = await fetch(`${this.apiBaseUrl}${endpoint}`);
        if (!response.ok) {
            throw new Error('Failed to fetch flights');
        }
        return await response.json();
    }

    getSpecialAircraftFromFlights(flights) {
        if (!flights || flights.length === 0) {
            return { closest: null, lowest: null, fastest: null };
        }

        let closest = flights[0];
        let lowest = flights[0];
        let fastest = flights[0];

        flights.forEach(flight => {
            // Closest aircraft (minimum distance)
            if (flight.distance_to_target !== null && 
                (closest.distance_to_target === null || flight.distance_to_target < closest.distance_to_target)) {
                closest = flight;
            }

            // Lowest aircraft (minimum altitude)
            if (flight.altitude_ft !== null && 
                (lowest.altitude_ft === null || flight.altitude_ft < lowest.altitude_ft)) {
                lowest = flight;
            }

            // Fastest aircraft (maximum speed)
            if (flight.speed_kts !== null && 
                (fastest.speed_kts === null || flight.speed_kts > fastest.speed_kts)) {
                fastest = flight;
            }
        });

        return { closest, lowest, fastest };
    }

    updateStats(stats) {
        document.getElementById('total-flights').textContent = stats.total_flights.toLocaleString();
        document.getElementById('flights-today').textContent = stats.flights_today.toLocaleString();
        document.getElementById('avg-altitude').textContent = `${Math.round(stats.average_altitude_ft)} ft`;
        document.getElementById('avg-speed').textContent = `${Math.round(stats.average_speed_kts)} kts`;
    }

    updateFlightsTable(flights) {
        const tbody = document.getElementById('flights-tbody');
        tbody.innerHTML = '';
        if (flights.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-plane-slash" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>
                        <p>No flights match the current filters</p>
                        <small>Try adjusting your filter criteria</small>
                    </td>
                </tr>
            `;
            return;
        }
        flights.forEach((flight, idx) => {
            const row = this.createFlightRow(flight, idx);
            tbody.appendChild(row);
        });
        // Add click listeners for flight number links
        tbody.querySelectorAll('.flight-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const idx = e.target.getAttribute('data-idx');
                this.showFlightModal(flights[idx]);
            });
        });

    }

    createFlightRow(flight, idx) {
        const row = document.createElement('tr');
        const timestamp = new Date(flight.timestamp);
        const timeString = timestamp.toLocaleString();
        row.innerHTML = `
            <td><a href="#" class="flight-link" data-idx="${idx}"><strong>${flight.callsign || 'Unknown'}</strong></a></td>
            <td>${this.safeNumber(flight.altitude_ft)} ft</td>
            <td>${this.safeNumber(flight.speed_kts)} kts</td>
            <td>${this.safeNumber(flight.distance_to_target, 2)} km</td>
            <td>${timeString}</td>
        `;
        return row;
    }

    showFlightModal(flight) {
        const modal = document.getElementById('flight-modal');
        const details = document.getElementById('modal-details');
        details.innerHTML = `
            <p><strong>Flight Number:</strong> ${flight.callsign || 'Unknown'}</p>
            <p><strong>ICAO24:</strong> ${flight.icao24 || 'Unknown'}</p>
            <p><strong>Aircraft Type:</strong> ${flight.aircraft_type || 'Unknown'}</p>
            <p><strong>Altitude:</strong> ${this.safeNumber(flight.altitude_ft)} ft</p>
            <p><strong>Speed:</strong> ${this.safeNumber(flight.speed_kts)} kts</p>
            <p><strong>Distance to Target:</strong> ${this.safeNumber(flight.distance_to_target, 2)} km</p>
            <p><strong>Origin:</strong> ${flight.origin_airport || 'Unknown'}</p>
            <p><strong>Destination:</strong> ${flight.destination_airport || 'Unknown'}</p>
            <p><strong>Time:</strong> ${new Date(flight.timestamp).toLocaleString()}</p>
        `;
        modal.style.display = 'block';
    }

    getActiveFilters() {
        return {
            altitudeMin: this.getNumberValue('altitude-min'),
            altitudeMax: this.getNumberValue('altitude-max'),
            distanceMin: this.getNumberValue('distance-min'),
            distanceMax: this.getNumberValue('distance-max'),
            speedMin: this.getNumberValue('speed-min'),
            speedMax: this.getNumberValue('speed-max'),
            trackingNumber: this.getStringValue('tracking-number')
        };
    }

    getNumberValue(id) {
        const value = document.getElementById(id).value;
        return value === '' ? null : parseFloat(value);
    }

    getStringValue(id) {
        const value = document.getElementById(id).value;
        return value === '' ? null : value.trim();
    }

    applyFilters() {
        // Re-render the flights table with current filters
        this.currentPage = 1; // Reset to first page when applying filters
        this.loadData();
        this.showNotification('Filters applied successfully!', 'success');
    }

    clearFilters() {
        // Clear all filter inputs
        const filterInputs = document.querySelectorAll('.filter-group input');
        filterInputs.forEach(input => {
            input.value = '';
        });
        
        // Reset to first page and reload data
        this.currentPage = 1;
        this.loadData();
        this.showNotification('Filters cleared!', 'success');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        const bgColor = type === 'success' ? '#28a745' : 
                       type === 'error' ? '#dc3545' : '#17a2b8';
        const icon = type === 'success' ? 'check-circle' : 
                    type === 'error' ? 'exclamation-triangle' : 'info-circle';
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${bgColor};
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            z-index: 1001;
            max-width: 300px;
        `;
        notification.innerHTML = `
            <i class="fas fa-${icon}" style="margin-right: 10px;"></i>
            ${message}
        `;
        
        document.body.appendChild(notification);
        
        // Remove after 3-5 seconds based on type
        const timeout = type === 'error' ? 5000 : 3000;
        setTimeout(() => {
            notification.remove();
        }, timeout);
    }

    updateSpecialAircraft(allFlights) {
        const specialAircraft = this.getSpecialAircraftFromFlights(allFlights);

        // Update closest aircraft
        if (specialAircraft.closest && specialAircraft.closest.distance_to_target !== null) {
            document.querySelector('#closest-aircraft .aircraft-id').textContent = specialAircraft.closest.callsign || specialAircraft.closest.icao24 || 'Unknown';
            document.querySelector('#closest-aircraft .aircraft-distance').textContent = `${this.safeNumber(specialAircraft.closest.distance_to_target, 2)} km`;
            document.querySelector('#closest-aircraft .aircraft-altitude').textContent = `${this.safeNumber(specialAircraft.closest.altitude_ft)} ft`;
            document.querySelector('#closest-aircraft .aircraft-speed').textContent = `${this.safeNumber(specialAircraft.closest.speed_kts)} kts`;
        } else {
            document.querySelector('#closest-aircraft .aircraft-id').textContent = 'No data';
            document.querySelector('#closest-aircraft .aircraft-distance').textContent = '-';
            document.querySelector('#closest-aircraft .aircraft-altitude').textContent = '-';
            document.querySelector('#closest-aircraft .aircraft-speed').textContent = '-';
        }

        // Update lowest aircraft
        if (specialAircraft.lowest && specialAircraft.lowest.altitude_ft !== null) {
            document.querySelector('#lowest-aircraft .aircraft-id').textContent = specialAircraft.lowest.callsign || specialAircraft.lowest.icao24 || 'Unknown';
            document.querySelector('#lowest-aircraft .aircraft-altitude').textContent = `${this.safeNumber(specialAircraft.lowest.altitude_ft)} ft`;
            document.querySelector('#lowest-aircraft .aircraft-speed').textContent = `${this.safeNumber(specialAircraft.lowest.speed_kts)} kts`;
            document.querySelector('#lowest-aircraft .aircraft-distance').textContent = `${this.safeNumber(specialAircraft.lowest.distance_to_target, 2)} km`;
        } else {
            document.querySelector('#lowest-aircraft .aircraft-id').textContent = 'No data';
            document.querySelector('#lowest-aircraft .aircraft-altitude').textContent = '-';
            document.querySelector('#lowest-aircraft .aircraft-speed').textContent = '-';
            document.querySelector('#lowest-aircraft .aircraft-distance').textContent = '-';
        }

        // Update fastest aircraft
        if (specialAircraft.fastest && specialAircraft.fastest.speed_kts !== null) {
            document.querySelector('#fastest-aircraft .aircraft-id').textContent = specialAircraft.fastest.callsign || specialAircraft.fastest.icao24 || 'Unknown';
            document.querySelector('#fastest-aircraft .aircraft-speed').textContent = `${this.safeNumber(specialAircraft.fastest.speed_kts)} kts`;
            document.querySelector('#fastest-aircraft .aircraft-altitude').textContent = `${this.safeNumber(specialAircraft.fastest.altitude_ft)} ft`;
            document.querySelector('#fastest-aircraft .aircraft-distance').textContent = `${this.safeNumber(specialAircraft.fastest.distance_to_target, 2)} km`;
        } else {
            document.querySelector('#fastest-aircraft .aircraft-id').textContent = 'No data';
            document.querySelector('#fastest-aircraft .aircraft-speed').textContent = '-';
            document.querySelector('#fastest-aircraft .aircraft-altitude').textContent = '-';
            document.querySelector('#fastest-aircraft .aircraft-distance').textContent = '-';
        }
    }

    showError(message) {
        // Create a simple error notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #dc3545;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            z-index: 1001;
            max-width: 300px;
        `;
        notification.innerHTML = `
            <i class="fas fa-exclamation-triangle" style="margin-right: 10px;"></i>
            ${message}
        `;
        
        document.body.appendChild(notification);
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    startAutoRefresh() {
        // Refresh data every 30 seconds
        setInterval(() => {
            this.loadData();
        }, 30000);
    }

    // Helper to safely format numbers
    safeNumber(val, digits = 0, fallback = 'N/A') {
        if (typeof val === 'number' && !isNaN(val)) {
            return digits > 0 ? val.toFixed(digits) : Math.round(val);
        }
        return fallback;
    }




}

// Initialize the flight tracker when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new FlightTracker();
});

// Add some visual feedback for the refresh button
document.addEventListener('DOMContentLoaded', () => {
    const refreshBtn = document.getElementById('refresh-btn');
    
    refreshBtn.addEventListener('click', () => {
        const icon = refreshBtn.querySelector('i');
        icon.style.transform = 'rotate(360deg)';
        icon.style.transition = 'transform 0.5s ease';
        
        setTimeout(() => {
            icon.style.transform = 'rotate(0deg)';
        }, 500);
    });
}); 

// Modal close logic
window.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('flight-modal');
    const closeBtn = document.getElementById('modal-close');
    closeBtn.onclick = () => { modal.style.display = 'none'; };
    window.onclick = (event) => {
        if (event.target === modal) modal.style.display = 'none';
    };
}); 