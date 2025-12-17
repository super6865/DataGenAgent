import { Card, Empty } from 'antd'
import { DatabaseOutlined } from '@ant-design/icons'

export default function DataSourcePage() {
  return (
    <div className="pt-2 pb-3 h-full flex flex-col">
      <div className="text-[20px] font-medium leading-6 coz-fg-plus py-4 px-6">数据源</div>
      <div className="flex-1 overflow-hidden px-6 flex flex-col">
        <div className="flex-1 flex items-center justify-center">
          <Card style={{ width: 500, textAlign: 'center' }}>
            <Empty
              image={<DatabaseOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />}
              description={
                <span style={{ color: '#999', fontSize: '16px' }}>
                  数据源功能即将推出
                </span>
              }
            />
          </Card>
        </div>
      </div>
    </div>
  )
}
