import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ScatterChart,
  Scatter
} from 'recharts';
import { 
  TrendingUp, 
  BarChart3, 
  Activity, 
  Zap,
  Calendar,
  Clock
} from 'lucide-react';

const Dashboard = ({ isMobile }) => {
  const [timeRange, setTimeRange] = useState('24h');
  const [chartType, setChartType] = useState('timeline');
  const [data, setData] = useState([]);

  // Generate sample data
  useEffect(() => {
    const generateData = () => {
      const now = new Date();
      const dataPoints = [];
      
      for (let i = 0; i < (timeRange === '24h' ? 24 : timeRange === '7d' ? 168 : 720); i++) {
        const time = new Date(now.getTime() - i * (timeRange === '24h' ? 3600000 : timeRange === '7d' ? 3600000 : 3600000));
        const hour = time.getHours();
        const dayOfWeek = time.getDay();
        
        // Mock energy calculation
        let baseConsumption = 100;
        const hourFactor = hour >= 17 && hour <= 20 ? 1.4 : hour >= 22 || hour <= 6 ? 0.7 : 1.0;
        const dayFactor = dayOfWeek === 0 || dayOfWeek === 6 ? 0.8 : 1.2;
        const randomFactor = 0.8 + Math.random() * 0.4;
        
        const consumption = baseConsumption * hourFactor * dayFactor * randomFactor;
        const temperature = 20 + 10 * Math.sin((time.getTime() / (1000 * 60 * 60 * 24 * 365)) * 2 * Math.PI) + Math.random() * 6 - 3;
        
        dataPoints.unshift({
          time: time.toISOString(),
          hour: hour,
          consumption: Math.round(consumption * 10) / 10,
          temperature: Math.round(temperature * 10) / 10,
          dayType: dayOfWeek === 0 || dayOfWeek === 6 ? 'Weekend' : 'Weekday',
          date: time.toLocaleDateString(),
          timeLabel: isMobile ? `${hour}:00` : time.toLocaleString()
        });
      }
      
      return dataPoints;
    };
    
    setData(generateData());
  }, [timeRange, isMobile]);

  // Aggregate data for different chart types
  const getChartData = () => {
    switch (chartType) {
      case 'hourly':
        const hourlyData = Array.from({ length: 24 }, (_, hour) => {
          const hourData = data.filter(d => d.hour === hour);
          const avgConsumption = hourData.reduce((sum, d) => sum + d.consumption, 0) / hourData.length || 0;
          return {
            hour: `${hour}:00`,
            consumption: Math.round(avgConsumption * 10) / 10,
            count: hourData.length
          };
        });
        return hourlyData;
      
      case 'temperature':
        return data.map(d => ({
          temperature: d.temperature,
          consumption: d.consumption,
          hour: d.hour
        }));
      
      default:
        return data.slice(0, isMobile ? 12 : 24);
    }
  };

  const chartData = getChartData();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="text-center">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
          Energy Analytics Dashboard
        </h2>
        <p className="text-gray-600">
          {isMobile ? 'Real-time energy insights' : 'Real-time energy consumption analytics and insights'}
        </p>
      </motion.div>

      {/* Controls */}
      <motion.div 
        variants={itemVariants}
        className={`bg-white rounded-2xl shadow-lg p-4 ${isMobile ? 'space-y-4' : 'flex justify-between items-center'}`}
      >
        <div className={`${isMobile ? 'space-y-2' : 'flex space-x-4'}`}>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <Calendar className="inline h-4 w-4 mr-1" />
              Time Range
            </label>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            >
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              <BarChart3 className="inline h-4 w-4 mr-1" />
              Chart Type
            </label>
            <select
              value={chartType}
              onChange={(e) => setChartType(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            >
              <option value="timeline">Timeline</option>
              <option value="hourly">Hourly Pattern</option>
              <option value="temperature">Temperature Impact</option>
            </select>
          </div>
        </div>

        <div className={`${isMobile ? 'grid grid-cols-2 gap-2' : 'flex space-x-4'}`}>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {Math.round(data.reduce((sum, d) => sum + d.consumption, 0) / data.length || 0)}
            </div>
            <div className="text-xs text-gray-600">Avg kWh</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {Math.max(...data.map(d => d.consumption)).toFixed(1)}
            </div>
            <div className="text-xs text-gray-600">Peak kWh</div>
          </div>
          {!isMobile && (
            <>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {Math.min(...data.map(d => d.consumption)).toFixed(1)}
                </div>
                <div className="text-xs text-gray-600">Min kWh</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {data.length}
                </div>
                <div className="text-xs text-gray-600">Data Points</div>
              </div>
            </>
          )}
        </div>
      </motion.div>

      {/* Main Chart */}
      <motion.div 
        variants={itemVariants}
        className="bg-white rounded-2xl shadow-lg p-6"
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">
            {chartType === 'timeline' && 'Energy Consumption Timeline'}
            {chartType === 'hourly' && 'Hourly Consumption Pattern'}
            {chartType === 'temperature' && 'Temperature vs Consumption'}
          </h3>
          <div className="flex items-center space-x-2">
            <Activity className="h-5 w-5 text-green-500" />
            <span className="text-sm text-gray-600">Live Data</span>
          </div>
        </div>

        <div style={{ width: '100%', height: isMobile ? 250 : 400 }}>
          <ResponsiveContainer>
            {chartType === 'timeline' && (
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey={isMobile ? "hour" : "timeLabel"} 
                  stroke="#666"
                  fontSize={isMobile ? 10 : 12}
                />
                <YAxis stroke="#666" fontSize={isMobile ? 10 : 12} />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'white'
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="consumption" 
                  stroke="#f97316" 
                  strokeWidth={2}
                  dot={{ fill: '#f97316', strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, stroke: '#f97316', strokeWidth: 2 }}
                />
              </LineChart>
            )}
            
            {chartType === 'hourly' && (
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="hour" stroke="#666" fontSize={isMobile ? 10 : 12} />
                <YAxis stroke="#666" fontSize={isMobile ? 10 : 12} />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'white'
                  }}
                />
                <Bar 
                  dataKey="consumption" 
                  fill="#3b82f6"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            )}
            
            {chartType === 'temperature' && (
              <ScatterChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey="temperature" 
                  stroke="#666" 
                  fontSize={isMobile ? 10 : 12}
                  name="Temperature (°C)"
                />
                <YAxis 
                  dataKey="consumption" 
                  stroke="#666" 
                  fontSize={isMobile ? 10 : 12}
                  name="Consumption (kWh)"
                />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'white'
                  }}
                />
                <Scatter 
                  dataKey="consumption" 
                  fill="#8b5cf6"
                />
              </ScatterChart>
            )}
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* Insights Cards */}
      <motion.div 
        variants={itemVariants}
        className={`grid gap-4 ${isMobile ? 'grid-cols-1' : 'grid-cols-2 lg:grid-cols-4'}`}
      >
        <div className="bg-gradient-to-br from-orange-500 to-red-500 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <TrendingUp className="h-8 w-8" />
            <span className="text-2xl font-bold">
              {((Math.max(...data.map(d => d.consumption)) - Math.min(...data.map(d => d.consumption))) / Math.min(...data.map(d => d.consumption)) * 100).toFixed(0)}%
            </span>
          </div>
          <h4 className="font-semibold mb-1">Peak Variation</h4>
          <p className="text-sm opacity-90">Daily consumption range</p>
        </div>

        <div className="bg-gradient-to-br from-blue-500 to-purple-500 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <Clock className="h-8 w-8" />
            <span className="text-2xl font-bold">
              {data.reduce((peak, d, i, arr) => 
                d.consumption > arr[peak].consumption ? i : peak, 0
              ) !== -1 ? data[data.reduce((peak, d, i, arr) => 
                d.consumption > arr[peak].consumption ? i : peak, 0
              )]?.hour || 0 : 0}:00
            </span>
          </div>
          <h4 className="font-semibold mb-1">Peak Hour</h4>
          <p className="text-sm opacity-90">Highest consumption time</p>
        </div>

        <div className="bg-gradient-to-br from-green-500 to-teal-500 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <Zap className="h-8 w-8" />
            <span className="text-2xl font-bold">
              {(data.reduce((sum, d) => sum + d.consumption, 0) * 0.12).toFixed(0)}
            </span>
          </div>
          <h4 className="font-semibold mb-1">Est. Cost ($)</h4>
          <p className="text-sm opacity-90">Based on $0.12/kWh</p>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <Activity className="h-8 w-8" />
            <span className="text-2xl font-bold">
              {(data.filter(d => d.dayType === 'Weekday').reduce((sum, d) => sum + d.consumption, 0) / 
                data.filter(d => d.dayType === 'Weekend').reduce((sum, d) => sum + d.consumption, 0) || 1).toFixed(1)}x
            </span>
          </div>
          <h4 className="font-semibold mb-1">Weekday Factor</h4>
          <p className="text-sm opacity-90">vs Weekend usage</p>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default Dashboard;