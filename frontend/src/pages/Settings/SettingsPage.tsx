import { useState, useEffect, useMemo } from 'react'
import { Table, Button, Space, Modal, Form, Input, InputNumber, Switch, message, Popconfirm, Tag, Pagination } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, StarOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { modelConfigService, ModelConfig, ModelConfigCreate, ModelConfigUpdate } from '../../services/modelConfigService'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const MODEL_TYPES = [
  { label: 'OpenAI', value: 'openai' },
  { label: '通义千问', value: 'qwen' },
  { label: 'DeepSeek', value: 'deepseek' },
]

export default function SettingsPage() {
  const [configs, setConfigs] = useState<ModelConfig[]>([])
  const [allConfigs, setAllConfigs] = useState<ModelConfig[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingConfig, setEditingConfig] = useState<ModelConfig | null>(null)
  const [form] = Form.useForm()
  const [searchKeyword, setSearchKeyword] = useState('')
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  })

  useEffect(() => {
    loadConfigs()
  }, [pagination.current, pagination.pageSize])

  // 前端过滤搜索结果
  useEffect(() => {
    if (!searchKeyword.trim()) {
      setConfigs(allConfigs)
      setPagination((prev) => ({ ...prev, total: allConfigs.length, current: 1 }))
    } else {
      const filtered = allConfigs.filter((config) =>
        config.config_name.toLowerCase().includes(searchKeyword.toLowerCase()) ||
        config.model_type.toLowerCase().includes(searchKeyword.toLowerCase()) ||
        config.model_version.toLowerCase().includes(searchKeyword.toLowerCase())
      )
      setConfigs(filtered)
      setPagination((prev) => ({ ...prev, total: filtered.length, current: 1 }))
    }
  }, [searchKeyword, allConfigs])

  const loadConfigs = async () => {
    setLoading(true)
    try {
      // 加载所有配置（用于前端搜索）
      const response = await modelConfigService.getAll(false, 0, 1000)
      if (response.success) {
        setAllConfigs(response.data)
        // 如果有搜索关键词，会通过useEffect过滤
        if (!searchKeyword.trim()) {
          setConfigs(response.data)
          setPagination((prev) => ({ ...prev, total: response.total }))
        }
      }
    } catch (error) {
      message.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (value: string) => {
    setSearchKeyword(value)
  }

  const handleCreate = () => {
    setEditingConfig(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (config: ModelConfig) => {
    setEditingConfig(config)
    form.setFieldsValue({
      config_name: config.config_name,
      model_type: config.model_type,
      model_version: config.model_version,
      api_base: config.api_base,
      temperature: config.temperature,
      max_tokens: config.max_tokens,
      timeout: config.timeout,
      is_enabled: config.is_enabled,
      is_default: config.is_default,
    })
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      const response = await modelConfigService.delete(id)
      if (response.success) {
        message.success('删除成功')
        loadConfigs()
      } else {
        throw new Error(response.message)
      }
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }

  const handleSetDefault = async (id: number) => {
    try {
      const response = await modelConfigService.setDefault(id)
      if (response.success) {
        message.success('设置默认成功')
        loadConfigs()
      } else {
        throw new Error(response.message)
      }
    } catch (error: any) {
      message.error(error.message || '设置失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      
      if (editingConfig) {
        const updateData: ModelConfigUpdate = { ...values }
        if (!values.api_key) {
          delete updateData.api_key
        }
        const response = await modelConfigService.update(editingConfig.id, updateData)
        if (response.success) {
          message.success('更新成功')
        } else {
          throw new Error(response.message)
        }
      } else {
        const createData: ModelConfigCreate = {
          ...values,
          api_key: values.api_key,
        }
        const response = await modelConfigService.create(createData)
        if (response.success) {
          message.success('创建成功')
        } else {
          throw new Error(response.message)
        }
      }
      
      setModalVisible(false)
      form.resetFields()
      loadConfigs()
    } catch (error: any) {
      if (error.errorFields) {
        return
      }
      message.error(error.message || '操作失败')
    }
  }

  const columns: ColumnsType<ModelConfig> = [
    {
      title: '配置名称',
      dataIndex: 'config_name',
      key: 'config_name',
    },
    {
      title: '模型类型',
      dataIndex: 'model_type',
      key: 'model_type',
      width: 120,
    },
    {
      title: '模型版本',
      dataIndex: 'model_version',
      key: 'model_version',
      width: 150,
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_: any, record: ModelConfig) => (
        <Space>
          {record.is_default && <Tag color="gold" icon={<StarOutlined />}>默认</Tag>}
          {record.is_enabled ? <Tag color="success">启用</Tag> : <Tag>禁用</Tag>}
        </Space>
      ),
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
      render: (_: any, record: ModelConfig) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          {!record.is_default && (
            <Button
              type="link"
              size="small"
              onClick={() => handleSetDefault(record.id)}
            >
              设为默认
            </Button>
          )}
          <Popconfirm
            title="确定要删除这个配置吗？"
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

  // 分页显示的数据
  const paginatedConfigs = useMemo(() => {
    const start = (pagination.current - 1) * pagination.pageSize
    const end = start + pagination.pageSize
    return configs.slice(start, end)
  }, [configs, pagination.current, pagination.pageSize])

  return (
    <div className="pt-2 pb-3 h-full flex flex-col">
      {/* 第一层：标题 */}
      <div className="flex items-center justify-between py-4 px-6">
        <div className="text-[20px] font-medium leading-6 coz-fg-plus">模型配置</div>
      </div>

      {/* 第二层：搜索框和操作按钮 */}
      <div className="box-border coz-fg-secondary pt-1 pb-3 px-6">
        <div className="flex items-center justify-between gap-4">
          <Space size="middle">
            <Input
              placeholder="搜索配置名称、模型类型或版本..."
              prefix={<SearchOutlined />}
              value={searchKeyword}
              onChange={(e) => handleSearch(e.target.value)}
              allowClear
              style={{ width: 300 }}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={loadConfigs}
            >
              刷新
            </Button>
          </Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建配置
          </Button>
        </div>
      </div>

      {/* 第三层：内容区 */}
      <div className="flex-1 overflow-hidden px-6 flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <Table
            columns={columns}
            dataSource={paginatedConfigs}
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
        title={editingConfig ? '编辑配置' : '新建配置'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
        }}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="config_name"
            label="配置名称"
            rules={[{ required: true, message: '请输入配置名称' }]}
          >
            <Input placeholder="请输入配置名称" />
          </Form.Item>
          <Form.Item
            name="model_type"
            label="模型类型"
            rules={[{ required: true, message: '请选择模型类型' }]}
          >
            <Input placeholder="openai, qwen, deepseek" />
          </Form.Item>
          <Form.Item
            name="model_version"
            label="模型版本"
            rules={[{ required: true, message: '请输入模型版本' }]}
          >
            <Input placeholder="例如: gpt-4, qwen-plus" />
          </Form.Item>
          <Form.Item
            name="api_key"
            label="API Key"
            rules={editingConfig ? [] : [{ required: true, message: '请输入API Key' }]}
          >
            <Input.Password placeholder="请输入API Key" />
          </Form.Item>
          <Form.Item name="api_base" label="API Base URL">
            <Input placeholder="例如: https://api.openai.com/v1" />
          </Form.Item>
          <Form.Item name="temperature" label="Temperature">
            <InputNumber min={0} max={2} step={0.1} placeholder="0.7" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="max_tokens" label="Max Tokens">
            <InputNumber min={1} placeholder="2000" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="timeout" label="超时时间（秒）">
            <InputNumber min={1} placeholder="120" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="is_enabled" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          <Form.Item name="is_default" valuePropName="checked" initialValue={false}>
            <Switch checkedChildren="设为默认" unCheckedChildren="非默认" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
