import { useEffect, useState, useMemo } from 'react';
import { ShieldCheck, Cpu, Clock as ClockIcon, Radio } from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { api } from '../services/api';
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
    const fetchData = async () => {
      try {
        const [resA, resB] = await Promise.all([
          api.get('/api/live/zone/A', { params: { mode: datasetMode } }),
          api.get('/api/live/zone/B', { params: { mode: datasetMode } })
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
    
    fetchData();
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
     const timestampDisplay = data?.timestamp || '2026-10-02 23:55:00';

     return (
       <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
             <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                <h2 className="text-base font-bold text-slate-800 uppercase tracking-tight">{title}</h2>
                <span className={`px-2 py-0.5 text-[10px] font-bold rounded uppercase ${QUALITY_BG[quality] || 'bg-slate-100'} ${QUALITY_COLORS[quality] || 'text-slate-600'}`}>
                   {isField ? `STATUS: COMPLETED` : `ENGINE: SIMULATED`}
                </span>
             </div>
             <span className="text-xs text-slate-600 font-mono font-bold flex items-center bg-slate-50 px-2.5 py-1 rounded border border-slate-200">
                <ClockIcon className="w-3.5 h-3.5 mr-1.5 text-teal-600" />
                {timestampDisplay}
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
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Radio className={`w-5 h-5 ${isField ? 'text-teal-700' : 'text-amber-700'}`} />
            <h1 className="text-xl font-bold text-slate-800">Live Monitoring & Sensor Telemetry Archive</h1>
            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full border flex items-center ${
              isField ? 'bg-teal-100 text-teal-800 border-teal-200' : 'bg-amber-100 text-amber-800 border-amber-200'
            }`}>
              {isField ? <ShieldCheck className="w-3.5 h-3.5 mr-1" /> : <Cpu className="w-3.5 h-3.5 mr-1" />}
              {isField ? 'COMPLETED CAMPAIGN AUDIT' : 'DIGITAL TWIN SIMULATOR'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Final audited microclimate transducer readings for 2-day field campaign (01 Oct 2026 – 02 Oct 2026).
          </p>
        </div>

        <div className={`flex items-center border px-3 py-1.5 rounded-lg text-xs font-bold space-x-2 ${
          isField ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-amber-50 text-amber-800 border-amber-200'
        }`}>
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
          <span>DATE: 01–02 OCT 2026 (CAMPAIGN COMPLETED)</span>
        </div>
      </div>

      {/* Render Zone Blocks */}
      {renderZoneBlock("ZONE A — OPEN FIELD (CONTROL)", zoneA, "#3b82f6")}
      {renderZoneBlock("ZONE B — AGRIVOLTAIC (PV CANOPY)", zoneB, "#10b981")}

      {/* Microclimate Divergence Table */}
      {diffValues && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
             <h2 className="text-base font-bold text-slate-800">
                Canopy Divergence Summary (Zone B - Zone A)
             </h2>
             <span className="text-xs font-mono text-teal-700 font-bold bg-teal-50 px-2.5 py-1 rounded border border-teal-200">
                Campaign Period: 01 Oct 2026 – 02 Oct 2026
             </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 font-mono text-xs">
             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Δ Air Temp</div>
                <div className="text-sm font-bold text-teal-700">{diffValues.temp} °C</div>
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Δ Humidity</div>
                <div className="text-sm font-bold text-blue-700">{diffValues.rh} %</div>
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Δ Soil Moisture</div>
                <div className="text-sm font-bold text-emerald-700">{diffValues.soil} m³/m³</div>
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Δ VPD</div>
                <div className="text-sm font-bold text-purple-700">{diffValues.vpd} kPa</div>
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Δ Soil Temp</div>
                <div className="text-sm font-bold text-amber-700">{diffValues.soilT} °C</div>
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Δ Irradiance</div>
                <div className="text-sm font-bold text-yellow-700">{diffValues.rs_incoming} W/m²</div>
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Δ Reflected Rs</div>
                <div className="text-sm font-bold text-slate-700">{diffValues.rs_reflected} W/m²</div>
             </div>

             <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Δ Albedo</div>
                <div className="text-sm font-bold text-slate-700">{diffValues.albedo}</div>
             </div>
          </div>
        </div>
      )}
    </div>
  );
}
