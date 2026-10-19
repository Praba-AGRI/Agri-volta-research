import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Calendar, Radio } from 'lucide-react';

interface ExperimentConfig {
  experiment_id: string;
  experiment_name: string;
  crop: string;
  start_date: string;
  end_date: string | null;
  active: boolean;
  status: string;
}

export default function ExperimentTimeline() {
  const [config, setConfig] = useState<ExperimentConfig | null>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await api.get('/api/experiment/active');
        setConfig(res.data);
      } catch (err) {
        console.error('Failed to fetch experiment config', err);
      }
    };
    fetchConfig();
  }, []);

  if (!config) return null;

  return (
    <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between text-sm shadow-sm z-10 relative">
      <div className="flex items-center space-x-6">
        <div className="flex items-center">
          <Calendar className="w-4 h-4 text-teal-700 mr-2" />
          <span className="font-semibold text-slate-700 mr-2">{config.experiment_name}</span>
          <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-xs border border-slate-200 font-mono">
            {config.experiment_id}
          </span>
        </div>
        
        <div className="flex items-center text-slate-600">
          <span className="text-xs uppercase font-bold tracking-wider text-slate-400 mr-2">Crop:</span>
          <span className="font-medium italic text-slate-800">{config.crop}</span>
        </div>
        
        <div className="flex items-center">
           <span className="text-xs uppercase font-bold tracking-wider text-slate-400 mr-2">Status:</span>
           <span className="flex items-center text-emerald-700 font-bold bg-emerald-50 px-2.5 py-0.5 rounded text-xs border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 mr-1.5"></span>
              {config.status || 'COMPLETED (OCT 1–2, 2026)'}
           </span>
        </div>
      </div>
      
      <div className="flex items-center">
        <div className="flex flex-col items-end">
          <span className="text-xs uppercase font-bold tracking-wider text-slate-400 mb-0.5 flex items-center">
            <Radio className="w-3 h-3 mr-1 text-teal-600" />
            Completed Field Experiment Telemetry
          </span>
          <div className="flex items-center font-mono text-xs">
            <span className="text-slate-600 font-semibold">Campaign: 01/10/2026 – 02/10/2026</span>
            <span className="ml-2 font-bold text-teal-700 bg-teal-50 px-1.5 py-0.5 rounded border border-teal-200 flex items-center">
              01 Oct – 02 Oct 2026
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
