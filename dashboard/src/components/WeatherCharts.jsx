import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

function WeatherCharts({ runData }) {
  // Extract weather data from recent failed stations
  const getFailedStationsWeatherData = () => {
    const failedStations = runData.flatMap(run => 
      (run.station_details || []).filter(station => 
        station.latest_weather_data && 
        !station.notification_sent && 
        station.conditions_result && 
        !station.conditions_result.overall_met
      )
    )

    // Group by station and get latest data
    const stationGroups = {}
    failedStations.forEach(station => {
      if (!stationGroups[station.station_id]) {
        stationGroups[station.station_id] = []
      }
      stationGroups[station.station_id].push(station)
    })

    return Object.entries(stationGroups).slice(0, 3) // Show top 3 stations
  }

  const createChartData = (stations, dataKey, label, color) => {
    const datasets = stations.map(([stationId, stationData], index) => {
      const latestStation = stationData[0] // Most recent
      const weatherData = latestStation.latest_weather_data
      
      if (!weatherData || !weatherData[dataKey]) return null

      return {
        label: `${latestStation.station_name} - ${label}`,
        data: weatherData[dataKey],
        borderColor: color[index % color.length],
        backgroundColor: color[index % color.length] + '20',
        tension: 0.1
      }
    }).filter(Boolean)

    // Create labels from timestamps
    const labels = stations[0]?.[1]?.[0]?.latest_weather_data?.timestamps?.map(ts => 
      new Date(ts).toLocaleTimeString()
    ) || []

    return { labels, datasets }
  }

  const failedStations = getFailedStationsWeatherData()

  if (failedStations.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Weather Trends</h2>
        <p className="text-gray-500">No recent failures with weather data to display</p>
      </div>
    )
  }

  const colors = ['#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6']

  const windSpeedData = createChartData(failedStations, 'wind_speeds', 'Wind Speed', colors)
  const windDirectionData = createChartData(failedStations, 'wind_directions', 'Wind Direction', colors)
  const windGustData = createChartData(failedStations, 'wind_gusts', 'Wind Gusts', colors)

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Weather Trends - Recent Failures</h2>
        <p className="text-sm text-gray-600 mb-6">
          Weather data from stations that recently failed condition checks
        </p>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Wind Speed (mph)</h3>
            <Line data={windSpeedData} options={chartOptions} />
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Wind Direction (°)</h3>
            <Line data={windDirectionData} options={chartOptions} />
          </div>
        </div>
        
        <div className="mt-6">
          <h3 className="text-lg font-medium text-gray-900 mb-3">Wind Gusts (mph)</h3>
          <div className="w-full lg:w-1/2">
            <Line data={windGustData} options={chartOptions} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default WeatherCharts