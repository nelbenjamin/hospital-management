// Add any custom JavaScript functionality here

document.addEventListener('DOMContentLoaded', function() {
    // Animation for dashboard cards
    const dashboardCards = document.querySelectorAll('.dashboard-card');
    dashboardCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.2}s`;
        card.classList.add('animated-count');
    });
    
    // Confirm before deleting
    const deleteButtons = document.querySelectorAll('.btn-delete');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });
    
    // Real-time validation for forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Add any custom validation logic here
            const dateInputs = form.querySelectorAll('input[type="date"]');
            dateInputs.forEach(input => {
                if (input.value) {
                    const inputDate = new Date(input.value);
                    const today = new Date();
                    
                    if (input.id.includes('dob') && inputDate > today) {
                        e.preventDefault();
                        alert('Date of birth cannot be in the future.');
                        input.focus();
                        return;
                    }
                    
                    if (input.id.includes('appointment') && inputDate < today) {
                        e.preventDefault();
                        alert('Appointment date cannot be in the past.');
                        input.focus();
                        return;
                    }
                }
            });
        });
    });
    
    // Add hover effects to table rows
    const tableRows = document.querySelectorAll('table tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8f9fa';
        });
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
    
    // Search functionality
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const searchValue = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('table tbody tr');
            
            tableRows.forEach(row => {
                const rowText = row.textContent.toLowerCase();
                if (rowText.includes(searchValue)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});

// Function to update time slots for appointment booking
function setupAppointmentTimeSlots() {
    console.log("Checking for appointment form elements...");
    
    const doctorSelect = document.getElementById('doctor_id');
    const dateInput = document.getElementById('appointment_date');
    const durationSelect = document.getElementById('duration');
    const timeSelect = document.getElementById('appointment_time');
    
    console.log("Found elements:", {
        doctorSelect: doctorSelect ? "Yes" : "No",
        dateInput: dateInput ? "Yes" : "No", 
        durationSelect: durationSelect ? "Yes" : "No",
        timeSelect: timeSelect ? "Yes" : "No"
    });
    
    // If we're not on the appointment page, exit
    if (!doctorSelect || !dateInput || !durationSelect || !timeSelect) {
        console.log("Not on appointment page, skipping time slot setup");
        return;
    }
    
    console.log("Setting up appointment time slots...");
    
    function updateTimeSlots() {
        console.log('updateTimeSlots() called');
        console.log('Doctor:', doctorSelect.value);
        console.log('Date:', dateInput.value);
        console.log('Duration:', durationSelect.value);
        
        if (doctorSelect.value && dateInput.value) {
            console.log('Making AJAX request to /get_available_slots...');
            
            // Show loading message
            timeSelect.innerHTML = '<option value="">Loading available slots...</option>';
            
            // Create form data
            const formData = new FormData();
            formData.append('doctor_id', doctorSelect.value);
            formData.append('appointment_date', dateInput.value);
            formData.append('duration', durationSelect.value);
            
            // Send AJAX request
            fetch('/get_available_slots', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                console.log('Response received. Status:', response.status, response.statusText);
                if (!response.ok) {
                    throw new Error('Network response was not ok: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                console.log('Data received from server:', data);
                
                // Clear existing options
                timeSelect.innerHTML = '';
                
                if (data.slots && data.slots.length > 0) {
                    console.log('Adding', data.slots.length, 'time slots');
                    // Add new options
                    data.slots.forEach(slot => {
                        const option = document.createElement('option');
                        option.value = slot;
                        option.textContent = slot;
                        timeSelect.appendChild(option);
                    });
                } else {
                    console.log('No slots available');
                    const option = document.createElement('option');
                    option.value = '';
                    option.textContent = 'No available slots for this date';
                    timeSelect.appendChild(option);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                timeSelect.innerHTML = '<option value="">Error loading slots. Check console.</option>';
            });
        } else {
            console.log('Doctor or date not selected yet');
            timeSelect.innerHTML = '<option value="">Select doctor and date first</option>';
        }
    }
    
    // Add event listeners
    doctorSelect.addEventListener('change', updateTimeSlots);
    dateInput.addEventListener('change', updateTimeSlots);
    durationSelect.addEventListener('change', updateTimeSlots);
    
    // Check for refresh button
    const refreshBtn = document.getElementById('refreshSlotsBtn');
    if (refreshBtn) {
        console.log("Found refresh button");
        refreshBtn.addEventListener('click', updateTimeSlots);
    } else {
        console.log("Refresh button not found");
    }
    
    // Initial update
    console.log("Performing initial time slot update");
    updateTimeSlots();
}

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== DOM Content Loaded ===');
    console.log('Initializing appointment time slots...');
    setupAppointmentTimeSlots();
});