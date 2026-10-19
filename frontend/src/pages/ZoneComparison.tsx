import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { api } from '../services/api';
import { useStore } from '../store/useStore';
import { GitCompare, ShieldCheck, CheckCircle2, Calendar, Lock, Cpu } from 'lucide-react';

export default function ZoneComparison() {
  const { datasetMode, timeRange } = useStore();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<any>(null);
  
  const [history, setHistory] = useState<Record<string, {A: any[], B: any[]}>>({
     soil_moisture: {A: [], B: []},
     air_temperature: {A: [], B: []},
     radiation: {A: [], B: []},
     vpd: {A: [], B: []}
  });

  const isField = datasetMode === 'FIELD';

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const start = timeRange === '24h' ? '-24h' : timeRange === '7d' ? '-7d' : '-30d';
        
        // Fetch comparison summary from API
        const summaryRes = await api.get('/api/comparison/summary', { params: { mode: datasetMode } });
        setSummary(summaryRes.data);

        // Fetch historical data for synchronized charts
        const paramsList = ['soil_moisture', 'air_temperature', 'radiation', 'vpd'];
        const newHistory: any = {};
        
        await Promise.all(paramsList.map(async (param) => {
           const [resA, resB] = await Promise.all([
             api.get('/api/history', { params: { start, resolution: '5m', mode: datasetMode, zone: 'A', parameter: param } }),
             api.get('/api/history', { params: { start, resolution: '5m', mode: datasetMode, zone: 'B', parameter: param } })
           ]);
           newHistory[param] = { A: resA.data.data, B: resB.data.data };
        }));
        
        setHistory(newHistory);
      } catch (err) {
        console.error("Failed to fetch comparison data", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [datasetMode, timeRange]);

  const getSyncChartOptions = (title: string, yAxisName: string, paramA: any[], paramB: any[], colorA: string, colorB: string) => {
    const times = paramA.map((d: any) => d.timestamp);
    
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 13, fontWeight: 'bold', color: '#475569' }, top: 0 },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any[]) => {
          if (!params || !params.length) return '';
          const timeLabel = params[0].axisValue;
          const valA = params[0]?.value ?? 0;
          const valB = params[1]?.value ?? 0;
          const delta = (valB - valA).toFixed(3);
          const sign = valB >= valA ? '+' : '';
          return `<div class="font-bold border-b pb-1 mb-1">${timeLabel}</div>
                  <div class="text-xs flex justify-between space-x-4"><span>Zone A (Control):</span><span class="font-bold">${valA}</span></div>
                  <div class="text-xs flex justify-between space-x-4"><span>Zone B (Agrivoltaic):</span><span class="font-bold">${valB}</span></div>
                  <div class="text-xs font-bold text-teal-700 border-t pt-1 mt-1 flex justify-between space-x-4"><span>Delta (B − A):</span><span>${sign}${delta}</span></div>`;
        }
      },
      legend: { data: ['Zone A (Reference)', 'Zone B (Agrivoltaic)'], bottom: 0, icon: 'circle', textStyle: { fontSize: 11 } },
      grid: { top: 35, right: 20, bottom: 35, left: 45 },
      dataZoom: [{ type: 'inside', xAxisIndex: [0] }],
      xAxis: { type: 'category', data: times, boundaryGap: false, axisLabel: { color: '#94a3b8', fontSize: 9 } },
      yAxis: { type: 'value', name: yAxisName, scale: true, splitLine: { lineStyle: { type: 'dashed', color: '#f1f5f9' } }, axisLabel: { color: '#94a3b8', fontSize: 9 } },
      series: [
        { name: 'Zone A (Reference)', type: 'line', data: paramA.map((d: any) => d.value), smooth: true, symbol: 'none', itemStyle: { color: colorA }, lineStyle: { width: 2, type: 'dashed' } },
        { name: 'Zone B (Agrivoltaic)', type: 'line', data: paramB.map((d: any) => d.value), smooth: true, symbol: 'none', itemStyle: { color: colorB }, lineStyle: { width: 2.5 } }
      ]
    };
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <GitCompare className={`w-5 h-5 ${isField ? 'text-teal-700' : 'text-amber-700'}`} />
            <h2 className="text-xl font-bold text-slate-800">
              {isField ? 'Zone Microclimate Comparison & Delta (B − A) Audit' : 'Simulated Microclimate Comparison & Physics Engine Delta'}
            </h2>
            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full border flex items-center ${
              isField ? 'bg-teal-100 text-teal-800 border-teal-200' : 'bg-amber-100 text-amber-800 border-amber-200'
            }`}>
              {isField ? <ShieldCheck className="w-3.5 h-3.5 mr-1" /> : <Cpu className="w-3.5 h-3.5 mr-1" />}
              {isField ? 'field_2026_oct_v1' : 'simulation_v1'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 flex items-center">
            <Calendar className="w-3.5 h-3.5 mr-1 text-slate-400" />
            {isField
              ? 'Synchronized comparison across 2-day completed field campaign (01 Oct 2026 – 02 Oct 2026).'
              : 'Synchronized closed-loop physics model differential comparison between Zone A & Zone B.'}
          </p>
        </div>

        <div className={`flex items-center border px-3.5 py-2 rounded-xl text-xs font-bold space-x-2 ${
          isField ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-amber-50 text-amber-800 border-amber-200'
        }`}>
          <CheckCircle2 className={`w-4 h-4 ${isField ? 'text-emerald-600' : 'text-amber-600'}`} />
          <span>{isField ? 'CAMPAIGN COMPLETED (OCT 1–2, 2026)' : 'PHYSICS ENGINE SIMULATION'}</span>
        </div>
      </div>

      {/* Summary Divergence Cards */}
      {summary && summary.microclimate_metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {summary.microclimate_metrics.map((m: any, idx: number) => (
            <div key={idx} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col justify-between hover:border-teal-300 transition">
              <div>
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{m.parameter}</div>
                <div className={`text-base font-extrabold mt-1 ${isField ? 'text-teal-800' : 'text-amber-800'}`}>{m.divergence}</div>
                <div className="text-xs font-semibold text-slate-600 mt-0.5">
                  A: <span className="font-bold">{m.zone_a_val}</span> | B: <span className="font-bold">{m.zone_b_val}</span>
                </div>
              </div>
              <div className="text-[10px] text-slate-400 mt-2 pt-2 border-t border-slate-100 italic">
                {m.mechanism}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Synchronized ECharts Grid */}
      {loading ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-400 font-semibold text-sm">
          Loading synchronized 5-min microclimate comparison series...
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <ReactECharts option={getSyncChartOptions('Air Temperature (°C)', '°C', history.air_temperature.A, history.air_temperature.B, '#94a3b8', isField ? '#ef4444' : '#f59e0b')} style={{ height: '300px' }} />
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <ReactECharts option={getSyncChartOptions('Solar Irradiance Rs (W/m²)', 'W/m²', history.radiation.A, history.radiation.B, '#94a3b8', '#eab308')} style={{ height: '300px' }} />
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <ReactECharts option={getSyncChartOptions('Vapor Pressure Deficit (VPD)', 'kPa', history.vpd.A, history.vpd.B, '#94a3b8', '#8b5cf6')} style={{ height: '300px' }} />
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <ReactECharts option={getSyncChartOptions('Soil Moisture VWC (m³/m³)', 'm³/m³', history.soil_moisture.A, history.soil_moisture.B, '#94a3b8', isField ? '#3b82f6' : '#10b981')} style={{ height: '300px' }} />
          </div>
        </div>
      )}

      <div className={`p-4 border rounded-xl text-xs flex items-center justify-between ${
        isField ? 'bg-teal-50 border-teal-200 text-teal-900' : 'bg-amber-50 border-amber-200 text-amber-900'
      }`}>
        <div className="flex items-center space-x-2">
          <Lock className="w-4 h-4 shrink-0" />
          <span>
            {isField
              ? 'Microclimate comparison based on 1,152 audited 5-minute analytical observations.'
              : 'Microclimate comparison generated by numerical physical model digital twin engine.'}
          </span>
        </div>
        <span className="font-bold">{isField ? 'PUBLICATION FROZEN (field_2026_oct_v1)' : 'DIGITAL TWIN SIMULATION'}</span>
      </div>
    </div>
  );
}
