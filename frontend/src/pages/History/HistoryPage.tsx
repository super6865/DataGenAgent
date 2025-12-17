import { useState, useEffect } from 'react'
import { Table, Button, Space, message, Popconfirm, Tag, Pagination, Modal } from 'antd'
import { DeleteOutlined, EyeOutlined } from '@ant-design/icons'
import { dataGenerationService } from '../../services/dataGenerationService'
import DataPreview from '../../components/DataPreview/DataPreview'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

interface HistoryItem {
  id: number
  user_query: string
  generated_data: string
  data_format: string
  model_used?: string
  created_at: string
  updated_at?: string
}

export default function HistoryPage() {
  const [histories, setHistories] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  })
  const [viewModalVisible, setViewModalVisible] = useState(false)
  const [viewingRecord, setViewingRecord] = useState<HistoryItem | null>(null)

  useEffect(() => {
    loadHistories()
  }, [pagination.current, pagination.pageSize])

  const loadHistories = async () => {
    setLoading(true)
    try {
      const skip = (pagination.current - 1) * pagination.pageSize
      const response = await dataGenerationService.getHistoryList(skip, pagination.pageSize)
      if (response.success) {
        setHistories(response.data)
        setPagination((prev) => ({ ...prev, total: response.total }))
      }
    } catch (error) {
      message.error('加载历史记录失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      const response = await dataGenerationService.deleteHistory(id)
      if (response.success) {
        message.success('删除成功')
        loadHistories()
      } else {
        throw new Error(response.message)
      }
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }

  const handleView = (record: HistoryItem) => {
    setViewingRecord(record)
    setViewModalVisible(true)
  }

  const columns: ColumnsType<HistoryItem> = [
    {
      title: '用户查询',
      dataIndex: 'user_query',
      key: 'user_query',
      ellipsis: true,
      width: 650,
      render: (text: string) => <span title={text}>{text}</span>,
    },
    {
      title: '格式',
      dataIndex: 'data_format',
      key: 'data_format',
      width: 100,
      render: (format: string) => <Tag>{format.toUpperCase()}</Tag>,
    },
    {
      title: '模型',
      dataIndex: 'model_used',
      key: 'model_used',
      width: 150,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: (time: string) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 300,
      render: (_: any, record: HistoryItem) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            查看
          </Button>
          <Popconfirm
            title="确定要删除这条记录吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="pt-2 pb-3 h-full flex flex-col">
      <div className="text-[20px] font-medium leading-6 coz-fg-plus py-4 px-6">历史记录</div>
      <div className="flex-1 overflow-hidden px-6 flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <Table
            columns={columns}
            dataSource={histories}
            rowKey="id"
            loading={loading}
            pagination={false}
          />
        </div>
        {(pagination.total > 0 || pagination.current > 1) && (
          <div className="shrink-0 flex flex-row-reverse justify-between items-center pt-4 border-t border-solid coz-stroke-primary">
            <Pagination
              current={pagination.current}
              pageSize={pagination.pageSize}
              total={pagination.total}
              showSizeChanger={true}
              showTotal={(total) => `共 ${total} 条`}
              onChange={(page, pageSize) => {
                setPagination((prev) => ({ ...prev, current: page, pageSize }))
              }}
              locale={{
                items_per_page: ' / 页',
              }}
            />
          </div>
        )}
      </div>
      <Modal
        title="生成数据详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={null}
        width={1000}
      >
        {viewingRecord && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ marginBottom: 8, fontSize: 14, fontWeight: 600 }}>用户查询</h3>
              <p style={{ margin: 0, color: '#666' }}>{viewingRecord.user_query}</p>
            </div>
            <div>
              <h3 style={{ marginBottom: 8, fontSize: 14, fontWeight: 600 }}>
                生成数据 ({viewingRecord.data_format.toUpperCase()})
              </h3>
              <DataPreview 
                data={viewingRecord.generated_data} 
                format={viewingRecord.data_format} 
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
