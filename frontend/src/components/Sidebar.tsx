import { Link, useLocation } from 'react-router-dom';
import { 
  Home, 
  Radio, 
  GitCompare, 
  LineChart, 
  BrainCircuit, 
  Network, 
  Sprout, 
  Stethoscope, 
  Download,
  ClipboardList,
  Lock,
  Cpu
} from 'lucide-react';
import { useStore } from '../store/useStore';

const NAV_ITEMS = [
  { path: '/', label: 'Overview', icon: Home },
  { path: '/live', label: 'Live Monitoring', icon: Radio },
  { path: '/comparison', label: 'Zone Comparison', icon: GitCompare },
  { path: '/trends', label: 'Graphs & Trends', icon: LineChart },
  { path: '/predictions', label: 'ML & Predictions', icon: BrainCircuit },
  { path: '/shap', label: 'SHAP / XAI', icon: Network },
  { path: '/agronomy', label: 'Agronomic Intelligence', icon: Sprout },
  { path: '/diagnostics', label: 'Sensor Diagnostics', icon: Stethoscope },
  { path: '/experiment', label: 'Field Experiment', icon: ClipboardList },
  { path: '/export', label: 'Data & Export', icon: Download },
];

export default function Sidebar() {
  const location = useLocation();
  const { datasetMode } = useStore();

  const isField = datasetMode === 'FIELD';

  return (
    <div className="w-64 bg-slate-900 text-slate-300 flex flex-col h-full shadow-xl z-20 shrink-0">
      <div className="p-6 overflow-y-auto flex-1">
        <div className="flex items-center space-x-3 text-emerald-400 mb-8">
          <div className="p-2 bg-teal-500/20 border border-teal-500/30 rounded-xl">
            <Sprout className="w-6 h-6 text-teal-400" />
          </div>
          <div>
            <span className="text-xl font-black tracking-wider text-white block leading-none font-sans">AGRO-VOLT</span>
            <span className="text-[9px] text-teal-300/80 font-bold uppercase tracking-widest mt-1 block">Research Suite</span>
          </div>
        </div>

        <div className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors font-medium text-sm ${
                  isActive 
                    ? (isField ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30' : 'bg-amber-500/15 text-amber-300 border border-amber-500/30')
                    : 'hover:bg-slate-800 hover:text-slate-100'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? (isField ? 'text-teal-400' : 'text-amber-400') : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
      
      {/* Research Context Block */}
      <div className="p-5 border-t border-slate-800 bg-slate-950/60">
        <div className={`rounded-xl p-4 border transition-colors ${
          isField ? 'bg-slate-900/90 border-teal-500/30' : 'bg-slate-900/90 border-amber-500/30'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Research Context</p>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center ${
              isField ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
            }`}>
              {isField ? <Lock className="w-3 h-3 mr-1 text-teal-400" /> : <Cpu className="w-3 h-3 mr-1 text-amber-400" />}
              {isField ? 'field_2026_oct_v1' : 'simulation_v1'}
            </span>
          </div>

          <div className="space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-sans">Run ID</span>
              <span className="text-white font-bold bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                {isField ? 'RUN 5' : 'SIM-01'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-sans">Status</span>
              <span className={`font-bold flex items-center ${
                isField ? 'text-emerald-400' : 'text-amber-400'
              }`}>
                <span className="w-2 h-2 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span>
                COMPLETED (OCT 1–2)
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-sans">Date</span>
              <span className="text-slate-300 font-semibold font-sans text-[11px]">
                01 Oct – 02 Oct 2026
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
