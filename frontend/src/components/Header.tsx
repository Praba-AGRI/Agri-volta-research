import { useState, useEffect } from 'react';
import { Activity, Clock, Database, Layers } from 'lucide-react';
import { useStore } from '../store/useStore';

export default function Header() {
  const { datasetMode, setDatasetMode } = useStore();
  const [timeString, setTimeString] = useState(new Date().toLocaleTimeString());

  const isField = datasetMode === 'FIELD';

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeString(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <>
      {/* Top Dynamic Mode Banner */}
      <div className={`px-6 py-2 flex items-center justify-between text-xs font-bold tracking-wider text-white transition-colors duration-300 ${
        isField ? 'bg-teal-700' : 'bg-amber-700'
      }`}>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-white animate-pulse"></span>
          <span>
            {isField
              ? 'AGRO-VOLT FIELD MODE — REAL-WORLD SENSOR TELEMETRY & LIVE STREAM'
              : 'AGRO-VOLT SIMULATION MODE — CLOSED-LOOP DIGITAL TWIN ENGINE'}
          </span>
        </div>

        {/* Mode Toggle Switch */}
        <div className="flex items-center bg-black/25 p-1 rounded-lg space-x-1">
          <button
            onClick={() => setDatasetMode('FIELD')}
            className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${
              isField
                ? 'bg-white text-teal-800 shadow'
                : 'text-teal-100 hover:bg-white/10'
            }`}
          >
            FIELD MODE
          </button>
          <button
            onClick={() => setDatasetMode('SIMULATION')}
            className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${
              !isField
                ? 'bg-white text-amber-900 shadow'
                : 'text-amber-100 hover:bg-white/10'
            }`}
          >
            SIMULATION MODE
          </button>
        </div>
      </div>

      {/* Main Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between shadow-sm z-10">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-xl transition-colors ${isField ? 'bg-teal-50 text-teal-700' : 'bg-amber-50 text-amber-700'}`}>
            <Activity className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-black text-slate-800 tracking-tight font-sans">AGRO-VOLT RESEARCH DASHBOARD</h1>
              <span className={`px-2 py-0.5 text-[10px] font-bold rounded-md uppercase border ${
                isField
                  ? 'bg-teal-50 text-teal-800 border-teal-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}>
                {datasetMode}
              </span>
            </div>
            <div className="flex items-center text-xs text-slate-500 mt-0.5 font-medium space-x-2">
              <span className="flex items-center text-emerald-600 font-semibold">
                <span className="w-2 h-2 rounded-full bg-emerald-500 mr-1.5 animate-pulse"></span>
                System Online
              </span>
              <span className="text-slate-300">|</span>
              <span className="flex items-center font-mono">
                <Clock className="w-3 h-3 mr-1 text-teal-600 animate-spin" />
                Last update: {timeString}
              </span>
              <span className="text-slate-300">|</span>
              <span>Dataset: {isField ? 'field_2026_v1' : 'simulation_v1'}</span>
            </div>
          </div>
        </div>

        {/* Global Data Provenance Card */}
        <div className="hidden lg:flex items-center bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-1.5 space-x-4 text-xs">
          <div className="flex items-center space-x-1.5 text-slate-600">
            <Database className="w-3.5 h-3.5 text-teal-600" />
            <div>
              <div className="text-[10px] text-slate-400 font-semibold uppercase">Source</div>
              <div className="font-bold text-slate-700">{isField ? 'SD_ARCHIVE / LIVE' : 'SIM_ENGINE'}</div>
            </div>
          </div>

          <div className="h-6 w-px bg-slate-200"></div>

          <div className="flex items-center space-x-1.5 text-slate-600">
            <Layers className="w-3.5 h-3.5 text-blue-600" />
            <div>
              <div className="text-[10px] text-slate-400 font-semibold uppercase">Resolution</div>
              <div className="font-bold text-slate-700">5 min analytical</div>
            </div>
          </div>
        </div>
      </header>
    </>
  );
}
