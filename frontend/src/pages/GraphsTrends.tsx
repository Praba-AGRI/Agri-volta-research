import { useState, useEffect, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { useStore } from '../store/useStore';
import { Download, Filter, BarChart3, ShieldCheck, Cpu } from 'lucide-react';

export default function GraphsTrends() {
  const { datasetMode, timeRange, setTimeRange } = useStore();
  
  const [selectedParams, setSelectedParams] = useState<string[]>(['soil_moisture']);
  const [selectedZone, setSelectedZone] = useState('B');
  const [resolution, setResolution] = useState('5m');
  
  const [data, setData] = useState<Record<string, {timestamp: string, value: number, quality: string, source: string}[]>>({});
  const [loading, setLoading] = useState(true);

  const isField = datasetMode === 'FIELD';

  const availableParams = [
    { id: 'soil_moisture', label: 'Soil moisture', color: '#3b82f6' },
    { id: 'air_temperature', label: 'Air temperature', color: '#ef4444' },
    { id: 'relative_humidity', label: 'Relative humidity', color: '#0ea5e9' },
    { id: 'vpd', label: 'VPD', color: '#8b5cf6' },
    { id: 'soil_temperature', label: 'Soil temperature', color: '#f59e0b' },
    { id: 'radiation', label: 'Radiation', color: '#eab308' }
  ];

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const start = timeRange === '24h' ? '-24h' : timeRange === '3d' ? '-3d' : timeRange === '7d' ? '-7d' : '-30d';
        const params = { start, resolution, mode: datasetMode };
        const fetchedData: any = {};
        
        for (const param of selectedParams) {
           let zonesToFetch = selectedZone === 'Both' ? ['A', 'B'] : [selectedZone];
           for (const z of zonesToFetch) {
              const res = await axios.get('http://localhost:8000/api/history', { params: { ...params, zone: z, parameter: param } });
              const actualData = res.data.data.map((d: any) => ({
                 ...d,
                 quality: d.quality || (isField ? 'VALID' : 'PHYSICS_SIMULATED'),
                 source: d.source || (isField ? 'SD_ARCHIVE' : 'SIMULATION_ENGINE')
              }));
              fetchedData[`${param}_${z}`] = actualData;
           }
        }
        
        setData(fetchedData);
      } catch (err) {
        console.error("Failed to fetch history", err);
      } finally {
        setLoading(false);
      }
    };
    
    if (selectedParams.length > 0) {
      fetchData();
    } else {
      setData({});
      setLoading(false);
    }
  }, [datasetMode, timeRange, selectedZone, selectedParams, resolution]);

  const handleExportCSV = () => {
    const primaryParam = selectedParams[0] || 'soil_moisture';
    const exportUrl = `http://localhost:8000/api/export/csv?zone=${selectedZone}&parameter=${primaryParam}&resolution=${resolution}&mode=${datasetMode}`;
    window.open(exportUrl, '_blank');
  };

  const toggleParam = (id: string) => {
     setSelectedParams(prev => 
        prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
     );
  };
  
  const stats = useMemo(() => {
     if (selectedParams.length === 0) return null;
     const primaryParam = selectedParams[0];
     const z = selectedZone === 'Both' ? 'B' : selectedZone;
     const seriesData = data[`${primaryParam}_${z}`];
     
     if (!seriesData || seriesData.length === 0) return null;
     
     const validValues = seriesData.map(d => d.value).filter(v => v !== null && v !== undefined) as number[];
     if (validValues.length === 0) return null;
     
     const min = Math.min(...validValues);
     const max = Math.max(...validValues);
     const mean = validValues.reduce((a, b) => a + b, 0) / validValues.length;
     
     return {
        paramName: availableParams.find(p => p.id === primaryParam)?.label,
        count: validValues.length,
        min: min.toFixed(3),
        max: max.toFixed(3),
        mean: mean.toFixed(3)
     };
  }, [data, selectedParams, selectedZone]);

  const getOption = () => {
    const seriesList: any[] = [];
    let xAxisTimes: string[] = [];

    selectedParams.forEach((paramId) => {
      const paramInfo = availableParams.find(p => p.id === paramId);
      const zonesToFetch = selectedZone === 'Both' ? ['A', 'B'] : [selectedZone];
      
      zonesToFetch.forEach((z) => {
        const seriesKey = `${paramId}_${z}`;
        const seriesData = data[seriesKey] || [];
        
        if (seriesData.length > 0 && xAxisTimes.length === 0) {
          xAxisTimes = seriesData.map(d => d.timestamp);
        }

        seriesList.push({
          name: `${paramInfo?.label || paramId} (${z})`,
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: seriesData.map(d => d.value),
          lineStyle: { width: 2.5 }
        });
      });
    });

    return {
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0 },
      grid: { top: 30, right: 30, bottom: 50, left: 50 },
      dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 25 }],
      xAxis: { type: 'category', data: xAxisTimes, boundaryGap: false },
      yAxis: { type: 'value', scale: true },
      series: seriesList
    };
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-slate-800">Historical Trends & Multi-Parameter Series</h1>
            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full border flex items-center ${
              isField ? 'bg-teal-100 text-teal-800 border-teal-200' : 'bg-amber-100 text-amber-800 border-amber-200'
            }`}>
              {isField ? <ShieldCheck className="w-3.5 h-3.5 mr-1" /> : <Cpu className="w-3.5 h-3.5 mr-1" />}
              {isField ? 'FIELD ARCHIVE (field_2026_v1)' : 'SIMULATION ENGINE (simulation_v1)'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {isField
              ? 'Quality-controlled 5-minute analytical telemetry records from physical SD-card field archive.'
              : 'Continuous differential time-series generated by closed-loop digital twin physics model.'}
          </p>
        </div>

        <button
          onClick={handleExportCSV}
          className={`flex items-center space-x-2 px-4 py-2 text-xs font-bold rounded-lg transition text-white shadow ${
            isField ? 'bg-teal-700 hover:bg-teal-800' : 'bg-amber-700 hover:bg-amber-800'
          }`}
        >
          <Download className="w-4 h-4" />
          <span>Export {datasetMode} Series CSV</span>
        </button>
      </div>

      {/* Control Filters */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Time Horizon</label>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as any)}
              className="w-full border border-slate-200 rounded-lg p-2 text-xs font-bold text-slate-700 bg-slate-50"
            >
              <option value="24h">Last 24 Hours</option>
              <option value="3d">Last 3 Days</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days (Full Field Campaign)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Target Zone</label>
            <select
              value={selectedZone}
              onChange={(e) => setSelectedZone(e.target.value)}
              className="w-full border border-slate-200 rounded-lg p-2 text-xs font-bold text-slate-700 bg-slate-50"
            >
              <option value="A">Zone A (Control / Full Sun)</option>
              <option value="B">Zone B (Agrivoltaic Canopy)</option>
              <option value="Both">Both Zones (Overlay)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Resampling Resolution</label>
            <select
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              className="w-full border border-slate-200 rounded-lg p-2 text-xs font-bold text-slate-700 bg-slate-50"
            >
              <option value="5m">5 Minutes (Native Analytical)</option>
              <option value="1h">1 Hour (Hourly Mean)</option>
              <option value="1d">1 Day (Daily Mean)</option>
            </select>
          </div>
        </div>

        {/* Multi-parameter Selectors */}
        <div>
          <div className="text-xs font-bold text-slate-600 uppercase mb-2 flex items-center">
            <Filter className="w-3.5 h-3.5 mr-1" />
            Select Parameters to Compare:
          </div>
          <div className="flex flex-wrap gap-2">
            {availableParams.map((p) => {
              const isSelected = selectedParams.includes(p.id);
              return (
                <button
                  key={p.id}
                  onClick={() => toggleParam(p.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center space-x-2 transition border ${
                    isSelected
                      ? (isField ? 'bg-teal-50 border-teal-300 text-teal-900 shadow-sm' : 'bg-amber-50 border-amber-300 text-amber-900 shadow-sm')
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.color }}></span>
                  <span>{p.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Summary Statistics Card */}
      {stats && (
        <div className={`text-white rounded-xl p-4 shadow flex flex-wrap items-center justify-between gap-4 ${
          isField ? 'bg-teal-900' : 'bg-amber-900'
        }`}>
          <div className="flex items-center space-x-3">
            <BarChart3 className="w-5 h-5" />
            <div>
              <div className="text-[10px] font-bold uppercase opacity-80">
                {isField ? 'Field Analytical Summary' : 'Digital Twin Simulation Summary'}
              </div>
              <div className="text-sm font-bold">{stats.paramName} (Zone {selectedZone})</div>
            </div>
          </div>

          <div className="flex items-center space-x-6 text-xs">
            <div>
              <span className="opacity-80">Mean:</span> <span className="font-bold text-white text-sm">{stats.mean}</span>
            </div>
            <div>
              <span className="opacity-80">Min:</span> <span className="font-bold text-white text-sm">{stats.min}</span>
            </div>
            <div>
              <span className="opacity-80">Max:</span> <span className="font-bold text-white text-sm">{stats.max}</span>
            </div>
            <div>
              <span className="opacity-80">Samples:</span> <span className="font-bold text-white text-sm">{stats.count}</span>
            </div>
          </div>
        </div>
      )}

      {/* Chart Canvas */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm min-h-[420px]">
        {loading ? (
          <div className="flex items-center justify-center h-80 text-slate-400 text-sm font-medium">
            Loading {datasetMode} time-series dataset...
          </div>
        ) : selectedParams.length === 0 ? (
          <div className="flex items-center justify-center h-80 text-slate-400 text-sm font-medium">
            Please select at least one parameter above to render chart.
          </div>
        ) : (
          <ReactECharts option={getOption()} style={{ height: '420px', width: '100%' }} />
        )}
      </div>
    </div>
  );
}
