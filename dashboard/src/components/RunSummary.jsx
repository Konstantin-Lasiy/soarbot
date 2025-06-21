function RunSummary({ runData }) {
  const totalRuns = runData.length
  const successfulRuns = runData.filter(run => run.success).length
  const successRate = totalRuns > 0 ? ((successfulRuns / totalRuns) * 100).toFixed(1) : 0
  const totalNotifications = runData.reduce((sum, run) => sum + (run.notifications_sent || 0), 0)
  const avgRuntime = totalRuns > 0 ? 
    (runData.reduce((sum, run) => sum + (run.runtime_seconds || 0), 0) / totalRuns).toFixed(2) : 0

  const cards = [
    {
      title: 'Total Runs',
      value: totalRuns,
      icon: '🔄',
      color: 'bg-blue-500'
    },
    {
      title: 'Success Rate',
      value: `${successRate}%`,
      icon: '✅',
      color: successRate >= 95 ? 'bg-green-500' : successRate >= 80 ? 'bg-yellow-500' : 'bg-red-500'
    },
    {
      title: 'Notifications Sent',
      value: totalNotifications,
      icon: '📱',
      color: 'bg-purple-500'
    },
    {
      title: 'Avg Runtime',
      value: `${avgRuntime}s`,
      icon: '⏱️',
      color: 'bg-indigo-500'
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {cards.map((card, index) => (
        <div key={index} className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className={`${card.color} rounded-lg p-3 mr-4`}>
              <span className="text-2xl">{card.icon}</span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">{card.title}</p>
              <p className="text-3xl font-bold text-gray-900">{card.value}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default RunSummary