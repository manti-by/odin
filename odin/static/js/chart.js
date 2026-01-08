let temperatureChartInstance = null;

// Initialize temperature chart for DS18B20 sensors
function initTemperatureChart(chartData) {
    const canvas = document.getElementById('temperatureChart');
    if (!canvas) {
        return;
    }

    if (temperatureChartInstance && typeof temperatureChartInstance.destroy === 'function') {
        temperatureChartInstance.destroy();
        temperatureChartInstance = null;
    }

    if (Chart && typeof Chart.getChart === 'function') {
        const existing = Chart.getChart(canvas);
        if (existing) {
            existing.destroy();
        }
    }

    const ctx = canvas.getContext('2d');
    
    // Transform timestamps to Date objects
    const timestamps = chartData.timestamps.map(timestamp => moment(timestamp).toDate());
    
    // Prepare datasets for each sensor
    const datasets = chartData.sensors.map((sensor, index) => {
        const colors = [
            { border: 'rgba(255, 99, 132, 1)', fill: 'rgba(255, 99, 132, 0.2)' },
            { border: 'rgba(54, 162, 235, 1)', fill: 'rgba(54, 162, 235, 0.2)' },
            { border: 'rgba(75, 192, 192, 1)', fill: 'rgba(75, 192, 192, 0.2)' },
            { border: 'rgba(153, 102, 255, 1)', fill: 'rgba(153, 102, 255, 0.2)' },
            { border: 'rgba(255, 159, 64, 1)', fill: 'rgba(255, 159, 64, 0.2)' },
            { border: 'rgba(199, 199, 199, 1)', fill: 'rgba(199, 199, 199, 0.2)' },
            { border: 'rgba(83, 102, 255, 1)', fill: 'rgba(83, 102, 255, 0.2)' },
        ];
        
        const color = colors[index % colors.length];
        
        return {
            label: sensor.name || sensor.sensor_id,
            data: sensor.data,
            borderColor: color.border,
            backgroundColor: color.fill,
            fill: true
        };
    });
    
    // Create chart
    temperatureChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: datasets
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        tooltipFormat: 'll HH:mm',
                    },
                    title: {
                        display: true,
                        text: 'Время'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Температура (°C)',
                    },
                    min: 20,
                    max: 45
                }
            }
        }
    });
}

