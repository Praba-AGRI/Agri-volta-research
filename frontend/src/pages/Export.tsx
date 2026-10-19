import { useState } from 'react';
import { Download, Database, FileText, ShieldCheck, Cpu } from 'lucide-react';
import { useStore } from '../store/useStore';
import { getApiUrl } from '../services/api';

export default function Export() {
  const { datasetMode } = useStore();
  const [selectedZone, setSelectedZone] = useState('B');
  const [dateRange, setDateRange] = useState('2d');

  const isField = datasetMode === 'FIELD';

  const handleExport = () => {
    const url = getApiUrl(`/api/export/csv?zone=${selectedZone}&mode=${datasetMode}&start=-${dateRange}&end=now`);
    
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto mt-4">
      {/* Header Banner */}
      <div className={`p-6 rounded-2xl border shadow-md flex justify-between items-center ${
        isField ? 'bg-white border-slate-200' : 'bg-amber-50/50 border-amber-200'
      }`}>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-slate-800">Research Data Export</h1>
            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full border flex items-center ${
              isField ? 'bg-teal-100 text-teal-800 border-teal-200' : 'bg-amber-100 text-amber-900 border-amber-200'
            }`}>
              {isField ? <ShieldCheck className="w-3.5 h-3.5 mr-1 text-teal-600" /> : <Cpu className="w-3.5 h-3.5 mr-1 text-amber-600" />}
              {isField ? 'FIELD ARCHIVE (field_2026_oct_v1)' : 'SIMULATION ENGINE (simulation_oct_v1)'}
            </span>
          </div>
          <p className="text-slate-500 text-xs mt-1">Download audited telemetry for 2-day real-time validation campaign (Oct 1–2, 2026).</p>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-6 border-b border-slate-100">
          <div>
            <label className="block text-xs font-bold uppercase text-slate-500 mb-2">Zone</label>
            <select 
              className="w-full border-slate-300 rounded-lg shadow-sm focus:border-teal-500 focus:ring-teal-500 text-sm font-medium"
              value={selectedZone}
              onChange={e => setSelectedZone(e.target.value)}
            >
              <option value="A">Zone A (Control / Full Sun)</option>
              <option value="B">Zone B (Agrivoltaic Canopy)</option>
              <option value="BOTH">Both Zones (Combined)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold uppercase text-slate-500 mb-2">Time Horizon</label>
            <select 
              className="w-full border-slate-300 rounded-lg shadow-sm focus:border-teal-500 focus:ring-teal-500 text-sm font-medium"
              value={dateRange}
              onChange={e => setDateRange(e.target.value)}
            >
              <option value="2d">2 Days (Oct 1–2, 2026 Real-Time Campaign)</option>
              <option value="24h">Last 24 Hours</option>
              <option value="30d">Full Research Archive</option>
            </select>
          </div>
        </div>

        {/* Dataset Information Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 flex items-start space-x-3">
            <Database className="w-5 h-5 text-teal-700 mt-0.5" />
            <div>
              <div className="text-xs font-bold text-slate-700">Source Dataset Provenance</div>
              <div className="text-sm font-bold text-slate-900 mt-0.5">
                {isField ? 'SD_ARCHIVE / LIVE (field_2026_oct_v1)' : 'SIMULATION_ENGINE (simulation_oct_v1)'}
              </div>
              <p className="text-[11px] text-slate-500 mt-1">5-minute analytical resampled time-series with quality control flags.</p>
            </div>
          </div>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 flex items-start space-x-3">
            <FileText className="w-5 h-5 text-blue-700 mt-0.5" />
            <div>
              <div className="text-xs font-bold text-slate-700">Campaign Window</div>
              <div className="text-sm font-bold text-slate-900 mt-0.5">01 Oct 2026 → 02 Oct 2026</div>
              <p className="text-[11px] text-slate-500 mt-1">2-day real-time validation campaign (576 analytical records per zone).</p>
            </div>
          </div>
        </div>

        {/* Export Button */}
        <div className="pt-2 flex justify-end">
          <button 
            onClick={handleExport}
            className={`flex items-center space-x-2 px-6 py-2.5 rounded-lg text-sm font-bold text-white shadow-md transition ${
              isField ? 'bg-teal-700 hover:bg-teal-800' : 'bg-amber-700 hover:bg-amber-800'
            }`}
          >
            <Download className="w-4 h-4" />
            <span>Download {isField ? 'field_2026_oct_v1' : 'simulation_oct_v1'} CSV</span>
          </button>
        </div>

      </div>
    </div>
  );
}
