import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Table, Button, Space, message, Popconfirm, Tag, Pagination, Input, Modal, Typography } from 'antd'
import { SearchOutlined, DeleteOutlined, EyeOutlined, ReloadOutlined, PlusOutlined, CopyOutlined } from '@ant-design/icons'
import { dataTemplateService, DataTemplate } from '../../services/dataTemplateService'
import { TemplateCreateModal } from '../../components/TemplateCreate'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Text } = Typography

export default function TemplateListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [templates, setTemplates] = useState<DataTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  })
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewTemplate, setPreviewTemplate] = useState<DataTemplate | null>(null)
  const [createModalVisible, setCreateModalVisible] = useState(false)

  // Check URL params for action=create
  useEffect(() => {
    const action = searchParams.get('action')
    if (action === 'create') {
      setCreateModalVisible(true)
      // Remove the action param from URL
      searchParams.delete('action')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  useEffect(() => {
    loadTemplates()
  }, [pagination.current, pagination.pageSize, searchKeyword])

  const loadTemplates = async () => {
    setLoading(true)
    try {
      const response = await dataTemplateService.getList(
        pagination.current,
        pagination.pageSize,
        searchKeyword || undefined
      )
      if (response.success && response.data) {
        const items = Array.isArray(response.data.items) ? response.data.items : []
        setTemplates(items)
        setPagination((prev) => ({ ...prev, total: response.data.total || 0 }))
      } else {
        message.error('加载模板列表失败')
        setTemplates([])
      }
    } catch (error: any) {
      console.error('Error loading templates:', error)
      const errorMessage = error?.response?.data?.detail || error?.message || '加载模板列表失败'
      message.error(errorMessage)
      setTemplates([])
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      const response = await dataTemplateService.delete(id)
      if (response.success) {
        message.success('删除成功')
        loadTemplates()
      } else {
        throw new Error(response.message)
      }
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }

  const handleCopy = async (id: number) => {
    try {
      const response = await dataTemplateService.copy(id)
      if (response.success) {
        message.success('复制成功')
        loadTemplates()
      } else {
        throw new Error(response.message)
      }
    } catch (error: any) {
      message.error(error.message || '复制失败')
    }
  }

  const handlePreview = async (record: DataTemplate) => {
    try {
      const response = await dataTemplateService.getById(record.id)
      if (response.success) {
        setPreviewTemplate(response.data)
      } else {
        setPreviewTemplate(record)
      }
    } catch (error) {
      setPreviewTemplate(record)
    }
    setPreviewVisible(true)
  }

  const handleSearch = (value: string) => {
    setSearchKeyword(value)
    setPagination((prev) => ({ ...prev, current: 1 }))
  }

  const handleCreate = () => {
    setCreateModalVisible(true)
  }

  const handleCreateSuccess = () => {
    loadTemplates()
  }

  const columns: ColumnsType<DataTemplate> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      width: 300,
      render: (text: string) => <span title={text}>{text}</span>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 250,
      render: (text: string) => text ? <span title={text}>{text}</span> : '-',
    },
    {
      title: '字段数量',
      dataIndex: 'field_count',
      key: 'field_count',
      width: 120,
      render: (count: number) => <Tag>{count}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-',
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
      width: 250,
      render: (_: any, record: DataTemplate) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
          >
            预览
          </Button>
          <Button
            type="link"
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleCopy(record.id)}
          >
            复制
          </Button>
          <Popconfirm
            title="确定要删除这个模板吗？"
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
      {/* 第一层：标题 */}
      <div className="flex items-center justify-between py-4 px-6">
        <div className="text-[20px] font-medium leading-6 coz-fg-plus">模版库</div>
      </div>
      
      {/* 第二层：搜索框和操作按钮 */}
      <div className="box-border coz-fg-secondary pt-1 pb-3 px-6">
        <div className="flex items-center justify-between gap-4">
          <Space size="middle">
            <Input
              placeholder="搜索模板..."
              prefix={<SearchOutlined />}
              value={searchKeyword}
              onChange={(e) => handleSearch(e.target.value)}
              allowClear
              style={{ width: 300 }}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={loadTemplates}
            >
              刷新
            </Button>
          </Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            创建模板
          </Button>
        </div>
      </div>
      
      {/* 第三层：内容区 */}
      <div className="flex-1 overflow-hidden px-6 flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <Table
            columns={columns}
            dataSource={templates || []}
            rowKey="id"
            loading={loading}
            pagination={false}
            scroll={{ y: 'calc(100vh - 350px)' }}
          />
        </div>
        
        {/* 分页 */}
        <div className="py-4 flex justify-end">
          <Pagination
            current={pagination.current}
            pageSize={pagination.pageSize}
            total={pagination.total}
            onChange={(page, pageSize) => {
              setPagination((prev) => ({ ...prev, current: page, pageSize }))
            }}
            showSizeChanger
            showQuickJumper
            showTotal={(total) => `共 ${total} 条`}
          />
        </div>
      </div>

      {/* 预览Modal */}
      <Modal
        title={previewTemplate?.name}
        open={previewVisible}
        onCancel={() => {
          setPreviewVisible(false)
          setPreviewTemplate(null)
        }}
        footer={null}
        width={800}
      >
        {previewTemplate && (
          <div>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {previewTemplate.description && (
                <div>
                  <Text strong>模板描述：</Text>
                  <Text>{previewTemplate.description}</Text>
                </div>
              )}
              <div>
                <Text strong>字段数量：</Text>
                <Text>{previewTemplate.field_count}</Text>
              </div>
              <div>
                <Text strong>创建时间：</Text>
                <Text>{previewTemplate.created_at 
                  ? dayjs(previewTemplate.created_at).format('YYYY-MM-DD HH:mm:ss')
                  : '未知时间'}</Text>
              </div>
              {previewTemplate.updated_at && (
                <div>
                  <Text strong>更新时间：</Text>
                  <Text>{dayjs(previewTemplate.updated_at).format('YYYY-MM-DD HH:mm:ss')}</Text>
                </div>
              )}
              <div>
                <Text strong>JSON Schema：</Text>
                <pre style={{ 
                  background: '#f5f5f5', 
                  padding: '12px', 
                  borderRadius: '4px',
                  maxHeight: '300px',
                  overflow: 'auto'
                }}>
                  {JSON.stringify(previewTemplate.schema, null, 2)}
                </pre>
              </div>
              {previewTemplate.example_data && (
                <div>
                  <Text strong>示例数据：</Text>
                  <pre style={{ 
                    background: '#f5f5f5', 
                    padding: '12px', 
                    borderRadius: '4px',
                    maxHeight: '300px',
                    overflow: 'auto'
                  }}>
                    {JSON.stringify(previewTemplate.example_data, null, 2)}
                  </pre>
                </div>
              )}
            </Space>
          </div>
        )}
      </Modal>

      {/* Create Template Modal */}
      <TemplateCreateModal
        visible={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onSuccess={handleCreateSuccess}
      />
    </div>
  )
}
