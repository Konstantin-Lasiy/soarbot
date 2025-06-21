import { useState } from 'react'

function StationTable({ runData }) {
  const [expandedRow, setExpandedRow] = useState(null)

  // Extract all station details from run data
  const stationDetails = runData.flatMap(run => 
    (run.station_details || []).map(station => ({
      ...station,
      run_id: run.run_id,
      start_time: run.start_time,
      winter_mode: run.winter_mode
    }))
  )

  const getStatusColor = (station) => {
    if (!station.enabled) return 'bg-gray-100 text-gray-600'
    if (station.api_error) return 'bg-red-100 text-red-700'
    if (!station.has_data) return 'bg-yellow-100 text-yellow-700'
    if (station.cooldown_active) return 'bg-blue-100 text-blue-700'
    if (station.notification_sent) return 'bg-green-100 text-green-700'
    if (station.conditions_result?.overall_met) return 'bg-purple-100 text-purple-700'
    return 'bg-red-100 text-red-700'
  }

  const getStatusText = (station) => {
    if (!station.enabled) return 'Disabled'
    if (station.api_error) return 'API Error'
    if (!station.has_data) return 'No Data'
    if (station.cooldown_active) return 'Cooldown'
    if (station.notification_sent) return 'Sent ✓'
    if (station.conditions_result?.overall_met) return 'Conditions Met'
    return 'Failed'
  }

  const getFailedConditions = (station) => {
    if (!station.conditions_result?.checks) return []
    return Object.entries(station.conditions_result.checks)
      .filter(([_, check]) => !check.passed)
      .map(([name, _]) => name)
  }

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  const toggleRow = (index) => {
    setExpandedRow(expandedRow === index ? null : index)
  }

  return (
    <div className="bg-white rounded-lg shadow mb-8">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900">Station Analysis</h2>
        <p className="text-sm text-gray-600">Click rows to expand details</p>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Time
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Station
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Failed Conditions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {stationDetails.map((station, index) => (
              <>
                <tr 
                  key={index}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => toggleRow(index)}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatDateTime(station.start_time)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {station.station_name}
                    </div>
                    <div className="text-sm text-gray-500">
                      Priority: {station.priority}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {station.user_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(station)}`}>
                      {getStatusText(station)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-wrap gap-1">
                      {getFailedConditions(station).map(condition => (
                        <span key={condition} className="inline-flex px-2 py-1 text-xs bg-red-100 text-red-700 rounded">
                          {condition.replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
                
                {expandedRow === index && (
                  <tr>
                    <td colSpan="5" className="px-6 py-4 bg-gray-50">
                      <div className="space-y-4">
                        {/* Weather Data */}
                        {station.latest_weather_data && (
                          <div>
                            <h4 className="font-medium text-gray-900 mb-2">Latest Weather Data</h4>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                              <div>
                                <span className="font-medium">Wind Speed:</span>
                                <div>{station.latest_weather_data.wind_speeds?.join(', ')} mph</div>
                              </div>
                              <div>
                                <span className="font-medium">Wind Direction:</span>
                                <div>{station.latest_weather_data.wind_directions?.join(', ')}°</div>
                              </div>
                              <div>
                                <span className="font-medium">Gusts:</span>
                                <div>{station.latest_weather_data.wind_gusts?.join(', ')} mph</div>
                              </div>
                              <div>
                                <span className="font-medium">Precipitation:</span>
                                <div>{station.latest_weather_data.precipitation?.join(', ')} in</div>
                              </div>
                            </div>
                          </div>
                        )}
                        
                        {/* Condition Details */}
                        {station.conditions_result?.checks && (
                          <div>
                            <h4 className="font-medium text-gray-900 mb-2">Condition Checks</h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                              {Object.entries(station.conditions_result.checks).map(([name, check]) => (
                                <div key={name} className={`p-3 rounded ${check.passed ? 'bg-green-50' : 'bg-red-50'}`}>
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="font-medium">{name.replace('_', ' ')}</span>
                                    <span className={check.passed ? 'text-green-600' : 'text-red-600'}>
                                      {check.passed ? '✓' : '✗'}
                                    </span>
                                  </div>
                                  <div className="text-xs text-gray-600">
                                    Criteria: {check.criteria}
                                  </div>
                                  {check.values && (
                                    <div className="text-xs text-gray-600">
                                      Values: {Array.isArray(check.values) ? check.values.join(', ') : check.values}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Error Details */}
                        {station.api_error && (
                          <div>
                            <h4 className="font-medium text-red-700 mb-2">API Error</h4>
                            <div className="text-sm text-red-600 bg-red-50 p-3 rounded">
                              {station.api_error}
                            </div>
                          </div>
                        )}
                        
                        {station.notification_error && (
                          <div>
                            <h4 className="font-medium text-red-700 mb-2">Notification Error</h4>
                            <div className="text-sm text-red-600 bg-red-50 p-3 rounded">
                              {station.notification_error}
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default StationTable