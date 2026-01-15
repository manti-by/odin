let temperatureChartInstance = null;

function initTemperatureChart(chartData, options = null) {
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

    const timestamps = chartData.timestamps.map(timestamp => moment(timestamp).toDate());

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

    const yMin = options?.y_min ?? 20;
    const yMax = options?.y_max ?? 45;
    const yTitle = options?.y_title ?? 'Температура (°C)';
    const xTitle = options?.x_title ?? 'Время';
    const timeUnit = options?.time_unit ?? 'minute';
    const timeTooltipFormat = options?.time_tooltip_format ?? 'll HH:mm';

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
                        unit: timeUnit,
                        tooltipFormat: timeTooltipFormat,
                    },
                    title: {
                        display: true,
                        text: xTitle
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: yTitle
                    },
                    min: yMin,
                    max: yMax
                }
            }
        }
    });
}

