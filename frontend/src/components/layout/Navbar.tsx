import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import type { MenuProps } from 'antd'
import {
  DatabaseOutlined,
  HistoryOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SettingOutlined,
  MonitorOutlined,
  FileTextOutlined,
  PictureOutlined,
  FolderOutlined,
} from '@ant-design/icons'
import classNames from 'classnames'

const { Sider } = Layout

interface MenuItem {
  key: string
  label: string
  icon?: React.ReactNode
  children?: MenuItem[]
}

const menuItems: MenuItem[] = [
  {
    key: '/',
    label: '数据生成',
    icon: <DatabaseOutlined />,
  },
  {
    key: 'resource-library',
    label: '资源库',
    icon: <FolderOutlined />,
    children: [
      {
        key: '/resource-library/documents',
        label: '数据文档',
        icon: <FileTextOutlined />,
      },
      // 数据源功能暂时隐藏，待开发
      // {
      //   key: '/resource-library/datasources',
      //   label: '数据源',
      //   icon: <DatabaseOutlined />,
      // },
      {
        key: '/resource-library/templates',
        label: '模版库',
        icon: <FileTextOutlined />,
      },
    ],
  },
  {
    key: 'monitoring',
    label: '监控',
    icon: <MonitorOutlined />,
    children: [
      {
        key: '/history',
        label: '历史记录',
        icon: <HistoryOutlined />,
      },
      {
        key: '/event-log',
        label: '事件日志',
        icon: <FileTextOutlined />,
      },
    ],
  },
  {
    key: 'system-config',
    label: '系统配置',
    icon: <PictureOutlined />,
    children: [
      {
        key: '/settings',
        label: '模型配置',
        icon: <SettingOutlined />,
      },
    ],
  },
]

export function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [selectedKeys, setSelectedKeys] = useState<string[]>([])
  const [openKeys, setOpenKeys] = useState<string[]>([])

  useEffect(() => {
    // 根据当前路径设置选中的菜单项和展开的父级菜单
    const path = location.pathname
    const keys: string[] = []
    const open: string[] = []
    
    if (path === '/' || path === '') {
      keys.push('/')
    } else if (path === '/history' || path.startsWith('/history')) {
      keys.push('/history')
      open.push('monitoring')
    } else if (path === '/event-log' || path.startsWith('/event-log')) {
      keys.push('/event-log')
      open.push('monitoring')
    } else if (path === '/resource-library/documents' || path.startsWith('/resource-library/documents')) {
      keys.push('/resource-library/documents')
      open.push('resource-library')
    // 数据源功能暂时隐藏，待开发
    // } else if (path === '/resource-library/datasources' || path.startsWith('/resource-library/datasources')) {
    //   keys.push('/resource-library/datasources')
    //   open.push('resource-library')
    } else if (path === '/resource-library/templates' || path.startsWith('/resource-library/templates')) {
      keys.push('/resource-library/templates')
      open.push('resource-library')
    } else if (path === '/settings' || path.startsWith('/settings')) {
      keys.push('/settings')
      open.push('system-config')
    }
    
    setSelectedKeys(keys)
    setOpenKeys(open)
  }, [location.pathname])

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    // 处理菜单点击，只处理叶子节点
    if (key === '/' || key.startsWith('/')) {
      navigate(key)
    }
  }

  const handleOpenChange: MenuProps['onOpenChange'] = (keys) => {
    setOpenKeys(keys)
  }

  return (
    <div className="h-full">
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={240}
        theme="light"
        className={classNames(
          'h-full min-h-full max-h-full min-w-[88px] !px-0 overflow-hidden !bg-white',
        )}
        style={{
          overflow: 'hidden',
          height: '100%',
          position: 'relative',
        }}
      >
        <div className={classNames('mb-[10px] relative', collapsed ? 'px-2' : 'px-6')}>
          <div className={classNames(
            'flex items-center w-full gap-3 py-[8px]',
            collapsed ? 'justify-center' : 'pl-[8px] pr-0'
          )}>
            {collapsed ? (
              <div className="flex items-center justify-center w-full">
                <div 
                  className="w-[36px] h-[36px] flex items-center justify-center rounded text-white font-bold text-lg"
                  style={{ backgroundColor: 'rgba(var(--coze-brand-7), 1)' }}
                >
                  DG
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div 
                    className="h-[36px] w-[36px] flex items-center justify-center rounded text-white font-bold text-lg flex-shrink-0"
                    style={{ backgroundColor: 'rgba(var(--coze-brand-7), 1)' }}
                  >
                    DG
                  </div>
                  <span className="text-2xl font-semibold coz-fg-primary whitespace-nowrap">DataGen</span>
                </div>
                <div
                  className="cursor-pointer flex-shrink-0 coz-fg-secondary h-[16px] w-[16px] hover:coz-fg-primary transition-colors flex items-center justify-center"
                  onClick={() => setCollapsed(!collapsed)}
                >
                  <MenuFoldOutlined className="text-base" />
                </div>
              </>
            )}
          </div>
          {collapsed && (
            <div
              className="absolute top-[17px] right-2 cursor-pointer flex-shrink-0 coz-fg-secondary h-[16px] w-[16px] hover:coz-fg-primary transition-colors flex items-center justify-center z-10"
              onClick={() => setCollapsed(!collapsed)}
            >
              <MenuUnfoldOutlined className="text-base" />
            </div>
          )}
        </div>
        <div className="px-6 flex-1 !pr-[18px] pb-2 overflow-y-auto styled-scrollbar">
          <Menu
            mode="inline"
            selectedKeys={selectedKeys}
            openKeys={openKeys}
            items={menuItems as any}
            onClick={handleMenuClick}
            onOpenChange={handleOpenChange}
            className="border-r-0"
            style={{
              background: 'transparent',
            }}
          />
        </div>
      </Sider>
    </div>
  )
}
