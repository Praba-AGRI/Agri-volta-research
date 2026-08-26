import { useEffect, useState, useMemo } from 'react';
import { Activity, ShieldCheck, CheckCircle2, Calendar, Cpu } from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { useStore } from '../store/useStore';

interface LiveData {
  zone: string;
  timestamp: string;
  soil_moisture?: number;
  soil_moisture_1?: number;
  soil_moisture_2?: number;
  soil_moisture_mean?: number;
  soil_adc_1?: number;
  soil_adc_2?: number;
  soil_calibrated?: boolean;
  air_temperature?: number;
  relative_humidity?: number;
  soil_temperature?: number;
  radiation?: number;
  rs_incoming?: number;
  rs_reflected?: number;
  rns_fao56?: number;
  rns_measured?: number;
  lux_incident?: number;
  lux_reflected?: number;
  albedo?: number;
  pressure?: number;
  rainfall?: number;
  vpd?: number;
  shade_fraction?: number;
  status: string;
  dataset_mode: string;
  quality?: string;
  source?: string;
}

const QUALITY_COLORS: Record<string, string> = {
  'VALID': 'text-emerald-600',
  'PHYSICS_SIMULATED': 'text-amber-600',
  'STALE': 'text-amber-600',
  'INVALID': 'text-red-600',
  'MISSING': 'text-slate-400'
};

const QUALITY_BG: Record<string, string> = {
  'VALID': 'bg-emerald-100',
  'PHYSICS_SIMULATED': 'bg-amber-100',
  'STALE': 'bg-amber-100',
  'INVALID': 'bg-red-100',
  'MISSING': 'bg-slate-100'
};

