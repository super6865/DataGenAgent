import { useState } from 'react'
import { Layout, Tabs, Button } from 'antd'
import { MenuFoldOutlined, MenuUnfoldOutlined, FolderOutlined } from '@ant-design/icons'
import DocumentList from './DocumentList'
import TemplateList from './TemplateList'

const { Sider } = Layout

interface ResourceLibrarySidebarProps {
  collapsed?: boolean
  onCollapse?: (collapsed: boolean) => void
}

export default function ResourceLibrarySidebar({
  collapsed: controlledCollapsed,
  onCollapse,
}: ResourceLibrarySidebarProps) {
  const [internalCollapsed, setInternalCollapsed] = useState(false)
  
  // Use controlled or internal state
  const collapsed = controlledCollapsed !== undefined ? controlledCollapsed : internalCollapsed
  const setCollapsed = onCollapse || setInternalCollapsed

  const handleCollapse = () => {
    setCollapsed(!collapsed)
  }

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={setCollapsed}
      width={320}
      theme="light"
      style={{
        borderLeft: '1px solid #f0f0f0',
        backgroundColor: '#fff',
      }}
      trigger={null}
    >
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FolderOutlined style={{ fontSize: '18px', color: '#1890ff' }} />
            {!collapsed && <span className="font-medium text-gray-800">资源库</span>}
          </div>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={handleCollapse}
            size="small"
          />
        </div>

        {/* Content */}
        {!collapsed && (
          <div className="flex-1 overflow-hidden flex flex-col">
            <Tabs
              defaultActiveKey="documents"
              type="card"
              size="small"
              style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
              className="resource-library-tabs"
              items={[
                {
                  key: 'documents',
                  label: '数据文档',
                  children: (
                    <div className="flex-1 overflow-hidden">
                      <DocumentList />
                    </div>
                  ),
                },
                // 数据源功能暂时隐藏，待开发
                // {
                //   key: 'datasources',
                //   label: '数据源',
                //   children: (
                //     <div className="p-4 text-center text-gray-400">
                //       <p>数据源功能即将推出</p>
                //     </div>
                //   ),
                // },
                {
                  key: 'templates',
                  label: '模版库',
                  children: (
                    <div className="flex-1 overflow-hidden">
                      <TemplateList />
                    </div>
                  ),
                },
              ]}
            />
          </div>
        )}
      </div>
    </Sider>
  )
}
