import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Spin } from 'antd'
import { TemplateLayout } from './components/layout/TemplateLayout'
import DataGenerationPage from './pages/Home/DataGenerationPage'
import HistoryPage from './pages/History/HistoryPage'
import SettingsPage from './pages/Settings/SettingsPage'
import DocumentListPage from './pages/ResourceLibrary/DocumentListPage'
// 数据源功能暂时隐藏，待开发
// import DataSourcePage from './pages/ResourceLibrary/DataSourcePage'
import TemplateListPage from './pages/ResourceLibrary/TemplateListPage'

const EventLogPage = lazy(() => import('./pages/EventLog/EventLogPage'))
const EventLogDetailPage = lazy(() => import('./pages/EventLog/EventLogDetailPage'))

function App() {
  return (
    <Routes>
      <Route path="/" element={<TemplateLayout />}>
        <Route index element={<DataGenerationPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route 
          path="/event-log" 
          element={
            <Suspense fallback={<div className="flex justify-center items-center h-full"><Spin size="large" /></div>}>
              <EventLogPage />
            </Suspense>
          } 
        />
        <Route 
          path="/event-log/traces/:traceId" 
          element={
            <Suspense fallback={<div className="flex justify-center items-center h-full"><Spin size="large" /></div>}>
              <EventLogDetailPage />
            </Suspense>
          } 
        />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="resource-library/documents" element={<DocumentListPage />} />
        {/* 数据源功能暂时隐藏，待开发 */}
        {/* <Route path="resource-library/datasources" element={<DataSourcePage />} /> */}
        <Route path="resource-library/templates" element={<TemplateListPage />} />
      </Route>
    </Routes>
  )
}

export default App
