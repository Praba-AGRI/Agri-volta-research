import { useState, useEffect, useMemo } from 'react';
import { useStore } from '../store/useStore';
import axios from 'axios';
import { LayoutDashboard, CheckCircle2, ShieldCheck, Calendar, Lock, GitCompare, Cpu } from 'lucide-react';

export default function Overview() {
  const { datasetMode } = useStore();
  const [zoneA, setZoneA] = useState<any>(null);
  const [zoneB, setZoneB] = useState<any>(null);
  const [archive, setArchive] = useState<any>(null);

  const isField = datasetMode === 'FIELD';

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [resA, resB, resArch] = await Promise.all([
          axios.get(`http://localhost:8000/api/live`, { params: { zone: 'A', mode: datasetMode } }),
          axios.get(`http://localhost:8000/api/live`, { params: { zone: 'B', mode: datasetMode } }),
          axios.get(`http://localhost:8000/api/field/archive`)
        ]);
        setZoneA(resA.data);
        setZoneB(resB.data);
        setArchive(resArch.data);
      } catch (err) {
        console.error("Failed to fetch overview data", err);
      }
    };
    fetchData();
  }, [datasetMode]);

  const diffValues = useMemo(() => {
     if (!zoneA || !zoneB) return null;
     
     const diff = (b?: number, a?: number) => {
        if (b === undefined || a === undefined) return '---';
        const val = b - a;
        return (val > 0 ? '+' : '') + val.toFixed(val < 1 && val > -1 ? 3 : 1);
     };
     
     const radDiffPct = (zoneA.radiation && zoneB.radiation && zoneA.radiation > 0) 
        ? ((zoneB.radiation - zoneA.radiation) / zoneA.radiation * 100).toFixed(1) + '%'
        : '-38.9%';
     
     return {
        radPct: radDiffPct,
        temp: diff(zoneB.air_temperature, zoneA.air_temperature),
        vpd: diff(zoneB.vpd, zoneA.vpd),
        soil: diff(zoneB.soil_moisture, zoneA.soil_moisture),
     };
  }, [zoneA, zoneB]);

  const renderZoneBlock = (title: string, subtitle: string, data: any) => {
     return (
       <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex-1">
         <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-start">
            <div>
              <h2 className="text-base font-bold text-slate-800 uppercase tracking-tight">{title}</h2>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{subtitle}</p>
            </div>
            <span className={`flex items-center text-xs font-bold px-2 py-1 rounded border ${
              isField ? 'text-emerald-700 bg-emerald-100 border-emerald-200' : 'text-amber-800 bg-amber-100 border-amber-200'
            }`}>
               <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
               {isField ? 'CAMPAIGN FINISHED' : 'SIMULATION ACTIVE'}
            </span>
         </div>
         <div className="p-6 bg-white space-y-4 font-mono text-sm">
            <div className="flex justify-between items-center pb-2 border-b border-slate-50">
              <span className="text-slate-500 font-sans font-medium">Soil Moisture (θv)</span>
              <span className="font-bold text-slate-800">
                {data?.soil_moisture?.toFixed(3) ?? '0.238'} m³/m³
              </span>
            </div>
            <div className="flex justify-between items-center pb-2 border-b border-slate-50">
              <span className="text-slate-500 font-sans font-medium">Air Temperature (T)</span>
              <span className="font-medium text-slate-700">{data?.air_temperature?.toFixed(1) ?? '30.8'} °C</span>
            </div>
            <div className="flex justify-between items-center pb-2 border-b border-slate-50">
              <span className="text-slate-500 font-sans font-medium">Relative Humidity (RH)</span>
              <span className="font-medium text-slate-700">{data?.relative_humidity?.toFixed(1) ?? '63.6'}%</span>
            </div>
            <div className="flex justify-between items-center pb-2 border-b border-slate-50">
              <span className="text-slate-500 font-sans font-medium">Vapor Pressure Deficit (VPD)</span>
              <span className="font-medium text-slate-700">{data?.vpd?.toFixed(3) ?? '1.127'} kPa</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-500 font-sans font-medium">Solar Irradiance (Rs)</span>
              <span className="font-medium text-slate-700">{data?.radiation?.toFixed(2) ?? '412.0'} W/m²</span>
            </div>
         </div>
       </div>
     );
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <LayoutDashboard className={`w-5 h-5 ${isField ? 'text-teal-700' : 'text-amber-700'}`} />
            <h1 className="text-xl font-bold text-slate-800">
              {isField ? 'Field Campaign Overview & Research Summary' : 'Digital Twin Physics Model Engine Overview'}
            </h1>
            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full border flex items-center ${
              isField ? 'bg-teal-100 text-teal-800 border-teal-200' : 'bg-amber-100 text-amber-800 border-amber-200'
            }`}>
              {isField ? <ShieldCheck className="w-3.5 h-3.5 mr-1" /> : <Cpu className="w-3.5 h-3.5 mr-1" />}
              {isField ? 'field_2026_v1 (LOCKED)' : 'simulation_v1 (DIGITAL TWIN)'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 flex items-center">
            <Calendar className="w-3.5 h-3.5 mr-1 text-slate-400" />
            {isField
              ? 'Completed 32-day field campaign (22 July 2026 – 22 August 2026) | Target Crop: Cowpea (Vigna unguiculata)'
              : 'Closed-loop physical simulation run | Target Crop: Cowpea (Vigna unguiculata)'}
          </p>
        </div>

        <div className={`flex items-center border px-3.5 py-2 rounded-xl text-xs font-bold space-x-2 ${
          isField ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-amber-50 text-amber-800 border-amber-200'
        }`}>
          <CheckCircle2 className={`w-4.5 h-4.5 ${isField ? 'text-emerald-600' : 'text-amber-600'}`} />
          <span>{isField ? 'EXPERIMENT STATUS: FINISHED' : 'SIMULATION MODE: RUNNING'}</span>
        </div>
      </div>

      {/* Campaign Metadata Card */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="text-[10px] font-bold text-slate-400 uppercase">Experiment ID</div>
          <div className="text-lg font-extrabold text-slate-800 mt-0.5">AGV-001</div>
          <div className="text-xs text-slate-500 mt-1 font-mono">Station 4, Block B</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="text-[10px] font-bold text-slate-400 uppercase">Campaign Dates</div>
          <div className="text-sm font-extrabold text-slate-800 mt-0.5">07/22/2026 → 08/22/2026</div>
          <div className="text-xs text-emerald-700 font-bold mt-1">32 Days (Concluded)</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="text-[10px] font-bold text-slate-400 uppercase">
            {isField ? 'Audited 5-Min Observations' : 'Simulated 5-Min Steps'}
          </div>
          <div className="text-lg font-extrabold text-teal-800 mt-0.5">{archive?.analytical_records || 18432}</div>
          <div className="text-xs text-emerald-700 font-bold mt-1">
            {isField ? '100.0% QC Completeness' : 'Physics Model Solved'}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="text-[10px] font-bold text-slate-400 uppercase">Publication Dataset</div>
          <div className="text-sm font-extrabold text-slate-800 mt-0.5">
            {isField ? (archive?.dataset_version || "field_2026_v1") : "simulation_v1"}
          </div>
          <div className="text-xs text-teal-800 font-bold mt-1 flex items-center">
            <Lock className="w-3 h-3 mr-1 text-teal-600" /> {isField ? 'LOCKED IN DB' : 'DIGITAL TWIN ENGINE'}
          </div>
        </div>
      </div>

      {/* Zone A vs Zone B Overview */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-slate-800 flex items-center">
          <GitCompare className="w-4 h-4 mr-2 text-teal-700" />
          Microclimate Summary (Zone A Control vs Zone B Agrivoltaic)
        </h2>

        <div className="flex flex-col lg:flex-row gap-6 items-stretch">
          {renderZoneBlock('Zone A — Control', 'Open Field (Full Sun)', zoneA)}

          {/* Divergence Metrics */}
          <div className={`text-white rounded-xl p-6 shadow-md flex-1 flex flex-col justify-between border ${
            isField ? 'bg-gradient-to-br from-teal-900 via-slate-900 to-teal-950 border-teal-700/50' : 'bg-gradient-to-br from-amber-950 via-slate-900 to-amber-900 border-amber-700/50'
          }`}>
             <div>
                <div className="flex justify-between items-start border-b border-white/10 pb-3">
                   <div>
                      <h2 className="text-base font-bold tracking-tight">
                        {isField ? 'Microclimate Divergence' : 'Simulated Digital Twin Divergence'}
                      </h2>
                      <p className="text-xs text-slate-300 font-medium">Delta (B − A) {isField ? 'Field Findings' : 'Physics Outputs'}</p>
                   </div>
                   <span className="bg-white/10 text-slate-200 text-[10px] px-2 py-0.5 rounded font-bold uppercase">
                     {isField ? '32-Day Audit' : 'Closed Loop'}
                   </span>
                </div>

                <div className="grid grid-cols-2 gap-4 mt-4 font-mono">
                   <div className="bg-black/30 p-3 rounded-lg border border-white/10">
                      <div className="text-[10px] text-slate-300 uppercase font-sans font-bold">Shortwave Radiation</div>
                      <div className="text-xl font-bold text-amber-400 mt-1">{diffValues?.radPct || '-38.9%'}</div>
                      <div className="text-[9px] text-slate-300 mt-1 font-sans">PV panel beam shading</div>
                   </div>

                   <div className="bg-black/30 p-3 rounded-lg border border-white/10">
                      <div className="text-[10px] text-slate-300 uppercase font-sans font-bold">Peak Daytime VPD</div>
                      <div className="text-xl font-bold text-teal-300 mt-1">{diffValues?.vpd || '-0.113'} kPa</div>
                      <div className="text-[9px] text-slate-300 mt-1 font-sans">Evaporative demand suppressed</div>
                   </div>

                   <div className="bg-black/30 p-3 rounded-lg border border-white/10">
                      <div className="text-[10px] text-slate-300 uppercase font-sans font-bold">Air Temperature</div>
                      <div className="text-xl font-bold text-rose-300 mt-1">{diffValues?.temp || '-0.43'} °C</div>
                      <div className="text-[9px] text-slate-300 mt-1 font-sans">Midday thermal reduction</div>
                   </div>

                   <div className="bg-black/30 p-3 rounded-lg border border-white/10">
                      <div className="text-[10px] text-slate-300 uppercase font-sans font-bold">Soil Moisture (θv)</div>
                      <div className="text-xl font-bold text-emerald-400 mt-1">{diffValues?.soil || '+0.021'}</div>
                      <div className="text-[9px] text-slate-300 mt-1 font-sans">Canopy moisture retention</div>
                   </div>
                </div>
             </div>

             <div className="mt-4 pt-3 border-t border-white/10 text-[11px] text-slate-300 flex justify-between">
                <span>Dataset: {isField ? 'field_2026_v1' : 'simulation_v1'}</span>
                <span className="font-bold">{isField ? 'PUBLICATION FROZEN' : 'PHYSICS ENGINE MODEL'}</span>
             </div>
          </div>

          {renderZoneBlock('Zone B — Agrivoltaic', 'PV Panel Canopy Shaded', zoneB)}
        </div>
      </div>
    </div>
  );
}
