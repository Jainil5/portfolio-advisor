import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Screener from './pages/Screener'
import Dashboard from './pages/Dashboard'
import Portfolio from './pages/Portfolio'
import StockPage from './pages/StockPage'
import StockAnalysis from './pages/StockAnalysis'
import Recommendations from './pages/Recommendations'
import Advisor from './pages/Advisor'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Screener />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/stock/:stockId" element={<StockPage />} />
        <Route path="/analysis" element={<StockAnalysis />} />
        <Route path="/recommendations" element={<Recommendations />} />
        <Route path="/advisor" element={<Advisor />} />
        <Route path="/market" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
