import { useState, useEffect } from 'react'
import RunSummary from './components/RunSummary'
import StationTable from './components/StationTable'
import WeatherCharts from './components/WeatherCharts'
import { supabase } from './utils/supabase'

function App() {
  const [runData, setRunData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 7 days ago
    end: new Date().toISOString().split('T')[0] // today
  })

  const fetchRunData = async () => {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('run_metrics')
        .select('*')
        .gte('start_time', `${dateRange.start}T00:00:00Z`)
        .lte('start_time', `${dateRange.end}T23:59:59Z`)
        .order('start_time', { ascending: false })

      if (error) throw error
      setRunData(data || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRunData()
  }, [dateRange])

  const handleDateRangeChange = (newRange) => {
    setDateRange(newRange)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-gray-600">Loading dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-red-600">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🌬️ SoarBot Dashboard
          </h1>
          <p className="text-gray-600">
            Monitor notification runs and diagnose failures
          </p>
        </header>

        {/* Date Range Picker */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">Date Range:</label>
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => handleDateRangeChange({ ...dateRange, start: e.target.value })}
              className="border border-gray-300 rounded px-3 py-1 text-sm"
            />
            <span className="text-gray-500">to</span>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => handleDateRangeChange({ ...dateRange, end: e.target.value })}
              className="border border-gray-300 rounded px-3 py-1 text-sm"
            />
            <button
              onClick={fetchRunData}
              className="bg-blue-500 text-white px-4 py-1 rounded text-sm hover:bg-blue-600"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Run Summary Cards */}
        <RunSummary runData={runData} />

        {/* Station Analysis Table */}
        <StationTable runData={runData} />

        {/* Weather Charts */}
        <WeatherCharts runData={runData} />
      </div>
    </div>
  )
}

export default App