import { useState, useEffect } from 'react';
import axios from 'axios';
import { useStore } from '../store/useStore';
import { Sprout, Sun, Droplets, ShieldCheck, CheckCircle2, Lock, Cpu } from 'lucide-react';

interface GDDData {
  daily_gdd: number;
  cumulative_gdd: number;
  phenology_stage: string;
  campaign_status: string;
}

interface ETCData {
  et0: number;
  kc: number;
  etc: number;
  cumulative_etc_mm: number;
  water_saved_mm: number;
}

interface KsData {
  ks: number;
  stress_status: string;
}

export default function Agronomy() {
  const { datasetMode } = useStore();
  const [selectedZone, setSelectedZone] = useState('B');
  
  const [gdd, setGdd] = useState<GDDData | null>(null);
  const [etc, setEtc] = useState<ETCData | null>(null);
  const [ks, setKs] = useState<KsData | null>(null);
  const [loading, setLoading] = useState(true);

  const isField = datasetMode === 'FIELD';

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const params = { zone: selectedZone, mode: datasetMode };
        const [gddRes, etcRes, ksRes] = await Promise.all([
          axios.get('http://localhost:8000/api/agronomy/gdd', { params }),
          axios.get('http://localhost:8000/api/agronomy/etc', { params }),
          axios.get('http://localhost:8000/api/agronomy/ks', { params })
        ]);
        
        setGdd(gddRes.data);
        setEtc(etcRes.data);
        setKs(ksRes.data);
      } catch (err) {
        console.error("Failed to fetch agronomy data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedZone, datasetMode]);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Sprout className={`w-5 h-5 ${isField ? 'text-teal-700' : 'text-amber-700'}`} />
            <h1 className="text-xl font-bold text-slate-800">
              {isField ? 'Agronomic Intelligence & Seasonal Crop Performance' : 'Digital Twin Simulated Crop Performance Engine'}
            </h1>
            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full border flex items-center ${
              isField ? 'bg-teal-100 text-teal-800 border-teal-200' : 'bg-amber-100 text-amber-800 border-amber-200'
            }`}>
              {isField ? <ShieldCheck className="w-3.5 h-3.5 mr-1" /> : <Cpu className="w-3.5 h-3.5 mr-1" />}
              {isField ? 'field_2026_v1' : 'simulation_v1'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {isField
              ? 'Authoritative FAO-56 Penman-Monteith ET model and thermal phenology indices for Cowpea (Vigna unguiculata).'
              : 'Physics digital twin ET calculations and simulated thermal time accumulation for Cowpea.'}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex bg-slate-100 p-1 rounded-lg border border-slate-200">
            <button 
              onClick={() => setSelectedZone('A')}
              className={`px-3 py-1.5 text-xs font-bold rounded-md transition ${selectedZone === 'A' ? 'bg-white text-slate-800 shadow' : 'text-slate-500 hover:text-slate-900'}`}
            >
              Zone A (Control)
            </button>
            <button 
              onClick={() => setSelectedZone('B')}
              className={`px-3 py-1.5 text-xs font-bold rounded-md transition ${selectedZone === 'B' ? 'bg-white text-teal-800 shadow' : 'text-slate-500 hover:text-slate-900'}`}
            >
              Zone B (Agrivoltaic)
            </button>
          </div>

          <span className={`flex items-center text-xs font-bold px-3 py-1.5 rounded-lg border ${
            isField ? 'bg-emerald-100 text-emerald-800 border-emerald-200' : 'bg-amber-100 text-amber-900 border-amber-200'
          }`}>
            <CheckCircle2 className={`w-4 h-4 mr-1 ${isField ? 'text-emerald-600' : 'text-amber-600'}`} />
            {isField ? 'CAMPAIGN FINISHED' : 'SIMULATION ACTIVE'}
          </span>
        </div>
      </div>

      {loading ? (
        <div className="h-64 flex justify-center items-center text-slate-500 text-sm font-medium">Loading agronomic data...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          
          {/* Phenology & GDD */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className={`flex items-center mb-4 ${isField ? 'text-teal-700' : 'text-amber-700'}`}>
              <Sprout className="w-5 h-5 mr-2" />
              <h2 className="text-base font-bold text-slate-800">Thermal Time & Phenology</h2>
            </div>

            <div className="space-y-4">
              <div className={`p-4 rounded-xl border ${isField ? 'bg-teal-50 border-teal-200' : 'bg-amber-50 border-amber-200'}`}>
                <div className={`text-xs font-bold uppercase tracking-wider ${isField ? 'text-teal-700' : 'text-amber-800'}`}>
                  Phenological Stage
                </div>
                <div className={`text-xl font-extrabold mt-1 ${isField ? 'text-teal-900' : 'text-amber-950'}`}>
                  {gdd?.phenology_stage}
                </div>
              </div>
              
              <div className="flex justify-between items-center py-2 border-b border-slate-100 text-xs">
                <span className="text-slate-600 font-medium">Cumulative GDD</span>
                <span className="font-bold text-slate-800">{gdd?.cumulative_gdd} °C-days</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-100 text-xs">
                <span className="text-slate-600 font-medium">Data Source</span>
                <span className="font-bold text-slate-800">{isField ? '22 July – 22 August (Field)' : 'Simulation Engine Model'}</span>
              </div>
            </div>

            <div className="text-[10px] text-slate-400 mt-4 pt-2 border-t border-slate-100 flex items-center">
              <Lock className="w-3 h-3 mr-1 text-teal-600" />
              <span>Base temperature T_base = 10°C for Cowpea</span>
            </div>
          </div>

          {/* FAO-56 Evapotranspiration */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center text-blue-600 mb-4">
              <Sun className="w-5 h-5 mr-2" />
              <h2 className="text-base font-bold text-slate-800">FAO-56 Evapotranspiration</h2>
            </div>

            <div className="space-y-4">
              <div className="bg-blue-50 p-4 rounded-xl border border-blue-200">
                <div className="text-xs text-blue-700 font-bold uppercase tracking-wider">Cumulative Evapotranspiration (ETc)</div>
                <div className="text-xl font-extrabold text-blue-900 mt-1">{etc?.cumulative_etc_mm} mm</div>
              </div>
              
              <div className="flex justify-between items-center py-2 border-b border-slate-100 text-xs">
                <span className="text-slate-600 font-medium">Reference ET0</span>
                <span className="font-bold text-slate-800">{etc?.et0} mm</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-100 text-xs">
                <span className="text-slate-600 font-medium">Water Saved in Zone B</span>
                <span className="font-bold text-emerald-700">{etc?.water_saved_mm} mm</span>
              </div>
            </div>

            <div className="text-[10px] text-slate-400 mt-4 pt-2 border-t border-slate-100 flex items-center">
              <Lock className="w-3 h-3 mr-1 text-blue-600" />
              <span>Calculated using full hourly FAO-56 Penman-Monteith equation</span>
            </div>
          </div>

          {/* Soil Moisture & Water Stress Index Ks */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center text-emerald-600 mb-4">
              <Droplets className="w-5 h-5 mr-2" />
              <h2 className="text-base font-bold text-slate-800">Crop Water Stress (Ks)</h2>
            </div>

            <div className="space-y-4">
              <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200">
                <div className="text-xs text-emerald-700 font-bold uppercase tracking-wider">Stress Coefficient (Ks)</div>
                <div className="text-xl font-extrabold text-emerald-900 mt-1">{ks?.ks.toFixed(2)}</div>
              </div>
              
              <div className="flex justify-between items-center py-2 border-b border-slate-100 text-xs">
                <span className="text-slate-600 font-medium">Stress Status</span>
                <span className="font-bold text-emerald-700">{ks?.stress_status}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-100 text-xs">
                <span className="text-slate-600 font-medium">Critical Soil Threshold (θ_crit)</span>
                <span className="font-bold text-slate-800">0.2025 m³/m³</span>
              </div>
            </div>

            <div className="text-[10px] text-slate-400 mt-4 pt-2 border-t border-slate-100 flex items-center">
              <Lock className="w-3 h-3 mr-1 text-emerald-600" />
              <span>{isField ? 'Zero stress hours accumulated in field' : 'Simulated soil water flux'}</span>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
