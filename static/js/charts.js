/**
 * Creates a bar chart for attendance statistics
 * @param {String} canvasId - ID of the canvas element
 * @param {Array} labels - Chart labels (e.g., course names)
 * @param {Array} values - Chart values (e.g., attendance percentages)
 * @param {Object} options - Additional chart options
 */
function createAttendanceBarChart(canvasId, labels, values, options = {}) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Generate colors based on attendance values
    const backgroundColor = values.map(value => {
        if (value >= 75) return 'rgba(40, 167, 69, 0.7)';  // Green for good attendance
        if (value >= 50) return 'rgba(255, 193, 7, 0.7)';  // Yellow for moderate attendance
        return 'rgba(220, 53, 69, 0.7)';                   // Red for poor attendance
    });
    
    const borderColor = values.map(value => {
        if (value >= 75) return 'rgba(40, 167, 69, 1)';
        if (value >= 50) return 'rgba(255, 193, 7, 1)';
        return 'rgba(220, 53, 69, 1)';
    });
    
    // Default chart options
    const defaultOptions = {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                title: {
                    display: true,
                    text: 'Attendance (%)'
                }
            }
        }
    };
    
    // Merge default options with provided options
    const chartOptions = Object.assign({}, defaultOptions, options);
    
    // Create the chart
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Attendance Percentage',
                data: values,
                backgroundColor: backgroundColor,
                borderColor: borderColor,
                borderWidth: 1
            }]
        },
        options: chartOptions
    });
}

/**
 * Creates a line chart for attendance over time
 * @param {String} canvasId - ID of the canvas element
 * @param {Array} dates - Array of date labels
 * @param {Array} presentCounts - Array of present student counts
 * @param {Number} totalStudents - Total number of students
 */
function createAttendanceLineChart(canvasId, dates, presentCounts, totalStudents) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'Students Present',
                data: presentCounts,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: totalStudents,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        footer: function(tooltipItems) {
                            const index = tooltipItems[0].dataIndex;
                            const present = presentCounts[index];
                            const percentage = (present / totalStudents * 100).toFixed(1);
                            return `Attendance: ${percentage}%`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Creates a pie chart for overall attendance summary
 * @param {String} canvasId - ID of the canvas element
 * @param {Number} presentCount - Number of days present
 * @param {Number} absentCount - Number of days absent
 */
function createAttendancePieChart(canvasId, presentCount, absentCount) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Present', 'Absent'],
            datasets: [{
                data: [presentCount, absentCount],
                backgroundColor: [
                    'rgba(40, 167, 69, 0.7)',  // Green for present
                    'rgba(220, 53, 69, 0.7)'   // Red for absent
                ],
                borderColor: [
                    'rgba(40, 167, 69, 1)',
                    'rgba(220, 53, 69, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = presentCount + absentCount;
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${context.raw} days (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}
