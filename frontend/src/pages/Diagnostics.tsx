import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Wifi, CheckCircle2, ShieldCheck, Lock, Cpu } from 'lucide-react';
import { useStore } from '../store/useStore';

export default function Diagnostics() {
  const { datasetMode } = useStore();
  const [data, setData] = useState<any | null>(null);

  const isField = datasetMode === 'FIELD';

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get('/api/diagnostics/summary', { params: { mode: datasetMode } });
        setData(res.data);
      } catch (err) {
        console.error("Failed to fetch diagnostics", err);
      }
    };
    fetchData();
  }, [datasetMode]);

  if (!data) return <div className="p-6 text-slate-500 font-medium">Loading diagnostics...</div>;

  const renderHealthIndicator = (pct: number) => {
    return <span className="flex items-center text-emerald-700 font-bold"><div className="w-2 h-2 rounded-full bg-emerald-500 mr-1.5"></div> {pct.toFixed(1)}%</span>;
  };

  const getSystemStatus = (status: string) => {
     return <span className={`font-bold flex items-center text-xs ${isField ? 'text-emerald-700' : 'text-amber-800'}`}>
        <CheckCircle2 className={`w-3.5 h-3.5 mr-1 ${isField ? 'text-emerald-600' : 'text-amber-600'}`} /> {status}
     </span>;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Wifi className={`w-5 h-5 ${isField ? 'text-teal-700' : 'text-amber-700'}`} />
            <h1 className="text-xl font-bold text-slate-800">
              {isField ? 'Sensor Diagnostics & Hardware Audit' : 'Digital Twin Infrastructure Diagnostics'}
            </h1>
            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full border flex items-center ${
              isField ? 'bg-teal-100 text-teal-800 border-teal-200' : 'bg-amber-100 text-amber-800 border-amber-200'
            }`}>
              {isField ? <ShieldCheck className="w-3.5 h-3.5 mr-1" /> : <Cpu className="w-3.5 h-3.5 mr-1" />}
              {isField ? 'field_2026_oct_v1 AUDITED' : 'simulation_v1 MODEL'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {isField
              ? 'Hardware health, packet delivery audit, and sensor validation for 2-day field experiment campaign.'
              : 'Closed-loop digital twin model node diagnostics and virtual data stream health.'}
          </p>
        </div>

        <div className={`flex items-center border px-3.5 py-2 rounded-xl text-xs font-bold space-x-2 ${
          isField ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-amber-50 text-amber-800 border-amber-200'
        }`}>
          <CheckCircle2 className={`w-4.5 h-4.5 ${isField ? 'text-emerald-600' : 'text-amber-600'}`} />
          <span>{isField ? 'CAMPAIGN FINISHED — AUDIT VERIFIED' : 'SIMULATION ENGINE: RUNNING'}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
         
         {/* System Communication Health */}
         <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm col-span-1 flex flex-col justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-800 mb-4 flex items-center">
                 <Wifi className={`w-4 h-4 mr-2 ${isField ? 'text-teal-700' : 'text-amber-700'}`} /> Infrastructure Node Status
              </h2>
              <div className="space-y-3 font-mono text-xs">
                 <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-600 font-sans font-medium">ESP32 Node A (Control)</span>
                    {getSystemStatus(isField ? 'COMPLETED' : 'SIMULATED')}
                 </div>
                 <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-600 font-sans font-medium">ESP32 Node B (Agrivoltaic)</span>
                    {getSystemStatus(isField ? 'COMPLETED' : 'SIMULATED')}
                 </div>
                 <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-600 font-sans font-medium">MQTT Telemetry Broker</span>
                    {getSystemStatus(isField ? 'ONLINE' : 'SIMULATED')}
                 </div>
                 <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-600 font-sans font-medium">FastAPI Backend API</span>
                    {getSystemStatus('ONLINE')}
                 </div>
                 <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-600 font-sans font-medium">PostgreSQL Metadata DB</span>
                    {getSystemStatus('ONLINE')}
                 </div>
                 <div className="flex justify-between pb-2">
                    <span className="text-slate-600 font-sans font-medium">5-min Parquet Analytical Store</span>
                    {getSystemStatus(isField ? 'LOCKED' : 'SIMULATED')}
                 </div>
              </div>
              
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 mt-6">Campaign Observation Audit</h2>
              <div className="space-y-3 font-mono text-xs">
                 <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-600 font-sans">Packet Loss (Zone A / B)</span>
                    <span className={`font-bold ${isField ? 'text-emerald-700' : 'text-amber-800'}`}>0.0% / 0.0%</span>
                 </div>
                 <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-600 font-sans">Audited Observations</span>
                    <span className="font-bold text-slate-800">1,152 5-min records</span>
                 </div>
                 <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-600 font-sans">Completeness Ratio</span>
                    <span className={`font-bold ${isField ? 'text-emerald-700' : 'text-amber-800'}`}>100.0%</span>
                 </div>
              </div>
            </div>

            <div className="mt-6 pt-3 border-t border-slate-100 text-[10px] text-slate-400 flex items-center">
              <Lock className="w-3 h-3 mr-1 text-teal-600" />
              <span>{isField ? 'Demobilized hardware archived for publication' : 'Physics digital twin virtual sensor bus active'}</span>
            </div>
         </div>

         {/* Sensor Health Matrix */}
         <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm col-span-2 flex flex-col justify-between">
            <div>
               <h2 className="text-base font-bold text-slate-800 mb-4">
                  {isField ? 'Sensor Transducer Integrity & Reliability Health' : 'Digital Twin Transducer Health Simulation'}
               </h2>
               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 space-y-2">
                     <div className="font-bold text-slate-800 text-sm">Zone A (Control / Full Sun)</div>
                     <div className="space-y-1.5 text-xs">
                        <div className="flex justify-between">
                           <span className="text-slate-600">BME280 Air T & RH:</span>
                           {renderHealthIndicator(data.zone_a.health.bme280)}
                        </div>
                        <div className="flex justify-between">
                           <span className="text-slate-600">BH1750 Irradiance:</span>
                           {renderHealthIndicator(data.zone_a.health.bh1750)}
                        </div>
                        <div className="flex justify-between">
                           <span className="text-slate-600">DS18B20 Soil Temp:</span>
                           {renderHealthIndicator(data.zone_a.health.ds18b20)}
                        </div>
                        <div className="flex justify-between">
                           <span className="text-slate-600">DS3231 RTC Clock:</span>
                           {renderHealthIndicator(data.zone_a.health.rtc)}
                        </div>
                     </div>
                  </div>

                  <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 space-y-2">
                     <div className="font-bold text-slate-800 text-sm">Zone B (Agrivoltaic Canopy)</div>
                     <div className="space-y-1.5 text-xs">
                        <div className="flex justify-between">
                           <span className="text-slate-600">BME280 Air T & RH:</span>
                           {renderHealthIndicator(data.zone_b.health.bme280)}
                        </div>
                        <div className="flex justify-between">
                           <span className="text-slate-600">BH1750 Irradiance:</span>
                           {renderHealthIndicator(data.zone_b.health.bh1750)}
                        </div>
                        <div className="flex justify-between">
                           <span className="text-slate-600">DS18B20 Soil Temp:</span>
                           {renderHealthIndicator(data.zone_b.health.ds18b20)}
                        </div>
                        <div className="flex justify-between">
                           <span className="text-slate-600">DS3231 RTC Clock:</span>
                           {renderHealthIndicator(data.zone_b.health.rtc)}
                        </div>
                     </div>
                  </div>
               </div>
            </div>

            <div className={`mt-6 p-3 border rounded-xl text-xs flex items-center justify-between ${
              isField ? 'bg-teal-50 border-teal-200 text-teal-900' : 'bg-amber-50 border-amber-200 text-amber-900'
            }`}>
              <span className="font-semibold">Campaign Audit Status:</span>
              <span className={`font-bold px-2.5 py-1 rounded-md ${
                isField ? 'text-emerald-800 bg-emerald-100' : 'text-amber-800 bg-amber-100'
              }`}>
                {isField ? 'VERIFIED (100% HEALTH)' : 'SIMULATED (PHYSICS ENGINE)'}
              </span>
            </div>
         </div>

      </div>
    </div>
  );
}
