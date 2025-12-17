import { useState, useEffect, useCallback } from 'react'
import { Input, List, Card, Space, Typography, Button, Popconfirm, message, Pagination, Tag, Modal } from 'antd'
import { SearchOutlined, DeleteOutlined, EditOutlined, EyeOutlined, CopyOutlined, FileTextOutlined } from '@ant-design/icons'
import { dataTemplateService, DataTemplate } from '../../services/dataTemplateService'

const { Text } = Typography

export default function TemplateList() {
  const [templates, setTemplates] = useState<DataTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewTemplate, setPreviewTemplate] = useState<DataTemplate | null>(null)
  const [editingTemplate, setEditingTemplate] = useState<{ id: number; name: string } | null>(null)

  // Load templates
  const loadTemplates = useCallback(async (currentPage: number = 1, keyword?: string) => {
    setLoading(true)
    try {
      const response = await dataTemplateService.getList(currentPage, pageSize, keyword)
      if (response.success) {
        setTemplates(response.data.items)
        setTotal(response.data.total)
      }
    } catch (error: any) {
      message.error('加载模板列表失败')
    } finally {
      setLoading(false)
    }
  }, [pageSize])

  // Initial load
  useEffect(() => {
    loadTemplates(page, searchKeyword)
  }, [page, searchKeyword, loadTemplates])

  // Handle search
  const handleSearch = (value: string) => {
    setSearchKeyword(value)
    setPage(1) // Reset to first page when searching
  }

  // Handle delete
  const handleDelete = async (templateId: number) => {
    try {
      const response = await dataTemplateService.delete(templateId)
      if (response.success) {
        message.success('删除成功')
        loadTemplates(page, searchKeyword)
      }
    } catch (error: any) {
      message.error('删除失败')
    }
  }

  // Handle copy
  const handleCopy = async (templateId: number) => {
    try {
      const response = await dataTemplateService.copy(templateId)
      if (response.success) {
        message.success('复制成功')
        loadTemplates(page, searchKeyword)
      }
    } catch (error: any) {
      message.error('复制失败')
    }
  }

  // Handle preview
  const handlePreview = (template: DataTemplate) => {
    setPreviewTemplate(template)
    setPreviewVisible(true)
  }

  // Handle page change
  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  // Handle use template (placeholder for now)
  const handleUse = (template: DataTemplate) => {
    message.info('使用模板功能将在后续版本中实现')
  }

  return (
    <div className="h-full flex flex-col">
      {/* Search */}
      <div className="p-4 border-b border-gray-200">
        <Input
          placeholder="搜索模板..."
          prefix={<SearchOutlined />}
          value={searchKeyword}
          onChange={(e) => handleSearch(e.target.value)}
          allowClear
        />
      </div>

      {/* Templates List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center">
            <Text type="secondary">加载中...</Text>
          </div>
        ) : templates.length === 0 ? (
          <div className="p-4 text-center text-gray-400">
            <p>暂无模板</p>
          </div>
        ) : (
          <List
            dataSource={templates}
            renderItem={(template) => (
              <List.Item
                style={{
                  padding: '12px 16px',
                  borderBottom: '1px solid #f0f0f0',
                }}
              >
                <Card
                  size="small"
                  style={{ width: '100%', border: 'none' }}
                  bodyStyle={{ padding: 0 }}
                >
                  <Space direction="vertical" style={{ width: '100%' }} size="small">
                    {/* Template Info */}
                    <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                      <Space>
                        <FileTextOutlined style={{ fontSize: '18px', color: '#1890ff' }} />
                        <div>
                          {editingTemplate?.id === template.id ? (
                            <Input
                              size="small"
                              value={editingTemplate.name}
                              onChange={(e) => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                              onPressEnter={() => {
                                if (editingTemplate.name.trim()) {
                                  // TODO: Implement rename functionality
                                  message.info('重命名功能将在后续版本中实现')
                                  setEditingTemplate(null)
                                }
                              }}
                              onBlur={() => {
                                setEditingTemplate(null)
                              }}
                              autoFocus
                            />
                          ) : (
                            <Text strong style={{ cursor: 'pointer' }} onClick={() => handlePreview(template)}>
                              {template.name}
                            </Text>
                          )}
                          <br />
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {template.description ? (
                              <>
                                {template.description.length > 50 
                                  ? `${template.description.substring(0, 50)}...` 
                                  : template.description}
                                <br />
                              </>
                            ) : null}
                            字段数: {template.field_count} · {template.created_at 
                              ? new Date(template.created_at).toLocaleString('zh-CN')
                              : '未知时间'}
                          </Text>
                        </div>
                      </Space>
                    </Space>

                    {/* Actions */}
                    {editingTemplate?.id !== template.id && (
                      <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                        <Button
                          type="text"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={() => handlePreview(template)}
                        >
                          预览
                        </Button>
                        <Button
                          type="text"
                          size="small"
                          icon={<CopyOutlined />}
                          onClick={() => handleCopy(template.id)}
                        >
                          复制
                        </Button>
                        <Button
                          type="text"
                          size="small"
                          icon={<EditOutlined />}
                          onClick={() => setEditingTemplate({ id: template.id, name: template.name })}
                        >
                          编辑
                        </Button>
                        <Button
                          type="text"
                          size="small"
                          onClick={() => handleUse(template)}
                        >
                          使用
                        </Button>
                        <Popconfirm
                          title="确定要删除这个模板吗？"
                          onConfirm={() => handleDelete(template.id)}
                          okText="确定"
                          cancelText="取消"
                        >
                          <Button
                            type="text"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                          >
                            删除
                          </Button>
                        </Popconfirm>
                      </Space>
                    )}
                  </Space>
                </Card>
              </List.Item>
            )}
          />
        )}
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="p-4 border-t border-gray-200">
          <Pagination
            current={page}
            pageSize={pageSize}
            total={total}
            onChange={handlePageChange}
            showSizeChanger={false}
            showQuickJumper
            showTotal={(total) => `共 ${total} 条`}
            size="small"
          />
        </div>
      )}

      {/* Preview Modal */}
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
                  ? new Date(previewTemplate.created_at).toLocaleString('zh-CN')
                  : '未知时间'}</Text>
              </div>
              {previewTemplate.updated_at && (
                <div>
                  <Text strong>更新时间：</Text>
                  <Text>{new Date(previewTemplate.updated_at).toLocaleString('zh-CN')}</Text>
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
    </div>
  )
}
