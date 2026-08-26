import { useState, useEffect } from 'react';
import axios from 'axios';
import { MapPin, Calendar, Clock, Settings, Save, CheckCircle2, Lock, ShieldCheck } from 'lucide-react';
import { Sprout as Plant } from 'lucide-react';

interface ExperimentConfig {
  experiment_id: string;
  experiment_name: string;
  crop: string;
  start_date: string;
  end_date: string;
  sampling_interval: number;
  status: string;
  active: boolean;
}

export default function FieldExperiment() {
  const [config, setConfig] = useState<ExperimentConfig>({
    experiment_id: 'AGV-001',
    experiment_name: 'Agrivoltaic Microclimate Study',
    crop: 'Cowpea (Vigna unguiculata)',
    start_date: '2026-07-22',
    end_date: '2026-08-22',
    sampling_interval: 120,
    status: 'FINISHED',
    active: false
  });

  const [crop, setCrop] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [interval, setIntervalVal] = useState(120);
  
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/experiment/active');
        setConfig(res.data);
        setCrop(res.data.crop);
        setStartDate(res.data.start_date);
        setEndDate(res.data.end_date || '2026-08-22');
        setIntervalVal(res.data.sampling_interval);
      } catch (err) {
        console.error('Failed to fetch experiment config', err);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(false);
    try {
      const res = await axios.post('http://localhost:8000/api/experiment/active', {
        crop: crop,
        start_date: startDate,
        end_date: endDate,
        sampling_interval: Number(interval)
      });
      setConfig(res.data);
      setSaved(true);
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (err) {
      console.error('Failed to save experiment config', err);
    }
  };

  if (loading) {
    return <div className="text-slate-500 text-center py-12 font-medium">Loading experiment configuration...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-slate-200 p-5 rounded-xl shadow-sm">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-slate-800">Field Experiment Management</h1>
            <span className="px-2.5 py-0.5 text-xs font-bold bg-emerald-100 text-emerald-800 rounded-full border border-emerald-300 flex items-center">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
              STATUS: FINISHED
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Research metadata, configuration, and finalized campaign boundaries for experiment {config.experiment_id}.
          </p>
        </div>

        <div className="flex items-center bg-teal-50 border border-teal-200 px-3.5 py-2 rounded-xl text-xs space-x-3">
          <ShieldCheck className="w-5 h-5 text-teal-700" />
          <div>
            <div className="text-[10px] text-teal-600 uppercase font-bold">Research Dataset</div>
            <div className="font-bold text-teal-900">field_2026_v1 (LOCKED)</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Core Metadata Form */}
        <form onSubmit={handleSave} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 lg:col-span-2 space-y-6">
          <div className="flex justify-between items-center border-b border-slate-100 pb-4">
            <h2 className="text-base font-bold text-slate-800 flex items-center">
              <Settings className="w-4 h-4 mr-2 text-slate-500" />
              Experiment Settings & Parameters
            </h2>
            {saved && (
              <span className="flex items-center text-xs font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-md">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> CONFIGURATION SAVED
              </span>
            )}
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs text-slate-500 uppercase font-bold mb-2">Experiment ID</label>
              <input
                type="text"
                disabled
                value={config.experiment_id}
                className="w-full bg-slate-100 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 font-mono font-bold cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-xs text-slate-500 uppercase font-bold mb-2">Location</label>
              <div className="flex items-center bg-slate-100 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700">
                <MapPin className="w-4 h-4 mr-2 text-slate-400" />
                <span>Research Farm, Block B</span>
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-500 uppercase font-bold mb-2">Start Date</label>
              <div className="flex items-center border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 font-medium">
                <Calendar className="w-4 h-4 mr-2 text-slate-400" />
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full outline-none bg-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-500 uppercase font-bold mb-2">End Date (Finished)</label>
              <div className="flex items-center border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 font-medium">
                <Calendar className="w-4 h-4 mr-2 text-slate-400" />
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full outline-none bg-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-500 uppercase font-bold mb-2">Target Crop (Species Name)</label>
              <div className="flex items-center border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 font-medium">
                <Plant className="w-4 h-4 mr-2 text-emerald-600" />
                <input
                  type="text"
                  value={crop}
                  onChange={(e) => setCrop(e.target.value)}
                  className="w-full outline-none bg-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-500 uppercase font-bold mb-2">Native Sampling Interval</label>
              <div className="flex items-center border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 font-medium">
                <Clock className="w-4 h-4 mr-2 text-slate-400" />
                <select
                  value={interval}
                  onChange={(e) => setIntervalVal(Number(e.target.value))}
                  className="w-full outline-none bg-transparent"
                >
                  <option value={120}>2 Minutes (Native Telemetry)</option>
                  <option value={300}>5 Minutes (Analytical Resampling)</option>
                </select>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex justify-between items-center">
            <div className="text-xs text-slate-500">
              Current Campaign State: <span className="font-bold text-emerald-700">FINISHED (Day 32 / 32)</span>
            </div>
            <button
              type="submit"
              className="flex items-center space-x-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-xs shadow transition"
            >
              <Save className="w-4 h-4" />
              <span>Save Configuration</span>
            </button>
          </div>
        </form>

        {/* Active Profile Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <h2 className="text-base font-bold text-slate-800 flex items-center">
                <Plant className="w-4 h-4 mr-2 text-emerald-600" />
                Completed Active Profile
              </h2>
              <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-100 text-emerald-800 rounded">
                COMPLETED
              </span>
            </div>

            <div className="space-y-4 mt-4">
              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">Target Crop</div>
                <div className="font-bold text-slate-800 text-sm mt-0.5">{config.crop}</div>
              </div>

              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">Campaign Duration</div>
                <div className="font-bold text-slate-800 text-sm mt-0.5">32 Days (22 July 2026 – 22 August 2026)</div>
              </div>

              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">Native vs Analytical Interval</div>
                <div className="font-bold text-slate-800 text-sm mt-0.5">2 min native $\rightarrow$ 5 min analytical</div>
              </div>

              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">Effective Root Depth</div>
                <div className="font-bold text-slate-800 text-sm mt-0.5">20 cm (Rooting Zone)</div>
              </div>

              <div>
                <div className="text-[10px] text-slate-400 font-bold uppercase">Total Analytical Records</div>
                <div className="font-bold text-teal-800 text-sm mt-0.5">18,432 Observations (100.0% QC)</div>
              </div>
            </div>
          </div>

          <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl text-xs text-teal-900 flex items-center space-x-2">
            <Lock className="w-4 h-4 text-teal-700 shrink-0" />
            <span>Field experiment is concluded and locked for research manuscript publication.</span>
          </div>
        </div>

      </div>
    </div>
  );
}
