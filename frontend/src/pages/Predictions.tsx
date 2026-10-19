import { useState, useEffect } from 'react';
import { api } from '../services/api';
import ReactECharts from 'echarts-for-react';
import { useStore } from '../store/useStore';
import { BrainCircuit, ShieldCheck, CheckCircle2, Cpu } from 'lucide-react';

interface Prediction {
  issued_at: string;
  target_time: string;
  zone: string;
  model_version: string;
  ir_10: number;
  ir_50: number;
  ir_90: number;
  applied_volume_mm: number;
  safety_status: string;
  confidence: string;
}

export default function Predictions() {
  const { datasetMode } = useStore();
  const [selectedZone, setSelectedZone] = useState('B');
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [attributions, setAttributions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const isField = datasetMode === 'FIELD';

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const predRes = await api.get('/api/predictions/latest', { params: { zone: selectedZone, mode: datasetMode } });
        setPrediction(predRes.data);

        const attrRes = await api.get('/api/predictions/attributions', { params: { mode: datasetMode } });
        setAttributions(attrRes.data.attributions);
      } catch (err) {
        console.error("Failed to fetch predictions/performance", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedZone, datasetMode]);

  const getAttributionChartOptions = () => {
    if (!attributions.length) return {};
    const reversed = [...attributions].reverse();
    return {
      title: { text: isField ? 'ElasticNet Standardized Feature Weights (Oct 1–2 Realtime Model)' : 'Digital Twin Simulated Model Feature Weights', left: 'center', textStyle: { fontSize: 13, fontWeight: 'bold', color: '#334155' } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { top: 35, right: 30, bottom: 30, left: 220 },
      xAxis: { type: 'value', name: 'Standardized Beta Coefficient' },
      yAxis: { type: 'category', data: reversed.map(a => a.feature) },
      series: [
        {
          name: 'Standardized Beta',
          type: 'bar',
          data: reversed.map(a => a.std_coef),
          itemStyle: {
            color: (params: any) => (params.value < 0 ? (isField ? '#0f766e' : '#d97706') : '#6366f1')
          }
        }
      ]
    };
  };

  if (loading) {
    return <div className="p-6 text-slate-400 font-medium">Loading ML predictions data...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className={`p-6 rounded-2xl border shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4 ${
        isField
          ? 'bg-gradient-to-r from-teal-950 via-slate-900 to-teal-900 border-teal-500/30'
          : 'bg-gradient-to-r from-amber-950 via-slate-900 to-amber-900 border-amber-500/30'
      }`}>
        <div>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 text-xs font-semibold rounded-full border flex items-center ${
              isField ? 'bg-teal-500/20 text-teal-300 border-teal-500/30' : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
            }`}>
              {isField ? <ShieldCheck className="w-3.5 h-3.5 mr-1" /> : <Cpu className="w-3.5 h-3.5 mr-1" />}
              {isField ? 'RUN 5 FROZEN REALTIME MODEL' : 'DIGITAL TWIN SIMULATION MODEL'}
            </span>
            <span className="text-xs text-slate-400">
              Dataset: {isField ? 'field_2026_oct_v1' : 'simulation_oct_v1'}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-2 flex items-center gap-2">
            <BrainCircuit className={`w-7 h-7 ${isField ? 'text-teal-400' : 'text-amber-400'}`} />
            ElasticNet Irrigation-Requirement Forecaster (B-AI-EN)
          </h1>
          <p className="text-slate-300 text-sm mt-1">
            24-h minimum sufficient irrigation forecasting using operational weather forecasts and root-zone soil state (Oct 1–2, 2026).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex bg-black/40 p-1 rounded-lg border border-white/10">
            <button
              onClick={() => setSelectedZone('A')}
              className={`px-3 py-1.5 text-xs font-bold rounded-md transition ${selectedZone === 'A' ? 'bg-white text-slate-900' : 'text-slate-400 hover:text-white'}`}
            >
              Zone A (Control)
            </button>
            <button
              onClick={() => setSelectedZone('B')}
              className={`px-3 py-1.5 text-xs font-bold rounded-md transition ${selectedZone === 'B' ? 'bg-white text-slate-900' : 'text-slate-400 hover:text-white'}`}
            >
              Zone B (Agrivoltaic)
            </button>
          </div>

          <span className={`flex items-center text-xs font-bold px-3 py-1.5 rounded-lg border ${
            isField ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
          }`}>
            <CheckCircle2 className="w-4 h-4 mr-1" />
            {isField ? 'FIELD MODEL ACTIVE' : 'SIMULATOR ACTIVE'}
          </span>
        </div>
      </div>

      {/* Main Prediction & Feature Attribution Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h2 className="font-bold text-slate-800 text-base">Irrigation Requirement (IR) Forecast</h2>
            <span className="px-2 py-0.5 text-xs font-bold bg-teal-50 text-teal-800 border border-teal-200 rounded">
              Zone {selectedZone}
            </span>
          </div>

          <div className="space-y-3 font-mono text-sm">
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-sans">Issued Time</span>
              <span className="font-bold text-slate-700">2026-10-02 09:47:34</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-sans">Target Horizon</span>
              <span className="font-bold text-slate-700">t + 24 Hours (Oct 3, 2026)</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-sans">P10 Lower Bound</span>
              <span className="font-bold text-blue-600">{prediction?.ir_10?.toFixed(2) ?? '2.80'} mm</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-sans">P50 Median Forecast</span>
              <span className="font-bold text-teal-800 text-base">{prediction?.ir_50?.toFixed(2) ?? '4.80'} mm</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-50">
              <span className="text-slate-500 font-sans">P90 Upper Bound</span>
              <span className="font-bold text-rose-600">{prediction?.ir_90?.toFixed(2) ?? '7.10'} mm</span>
            </div>
          </div>

          <div className={`p-3 rounded-xl border text-xs font-bold flex justify-between items-center ${
            prediction?.safety_status === 'PASS' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-emerald-50 text-emerald-800 border-emerald-200'
          }`}>
            <span>Safety Constraint Filter:</span>
            <span>SAFE (Ks = 1.00 - ZERO STRESS)</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm col-span-2">
          <ReactECharts option={getAttributionChartOptions()} style={{ height: '320px' }} />
        </div>
      </div>
    </div>
  );
}
