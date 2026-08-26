import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import ExperimentTimeline from './components/ExperimentTimeline';
import Overview from './pages/Overview';
import LiveMonitoring from './pages/LiveMonitoring';
import ZoneComparison from './pages/ZoneComparison';
import GraphsTrends from './pages/GraphsTrends';
import Agronomy from './pages/Agronomy';
import Predictions from './pages/Predictions';
import Shap from './pages/Shap';
import Diagnostics from './pages/Diagnostics';
import Validation from './pages/Validation';
import Export from './pages/Export';
import FieldExperiment from './pages/FieldExperiment';

function App() {
  return (
    <Router>
      <div className="flex h-screen bg-slate-50 text-slate-900 overflow-hidden">
        <Sidebar />
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <Header />
          <ExperimentTimeline />
          <main className="flex-1 overflow-auto p-6">
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/live" element={<LiveMonitoring />} />
              <Route path="/comparison" element={<ZoneComparison />} />
              <Route path="/trends" element={<GraphsTrends />} />
              <Route path="/agronomy" element={<Agronomy />} />
              <Route path="/predictions" element={<Predictions />} />
              <Route path="/shap" element={<Shap />} />
              <Route path="/diagnostics" element={<Diagnostics />} />
              <Route path="/experiment" element={<FieldExperiment />} />
              <Route path="/validation" element={<Validation />} />
              <Route path="/export" element={<Export />} />
              {/* Other routes will be added in subsequent phases */}
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App;
