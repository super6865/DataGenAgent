import { Outlet } from 'react-router-dom'
import { Navbar } from './Navbar'
import { Breadcrumb } from './Breadcrumb'

export function TemplateLayout() {
  return (
    <div className="relative h-full min-h-0 flex-shrink flex overflow-y-hidden">
      <Navbar />
      <div className="flex flex-col flex-1 overflow-hidden coz-bg-plus">
        <Breadcrumb />
        <div className="flex-1 overflow-x-auto overflow-y-hidden min-h-0">
          <div className="min-w-[960px] h-full">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  )
}
