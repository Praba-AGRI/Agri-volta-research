import { useState, useEffect } from 'react';
import { api } from '../services/api';
import ReactECharts from 'echarts-for-react';
import { Network, ShieldCheck, CheckCircle2, Cpu } from 'lucide-react';
import { useStore } from '../store/useStore';

export default function Shap() {
  const { datasetMode } = useStore();
  const [globalShap, setGlobalShap] = useState<Record<string, number>>({});
  const [localShap, setLocalShap] = useState<{feature: string, contribution: number}[]>([]);
  const [temporalShap, setTemporalShap] = useState<{features: string[], timestamps: string[], matrix: number[][]}|null>(null);
  const [loading, setLoading] = useState(true);

  const isField = datasetMode === 'FIELD';

  useEffect(() => {
    const fetchShapData = async () => {
      setLoading(true);
      try {
        const predictionId = "latest";
        const [globalRes, localRes, temporalRes] = await Promise.all([
          api.get('/api/shap/global', { params: { mode: datasetMode } }),
          api.get(`/api/shap/local/${predictionId}`, { params: { mode: datasetMode } }),
          api.get(`/api/shap/temporal/${predictionId}`, { params: { mode: datasetMode } })
        ]);
        
        setGlobalShap(globalRes.data);
        setLocalShap(localRes.data);
        setTemporalShap(temporalRes.data);
      } catch (err) {
        console.error("Failed to fetch SHAP data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchShapData();
  }, [datasetMode]);

  const getGlobalChartOptions = () => {
    const entries = Object.entries(globalShap).sort((a, b) => a[1] - b[1]);
    return {
      title: {
        text: isField
          ? 'Standardized ElasticNet Coefficients (Field Model)'
          : 'Digital Twin Simulated Feature Weight Coefficients',
        left: 'center',
        textStyle: { fontSize: 13, fontWeight: 'bold', color: '#334155' }
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { top: 35, right: 30, bottom: 20, left: 180 },
      xAxis: { type: 'value', name: 'Standardized Coefficient Weight', nameLocation: 'middle', nameGap: 25, axisLabel: { color: '#64748b' } },
      yAxis: { type: 'category', data: entries.map(e => e[0]), axisLabel: { color: '#334155', fontWeight: 'bold', fontSize: 10 } },
      series: [{
        type: 'bar',
        data: entries.map(e => e[1]),
        itemStyle: {
          color: (params: any) => (params.value >= 0 ? (isField ? '#0f766e' : '#d97706') : '#e11d48')
        }
      }]
    };
  };

  const getLocalChartOptions = () => {
    let current = 0;
    const data = localShap.map(item => {
      const prev = current;
      current += item.contribution;
      return {
        name: item.feature,
        value: item.contribution,
        start: prev,
        end: current
      };
    });

    const transparentData = data.map(d => d.value > 0 ? d.start : d.end);
    const positiveData = data.map(d => d.value > 0 ? d.value : '-');
    const negativeData = data.map(d => d.value < 0 ? Math.abs(d.value) : '-');

    return {
      title: {
        text: isField ? 'Field Feature Decision Impact (Waterfall)' : 'Digital Twin Simulated Waterfall Decomposition',
        left: 'center',
        textStyle: { fontSize: 13, fontWeight: 'bold', color: '#334155' }
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: function (params: any) {
         const pos = params[1];
         const neg = params[2];
         const val = pos.value !== '-' ? pos.value : -neg.value;
         return `<b>${pos.name}</b><br/>Contribution Weight: ${val.toFixed(4)}`;
      }},
      grid: { top: 35, right: 30, bottom: 20, left: 160 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: data.map(d => d.name) },
      series: [
        { type: 'bar', stack: 'total', itemStyle: { borderColor: 'transparent', color: 'transparent' }, data: transparentData },
        { type: 'bar', stack: 'total', name: 'Positive Impact', itemStyle: { color: isField ? '#0f766e' : '#d97706' }, data: positiveData },
        { type: 'bar', stack: 'total', name: 'Negative Impact', itemStyle: { color: '#e11d48' }, data: negativeData }
      ]
    };
  };

  const getTemporalChartOptions = () => {
    if (!temporalShap) return {};
    const data: any[] = [];
    temporalShap.matrix.forEach((row, yIndex) => {
      row.forEach((value, xIndex) => {
        data.push([xIndex, yIndex, value]);
      });
    });

    return {
      title: {
        text: isField ? 'Temporal Feature Importance Matrix (Field)' : 'Simulated Temporal Weight Matrix (Digital Twin)',
        left: 'center',
        textStyle: { fontSize: 13, fontWeight: 'bold', color: '#334155' }
      },
      tooltip: { position: 'top' },
      grid: { top: 35, right: 20, bottom: 40, left: 80 },
      xAxis: { type: 'category', data: temporalShap.timestamps, splitArea: { show: true } },
      yAxis: { type: 'category', data: temporalShap.features, splitArea: { show: true } },
      visualMap: {
        min: 0,
        max: 1,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '0%',
        inRange: { color: isField ? ['#f0fdf4', '#0d9488', '#042f2e'] : ['#fffbe6', '#d97706', '#78350f'] }
      },
      series: [{
        name: 'Temporal Weight',
        type: 'heatmap',
        data: data,
        label: { show: true, fontSize: 10 },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
      }]
    };
  };

  if (loading) {
    return <div className="p-6 text-slate-400 font-medium">Loading SHAP & XAI model explainability data...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Network className={`w-5 h-5 ${isField ? 'text-teal-700' : 'text-amber-700'}`} />
            <h1 className="text-xl font-bold text-slate-800">
              {isField ? 'Explainable AI (SHAP) & Standardized Regression Coefficients' : 'Digital Twin Explainable AI (SHAP) & Simulated Feature Weights'}
            </h1>
            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full border flex items-center ${
              isField ? 'bg-teal-100 text-teal-800 border-teal-200' : 'bg-amber-100 text-amber-800 border-amber-200'
            }`}>
              {isField ? <ShieldCheck className="w-3.5 h-3.5 mr-1" /> : <Cpu className="w-3.5 h-3.5 mr-1" />}
              {isField ? 'field_2026_v1 FROZEN' : 'simulation_v1 ENGINE'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {isField
              ? 'Standardized ElasticNet coefficients and feature importance breakdown for finalized field experiment campaign.'
              : 'Physics engine feature importance coefficients and simulated model attribution breakdown.'}
          </p>
        </div>

        <div className={`flex items-center border px-3 py-1.5 rounded-lg text-xs font-bold space-x-1.5 ${
          isField ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-amber-50 text-amber-800 border-amber-200'
        }`}>
          <CheckCircle2 className={`w-4 h-4 ${isField ? 'text-emerald-600' : 'text-amber-600'}`} />
          <span>{isField ? 'EXPERIMENT COMPLETED — MODEL FROZEN' : 'SIMULATION ENGINE ACTIVE'}</span>
        </div>
      </div>

      {/* Grid of Explainability Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <ReactECharts option={getGlobalChartOptions()} style={{ height: '360px' }} />
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <ReactECharts option={getLocalChartOptions()} style={{ height: '360px' }} />
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <ReactECharts option={getTemporalChartOptions()} style={{ height: '320px' }} />
      </div>
    </div>
  );
}
