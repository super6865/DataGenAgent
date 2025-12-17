import { useState, useEffect } from 'react'
import { Modal, Tabs, Form, Input, Button, message } from 'antd'
import { dataTemplateService, TemplateCreateRequest } from '../../services/dataTemplateService'
import FormConfigTab from './FormConfigTab'
import JsonImportTab from './JsonImportTab'
import { validateTemplateData } from '../../utils/templateUtils'

const { TextArea } = Input

interface TemplateCreateModalProps {
  visible: boolean
  onCancel: () => void
  onSuccess: () => void
  template?: any // For editing mode
}

export default function TemplateCreateModal({
  visible,
  onCancel,
  onSuccess,
  template
}: TemplateCreateModalProps) {
  const [form] = Form.useForm()
  const [activeTab, setActiveTab] = useState('form')
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState<{
    schema: any
    field_definitions: any[]
  } | null>(null)
  const [dataSource, setDataSource] = useState<'form' | 'json' | null>(null) // Track data source

  const isEditMode = !!template

  useEffect(() => {
    if (visible) {
      if (isEditMode && template) {
        // Pre-fill form for editing
        form.setFieldsValue({
          name: template.name,
          description: template.description
        })
        setFormData({
          schema: template.schema,
          field_definitions: template.field_definitions
        })
        // In edit mode, default to form config source
        setDataSource('form')
      } else {
        // Reset form for creating
        form.resetFields()
        setFormData(null)
        setDataSource(null)
      }
    }
  }, [visible, template, isEditMode, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      
      // Different validation based on active tab and data source
      if (activeTab === 'json') {
        // For JSON import, data must come from JSON import tab
        if (dataSource !== 'json') {
          message.error('请先在JSON导入标签页中解析JSON并确认字段定义')
          return
        }
        if (!formData || !formData.schema || !formData.field_definitions) {
          message.error('请先在JSON导入标签页中解析JSON并确认字段定义')
          return
        }
        if (!Array.isArray(formData.field_definitions) || formData.field_definitions.length === 0) {
          message.error('请先在JSON导入标签页中解析JSON，至少需要一个字段')
          return
        }
      } else {
        // For form config, data must come from form config tab
        if (dataSource !== 'form') {
          message.error('请先在表单配置标签页中添加至少一个字段')
          return
        }
        if (!formData || !formData.schema || !formData.field_definitions) {
          message.error('请先在表单配置标签页中添加至少一个字段')
          return
        }
        if (!Array.isArray(formData.field_definitions) || formData.field_definitions.length === 0) {
          message.error('请先在表单配置标签页中添加至少一个字段')
          return
        }
      }

      // Ensure field_definitions is an array
      let fieldDefinitions = formData.field_definitions
      if (!Array.isArray(fieldDefinitions)) {
        console.warn('field_definitions is not an array, attempting to convert:', typeof fieldDefinitions, fieldDefinitions)
        
        // Try to convert if it's a string (JSON string)
        if (typeof fieldDefinitions === 'string') {
          try {
            fieldDefinitions = JSON.parse(fieldDefinitions)
          } catch (e) {
            message.error('字段定义格式错误，无法解析')
            return
          }
        }
        
        // If still not an array, try to wrap it
        if (!Array.isArray(fieldDefinitions)) {
          if (fieldDefinitions && typeof fieldDefinitions === 'object') {
            // If it's an object, try to convert to array
            fieldDefinitions = Object.values(fieldDefinitions)
          } else {
            message.error('字段定义必须是数组格式')
            return
          }
        }
      }

      // Ensure schema is an object
      let schema = formData.schema
      if (!schema || typeof schema !== 'object' || Array.isArray(schema)) {
        message.error('Schema必须是有效的对象')
        return
      }

      // Validate template data
      const validation = validateTemplateData({
        name: values.name,
        description: values.description,
        schema: schema,
        field_definitions: fieldDefinitions
      })

      if (!validation.valid) {
        message.error(validation.errors.join('; '))
        return
      }

      setLoading(true)

      const request: TemplateCreateRequest = {
        name: values.name,
        description: values.description,
        schema: schema,
        field_definitions: fieldDefinitions,
        example_data: null
      }

      if (isEditMode) {
        // Update template
        await dataTemplateService.update(template.id, request)
        message.success('模板更新成功')
      } else {
        // Create template
        await dataTemplateService.create(request)
        message.success('模板创建成功')
      }

      onSuccess()
      handleCancel()
    } catch (error: any) {
      message.error(error.message || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    form.resetFields()
    setFormData(null)
    setDataSource(null)
    setActiveTab('form')
    onCancel()
  }

  const handleFormDataChange = (data: { schema: any; field_definitions: any[] }, source: 'form' | 'json') => {
    // Only update if the data source matches the current active tab
    // This prevents non-active tabs from updating the data
    if (source !== activeTab) {
      return // Ignore updates from non-active tabs
    }
    
    // Update formData and track data source based on current active tab
    if (data && data.field_definitions && Array.isArray(data.field_definitions)) {
      if (activeTab === 'json') {
        // JSON import: only set if there are fields (user has parsed and confirmed)
        if (data.field_definitions.length > 0) {
          setFormData(data)
          setDataSource('json')
        }
      } else {
        // Form config: update if there are fields
        if (data.field_definitions.length > 0) {
          setFormData(data)
          setDataSource('form')
        } else {
          // If no fields, clear data source but keep formData for tracking
          setFormData(data)
          setDataSource(null)
        }
      }
    }
  }

  const handleTabChange = (key: string) => {
    setActiveTab(key)
    // When switching tabs, clear data if source doesn't match
    if (key === 'json') {
      // Switching to JSON import: clear form config data
      if (dataSource === 'form') {
        setFormData(null)
        setDataSource(null)
      }
    } else {
      // Switching to form config: clear JSON import data
      if (dataSource === 'json') {
        setFormData(null)
        setDataSource(null)
      }
    }
  }

  return (
    <Modal
      title={isEditMode ? '编辑模板' : '创建模板'}
      open={visible}
      onCancel={handleCancel}
      footer={[
        <Button key="cancel" onClick={handleCancel}>
          取消
        </Button>,
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          {isEditMode ? '更新' : '创建'}
        </Button>
      ]}
      width={900}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          name: '',
          description: ''
        }}
      >
        <Form.Item
          name="name"
          label="模板名称"
          rules={[
            { required: true, message: '请输入模板名称' },
            { max: 50, message: '模板名称不能超过50个字符' }
          ]}
        >
          <Input placeholder="请输入模板名称（1-50字符）" />
        </Form.Item>

        <Form.Item
          name="description"
          label="模板描述"
          rules={[{ max: 200, message: '模板描述不能超过200个字符' }]}
        >
          <TextArea
            placeholder="请输入模板描述（可选，最多200字符）"
            rows={2}
            showCount
            maxLength={200}
          />
        </Form.Item>

        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={[
            {
              key: 'form',
              label: '表单配置',
              children: (
                <FormConfigTab
                  initialData={isEditMode ? {
                    schema: template?.schema,
                    field_definitions: template?.field_definitions
                  } : undefined}
                  isActive={activeTab === 'form'}
                  onChange={(data) => handleFormDataChange(data, 'form')}
                />
              )
            },
            {
              key: 'json',
              label: 'JSON导入',
              children: (
                <JsonImportTab
                  isActive={activeTab === 'json'}
                  onChange={(data) => handleFormDataChange(data, 'json')}
                />
              )
            }
          ]}
        />
      </Form>
    </Modal>
  )
}
