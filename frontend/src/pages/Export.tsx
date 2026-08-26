import { useState } from 'react';
import { Download, Database, FileText, ShieldCheck, Cpu } from 'lucide-react';
import { useStore } from '../store/useStore';

export default function Export() {
  const { datasetMode } = useStore();
  const [selectedZone, setSelectedZone] = useState('B');
  const [dateRange, setDateRange] = useState('7d');

  const isField = datasetMode === 'FIELD';

  const handleExport = () => {
    const url = `http://localhost:8000/api/export/csv?zone=${selectedZone}&mode=${datasetMode}&start=-${dateRange}&end=now`;
    
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
              {isField ? 'FIELD ARCHIVE (field_2026_v1)' : 'SIMULATION ENGINE (simulation_v1)'}
            </span>
          </div>
          <p className="text-slate-500 text-xs mt-1">Download audited telemetry, ML predictions, and agronomic datasets for external research.</p>
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
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days (Full Field Campaign)</option>
              <option value="season">Entire Season</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="border border-slate-200 rounded-xl p-6 hover:border-teal-300 transition-colors bg-slate-50 group">
             <div className="flex items-center text-teal-700 mb-4">
                <Database className="w-8 h-8 mr-3" />
                <div>
                   <h3 className="font-bold text-slate-800">
                     {isField ? 'Audited Field Sensor Telemetry' : 'Simulated Digital Twin Output Data'}
                   </h3>
                   <p className="text-xs text-slate-500">Quality-flagged 5-min analytical observations</p>
                </div>
             </div>
             <button 
               onClick={handleExport}
               className={`w-full py-2 bg-white border font-bold rounded-lg transition-colors flex justify-center items-center text-xs ${
                 isField ? 'border-slate-300 text-slate-700 hover:bg-teal-700 hover:text-white' : 'border-slate-300 text-slate-700 hover:bg-amber-700 hover:text-white'
               }`}
             >
               <Download className="w-4 h-4 mr-2" /> Download CSV ({datasetMode} Mode)
             </button>
          </div>

          <div className="border border-slate-200 rounded-xl p-6 hover:border-indigo-300 transition-colors bg-slate-50 group">
             <div className="flex items-center text-indigo-600 mb-4">
                <FileText className="w-8 h-8 mr-3" />
                <div>
                   <h3 className="font-bold text-slate-800">Model Predictions & Attributes</h3>
                   <p className="text-xs text-slate-500">ElasticNet irrigation forecasts & error metrics</p>
                </div>
             </div>
             <button 
               onClick={handleExport}
               className="w-full py-2 bg-white border border-slate-300 text-slate-700 font-bold text-xs rounded-lg hover:bg-indigo-600 hover:text-white transition-colors flex justify-center items-center"
             >
               <Download className="w-4 h-4 mr-2" /> Download CSV ({datasetMode} Mode)
             </button>
          </div>
        </div>
        
      </div>
      
      <div className="text-center text-xs text-slate-500 font-medium mt-4">
        Active Export Source: <span className="font-bold text-slate-800">{isField ? 'SD_ARCHIVE (field_2026_v1)' : 'SIMULATION_ENGINE (simulation_v1)'}</span>
      </div>
    </div>
  );
}
