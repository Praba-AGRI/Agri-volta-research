import { create } from 'zustand';

interface DashboardState {
  datasetMode: 'FIELD' | 'SIMULATION';
  setDatasetMode: (mode: 'FIELD' | 'SIMULATION') => void;
  
  selectedZone: 'A' | 'B' | 'BOTH';
  setSelectedZone: (zone: 'A' | 'B' | 'BOTH') => void;
  
  timeRange: '24h' | '3d' | '7d' | '30d' | 'season' | 'custom';
  setTimeRange: (range: '24h' | '3d' | '7d' | '30d' | 'season' | 'custom') => void;
  
  selectedParameter: string;
  setSelectedParameter: (param: string) => void;
}

export const useStore = create<DashboardState>((set) => ({
  datasetMode: 'FIELD', // Default to field telemetry
  setDatasetMode: (mode) => set({ datasetMode: mode }),
  
  selectedZone: 'BOTH',
  setSelectedZone: (zone) => set({ selectedZone: zone }),
  
  timeRange: '24h',
  setTimeRange: (range) => set({ timeRange: range }),
  
  selectedParameter: 'soil_moisture',
  setSelectedParameter: (param) => set({ selectedParameter: param }),
}));
