import { useMemo } from 'react'
import { Breadcrumb as AntBreadcrumb } from 'antd'
import { useLocation, Link } from 'react-router-dom'

const breadcrumbNameMap: Record<string, string> = {
  '/': '数据生成',
  '/history': '历史记录',
  '/settings': '模型配置',
  '/event-log': '事件日志',
  '/resource-library': '资源库',
  '/resource-library/documents': '数据文档',
  '/resource-library/datasources': '数据源',
  '/resource-library/templates': '模版库',
}

export function Breadcrumb() {
  const location = useLocation()
  const pathSnippets = location.pathname.split('/').filter((i) => i)

  const breadcrumbItems = useMemo(() => {
    const items = [
      {
        title: <Link to="/" className="coz-fg-secondary">首页</Link>,
      },
    ]

    // 检查完整路径是否在映射中（用于跳过中间层级）
    const fullPath = location.pathname
    if (breadcrumbNameMap[fullPath]) {
      items.push({
        title: <span className="coz-fg-primary">{breadcrumbNameMap[fullPath]}</span>,
      })
      return items
    }

    pathSnippets.forEach((_, index) => {
      const url = `/${pathSnippets.slice(0, index + 1).join('/')}`
      const isLast = index === pathSnippets.length - 1
      const snippet = pathSnippets[index]
      
      let title: string = breadcrumbNameMap[url] || snippet

      items.push({
        title: isLast ? (
          <span className="coz-fg-primary">{title}</span>
        ) : (
          <Link to={url} className="coz-fg-secondary hover:coz-fg-primary transition-colors">
            {title}
          </Link>
        ),
      })
    })

    return items
  }, [pathSnippets, location.pathname])

  return (
    <div className="h-[56px] flex items-center justify-between px-6 border-0 border-b border-solid coz-stroke-primary">
      <AntBreadcrumb
        separator={
          <div className="rotate-[22deg] coz-fg-dim inline-block mx-2">/</div>
        }
        items={breadcrumbItems}
        className="[&_.ant-breadcrumb-link]:!text-[13px]"
      />
    </div>
  )
}
