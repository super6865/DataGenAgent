import { useState, useCallback, useEffect } from 'react'
import { Modal, Input, List, Card, Space, Button, message, Spin, Typography } from 'antd'
import { SearchOutlined, CheckOutlined, FormOutlined, PlusOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { dataTemplateService, DataTemplate } from '../../services/dataTemplateService'

const { Text } = Typography

interface TemplateSelectModalProps {
  visible: boolean
  onCancel: () => void
  onSelect: (template: DataTemplate) => void
}

export default function TemplateSelectModal({ visible, onCancel, onSelect }: TemplateSelectModalProps) {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<DataTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)

  // Load templates list
  const loadTemplates = useCallback(async (search?: string) => {
    setLoading(true)
    try {
      const response = await dataTemplateService.getList(1, 100, search)
      if (response.success) {
        setTemplates(response.data.items)
      }
    } catch (error: any) {
      message.error('加载模板列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // Load templates when modal opens
  useEffect(() => {
    if (visible) {
      loadTemplates()
      setSearchKeyword('')
      setSelectedTemplateId(null)
    }
  }, [visible, loadTemplates])

  const handleSearch = (value: string) => {
    setSearchKeyword(value)
    loadTemplates(value)
  }

  const handleSelectTemplate = (template: DataTemplate) => {
    setSelectedTemplateId(template.id)
  }

  const handleConfirmSelection = () => {
    if (!selectedTemplateId) {
      message.warning('请先选择一个模板')
      return
    }

    const selectedTemplate = templates.find(t => t.id === selectedTemplateId)
    if (selectedTemplate) {
      onSelect(selectedTemplate)
      handleCancel()
    }
  }

  const handleCancel = () => {
    setSelectedTemplateId(null)
    setSearchKeyword('')
    onCancel()
  }

  const handleCreateNewTemplate = () => {
    // 关闭当前Modal
    handleCancel()
    // 跳转到模板库页面（模板库页面会自动打开创建Modal）
    navigate('/resource-library/templates?action=create')
  }

  return (
    <Modal
      title="选择模板"
      open={visible}
      onCancel={handleCancel}
      footer={[
        <Button key="cancel" onClick={handleCancel}>
          取消
        </Button>,
        <Button
          key="confirm"
          type="primary"
          onClick={handleConfirmSelection}
          disabled={!selectedTemplateId}
        >
          确认选择
        </Button>
      ]}
      width={600}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* Create New Template Button */}
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={handleCreateNewTemplate}
          block
          style={{ marginBottom: '8px' }}
        >
          创建新模板
        </Button>

        {/* Search */}
        <Input
          placeholder="搜索模板..."
          prefix={<SearchOutlined />}
          value={searchKeyword}
          onChange={(e) => handleSearch(e.target.value)}
          allowClear
        />

        {/* Templates List */}
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <Spin />
            </div>
          ) : templates.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
              {searchKeyword ? '未找到匹配的模板' : '暂无模板'}
            </div>
          ) : (
            <List
              dataSource={templates}
              renderItem={(template) => (
                <List.Item
                  style={{
                    padding: '12px',
                    cursor: 'pointer',
                    backgroundColor: selectedTemplateId === template.id ? '#fff7e6' : 'transparent',
                    border: selectedTemplateId === template.id ? '1px solid #fa8c16' : '1px solid #f0f0f0',
                    borderRadius: '4px',
                    marginBottom: '8px',
                  }}
                  onClick={() => handleSelectTemplate(template)}
                >
                  <Card
                    size="small"
                    style={{ width: '100%', border: 'none' }}
                    bodyStyle={{ padding: 0 }}
                  >
                    <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                      <Space>
                        <FormOutlined style={{ fontSize: '20px', color: '#fa8c16' }} />
                        <div>
                          <Text strong>{template.name}</Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {template.description || '无描述'} · 字段数: {template.field_count}
                          </Text>
                        </div>
                      </Space>
                      {selectedTemplateId === template.id && (
                        <CheckOutlined style={{ color: '#fa8c16', fontSize: '18px' }} />
                      )}
                    </Space>
                  </Card>
                </List.Item>
              )}
            />
          )}
        </div>
      </Space>
    </Modal>
  )
}