export default function LiveMonitoring() {
  const { datasetMode } = useStore();
  const [zoneA, setZoneA] = useState<LiveData | null>(null);
  const [zoneB, setZoneB] = useState<LiveData | null>(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [resA, resB] = await Promise.all([
          axios.get(`http://localhost:8000/api/live/zone/A`, { params: { mode: datasetMode } }),
          axios.get(`http://localhost:8000/api/live/zone/B`, { params: { mode: datasetMode } })
        ]);
        
        if (resA.data) {
          setZoneA(resA.data);
        }
        if (resB.data) {
          setZoneB(resB.data);
        }
      } catch (err) {
        console.error("Failed to fetch live data", err);
      }
    };
    
    fetchInitialData();
  }, [datasetMode]);

  const isField = datasetMode === 'FIELD';

  const diffValues = useMemo(() => {
     if (!zoneA || !zoneB) return null;
     
     const diff = (b?: number, a?: number, decimals = 2) => {
        if (b === undefined || a === undefined) return '---';
        const val = b - a;
        return (val > 0 ? '+' : '') + val.toFixed(decimals);
     };

     return {
        rs_incoming: diff(zoneB.rs_incoming, zoneA.rs_incoming, 2),
        rs_reflected: diff(zoneB.rs_reflected, zoneA.rs_reflected, 2),
        rns_fao56: diff(zoneB.rns_fao56, zoneA.rns_fao56, 2),
        rns_measured: diff(zoneB.rns_measured, zoneA.rns_measured, 2),
        albedo: diff(zoneB.albedo, zoneA.albedo, 4),
        temp: diff(zoneB.air_temperature, zoneA.air_temperature, 1),
        vpd: diff(zoneB.vpd, zoneA.vpd, 3),
        soil: diff(zoneB.soil_moisture, zoneA.soil_moisture, 3),
        soilT: diff(zoneB.soil_temperature, zoneA.soil_temperature, 1),
        rh: diff(zoneB.relative_humidity, zoneA.relative_humidity, 1)
     };
  }, [zoneA, zoneB]);

  const renderGauge = (val: number | undefined, unit: string, min: number, max: number, color: string) => {
    const option = {
      series: [
        {
          type: 'gauge',
          center: ['50%', '60%'],
          radius: '90%',
          startAngle: 180,
          endAngle: 0,
          min: min,
          max: max,
          splitNumber: 4,
          axisLine: {
            lineStyle: {
              width: 8,
              color: [
                [0.35, '#3b82f6'],
                [0.6, '#10b981'],
                [1, '#ef4444']
              ]
            }
          },
          pointer: { length: '60%', width: 4, itemStyle: { color: color } },
          axisTick: { show: false },
          splitLine: { length: 6, lineStyle: { width: 1, color: '#cbd5e1' } },
          axisLabel: { color: '#64748b', fontSize: 9, distance: 10 },
          detail: {
            valueAnimation: true,
            formatter: (v: number) => `${v.toFixed(val !== undefined && val < 1 && val > -1 ? 3 : 1)} ${unit}`,
            color: '#1e293b',
            fontSize: 13,
            fontWeight: 'bold',
            offsetCenter: [0, '20%']
          },
          data: [{ value: val ?? 0 }]
        }
      ]
    };
    return <ReactECharts option={option} style={{ height: '140px', width: '100%' }} />;
  };

  const renderZoneBlock = (title: string, data: LiveData | null, gaugeColor: string) => {
     const quality = data?.quality || (isField ? 'VALID' : 'PHYSICS_SIMULATED');
     return (
       <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
             <div className="flex items-center space-x-2">
                <h2 className="text-base font-bold text-slate-800 uppercase tracking-tight">{title}</h2>
                <span className={`px-2 py-0.5 text-[10px] font-bold rounded uppercase ${QUALITY_BG[quality] || 'bg-slate-100'} ${QUALITY_COLORS[quality] || 'text-slate-600'}`}>
                   {isField ? `STATUS: ${quality}` : `ENGINE: SIMULATED`}
                </span>
             </div>
             <span className="text-xs text-slate-500 font-mono flex items-center">
                <ClockIcon className="w-3.5 h-3.5 mr-1 text-slate-400" />
                {isField ? '2026-08-22 23:55:00' : 'CLOSED-LOOP MODEL ACTIVE'}
             </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Soil Moisture (θv)</div>
                {renderGauge(data?.soil_moisture, "m³/m³", 0, 0.35, gaugeColor)}
                <div className="text-[9px] text-teal-800 font-bold mt-1">θ_wp: 0.12 | θ_crit: 0.2025 | θ_fc: 0.27</div>
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Air Temp (T)</div>
                {renderGauge(data?.air_temperature, "°C", 0, 50, "#ef4444")}
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Humidity (RH)</div>
                {renderGauge(data?.relative_humidity, "%", 0, 100, "#0ea5e9")}
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">VPD</div>
                {renderGauge(data?.vpd, "kPa", 0, 3, "#8b5cf6")}
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Soil Temp (Tsoil)</div>
                {renderGauge(data?.soil_temperature, "°C", 0, 50, "#f59e0b")}
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Irradiance (Rs)</div>
                {renderGauge(data?.radiation, "W/m²", 0, 1200, "#eab308")}
             </div>
          </div>
       </div>
     );
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Activity className={`w-5 h-5 ${isField ? 'text-teal-700' : 'text-amber-700'}`} />
            <h1 className="text-xl font-bold text-slate-800">
              {isField ? 'Field Telemetry Gauges & Sensor Monitoring' : 'Digital Twin Physics Simulation Engine'}
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
              ? 'Audited real-world sensor observations (22 July 2026 – 22 August 2026 | Day 32 Finished)'
              : 'Physics-based numerical microclimate engine simulation outputs'}
          </p>
        </div>

        <div className={`flex items-center border px-3.5 py-2 rounded-xl text-xs font-bold space-x-2 ${
          isField ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-amber-50 text-amber-800 border-amber-200'
        }`}>
          <CheckCircle2 className={`w-4.5 h-4.5 ${isField ? 'text-emerald-600' : 'text-amber-600'}`} />
          <span>{isField ? 'EXPERIMENT STATUS: FINISHED' : 'SIMULATION MODE: RUNNING'}</span>
        </div>
      </div>
      
      {renderZoneBlock("ZONE A — OPEN FIELD (CONTROL)", zoneA, "#f59e0b")}
      {renderZoneBlock("ZONE B — AGRIVOLTAIC (PV CANOPY)", zoneB, "#3b82f6")}
      
      {/* Difference Table */}
      <div className="bg-slate-900 rounded-xl shadow-lg border border-slate-800 overflow-hidden text-slate-300">
         <div className="p-4 border-b border-slate-800 bg-slate-950/50 flex justify-between items-center">
            <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center">
               <ShieldCheck className="w-4 h-4 mr-1.5" />
               {isField ? 'Final Agrivoltaic Microclimate Divergence (B − A)' : 'Simulated Digital Twin Microclimate Divergence (B − A)'}
            </h3>
            <span className="text-[10px] text-slate-400 font-mono font-semibold">
              Source: {isField ? 'SD_ARCHIVE (18,432 Observations)' : 'SIMULATION_ENGINE (Physics Model)'}
            </span>
         </div>
         <div className="p-0 overflow-x-auto">
            <table className="w-full text-xs text-left">
               <thead className="bg-slate-800/50 text-[10px] uppercase text-slate-400">
                  <tr>
                     <th className="px-6 py-3 font-semibold">Parameter</th>
                     <th className="px-6 py-3 font-semibold text-right">Zone A (Control)</th>
                     <th className="px-6 py-3 font-semibold text-right">Zone B (Agrivoltaic)</th>
                     <th className="px-6 py-3 font-semibold text-right text-emerald-300">Delta (B − A)</th>
                  </tr>
               </thead>
               <tbody className="divide-y divide-slate-800/50 font-mono">
                  <tr className="hover:bg-slate-800/30">
                     <td className="px-6 py-3 font-sans font-medium text-white">Shortwave Solar Irradiance (Rs)</td>
                     <td className="px-6 py-3 text-right">{zoneA?.rs_incoming?.toFixed(2) ?? '---'}</td>
                     <td className="px-6 py-3 text-right">{zoneB?.rs_incoming?.toFixed(2) ?? '---'}</td>
                     <td className="px-6 py-3 text-right text-emerald-400 font-bold">{diffValues?.rs_incoming} <span className="text-[10px] font-sans text-slate-400">W/m²</span></td>
                  </tr>
                  <tr className="hover:bg-slate-800/30">
                     <td className="px-6 py-3 font-sans font-medium text-white">Air Temperature</td>
                     <td className="px-6 py-3 text-right">{zoneA?.air_temperature?.toFixed(1) ?? '---'}</td>
                     <td className="px-6 py-3 text-right">{zoneB?.air_temperature?.toFixed(1) ?? '---'}</td>
                     <td className="px-6 py-3 text-right text-emerald-400 font-bold">{diffValues?.temp} <span className="text-[10px] font-sans text-slate-400">°C</span></td>
                  </tr>
                  <tr className="hover:bg-slate-800/30">
                     <td className="px-6 py-3 font-sans font-medium text-white">Vapor Pressure Deficit (VPD)</td>
                     <td className="px-6 py-3 text-right">{zoneA?.vpd?.toFixed(3) ?? '---'}</td>
                     <td className="px-6 py-3 text-right">{zoneB?.vpd?.toFixed(3) ?? '---'}</td>
                     <td className="px-6 py-3 text-right text-emerald-400 font-bold">{diffValues?.vpd} <span className="text-[10px] font-sans text-slate-400">kPa</span></td>
                  </tr>
                  <tr className="hover:bg-slate-800/30">
                     <td className="px-6 py-3 font-sans font-medium text-white">Soil Moisture (θv)</td>
                     <td className="px-6 py-3 text-right">{zoneA?.soil_moisture?.toFixed(3) ?? '---'}</td>
                     <td className="px-6 py-3 text-right">{zoneB?.soil_moisture?.toFixed(3) ?? '---'}</td>
                     <td className="px-6 py-3 text-right text-emerald-400 font-bold">{diffValues?.soil} <span className="text-[10px] font-sans text-slate-400">m³/m³</span></td>
                  </tr>
                  <tr className="hover:bg-slate-800/30">
                     <td className="px-6 py-3 font-sans font-medium text-white">Soil Temperature</td>
                     <td className="px-6 py-3 text-right">{zoneA?.soil_temperature?.toFixed(1) ?? '---'}</td>
                     <td className="px-6 py-3 text-right">{zoneB?.soil_temperature?.toFixed(1) ?? '---'}</td>
                     <td className="px-6 py-3 text-right text-emerald-400 font-bold">{diffValues?.soilT} <span className="text-[10px] font-sans text-slate-400">°C</span></td>
                  </tr>
                  <tr className="hover:bg-slate-800/30">
                     <td className="px-6 py-3 font-sans font-medium text-white">Relative Humidity</td>
                     <td className="px-6 py-3 text-right">{zoneA?.relative_humidity?.toFixed(1) ?? '---'}</td>
                     <td className="px-6 py-3 text-right">{zoneB?.relative_humidity?.toFixed(1) ?? '---'}</td>
                     <td className="px-6 py-3 text-right text-emerald-400 font-bold">{diffValues?.rh} <span className="text-[10px] font-sans text-slate-400">%</span></td>
                  </tr>
               </tbody>
            </table>
         </div>
      </div>
      
    </div>
  );
}

function ClockIcon(props: any) {
  return (
    <svg {...props} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}
