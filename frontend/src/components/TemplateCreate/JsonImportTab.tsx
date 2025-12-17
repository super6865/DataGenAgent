import { useState } from 'react'
import { Steps, Button, Input, Space, message, Card, Typography, Form, List, Select, Radio, Collapse, Popconfirm, Divider } from 'antd'
import { CheckOutlined, EditOutlined, DeleteOutlined, PlusOutlined, CaretRightOutlined, CaretDownOutlined } from '@ant-design/icons'
import { Editor } from '@monaco-editor/react'
import { dataTemplateService } from '../../services/dataTemplateService'
import { generateSchemaFromFields, FieldDefinition, formatFieldPath } from '../../utils/templateUtils'

const { Text } = Typography
const { Option } = Select
const { Panel } = Collapse

interface JsonImportTabProps {
  isActive?: boolean
  onChange: (data: { schema: any; field_definitions: any[] }) => void
}

export default function JsonImportTab({ isActive = true, onChange }: JsonImportTabProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [jsonString, setJsonString] = useState('')
  const [parsedData, setParsedData] = useState<{
    schema: any
    field_definitions: any[]
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [useAgent, setUseAgent] = useState(false)
  const [editableFields, setEditableFields] = useState<FieldDefinition[]>([])
  const [editingFieldIndex, setEditingFieldIndex] = useState<number | null>(null)
  const [expandedNestedFields, setExpandedNestedFields] = useState<Set<string>>(new Set())

  const steps = [
    {
      title: '粘贴JSON',
      description: '输入JSON示例'
    },
    {
      title: '编辑字段',
      description: '检查和修改字段定义'
    },
    {
      title: '完成',
      description: '确认创建'
    }
  ]

  const handleParseJson = async () => {
    if (!jsonString.trim()) {
      message.error('请输入JSON内容')
      return
    }

    // Basic JSON validation
    try {
      JSON.parse(jsonString)
    } catch (e) {
      message.error('JSON格式无效，请检查')
      return
    }

    setLoading(true)
    try {
      const response = await dataTemplateService.parseJson(jsonString, useAgent)
      if (response.success) {
        const data = response.data
        setParsedData(data)
        
        // Initialize editable fields
        setEditableFields(data.field_definitions.map((field: any) => ({
          name: field.name || '',
          type: field.type || 'string',
          description: field.description || '',
          required: field.required || false,
          constraints: field.constraints || {},
          properties: field.properties || [],
          items: field.items || undefined
        })))
        
        setCurrentStep(1)
        message.success(useAgent ? '智能解析成功' : 'JSON解析成功')
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || error.message || '解析失败')
    } finally {
      setLoading(false)
    }
  }

  const handleFieldChange = (index: number, field: Partial<FieldDefinition>) => {
    const newFields = [...editableFields]
    newFields[index] = { ...newFields[index], ...field }
    setEditableFields(newFields)
  }

  const handleAddField = () => {
    const newField: FieldDefinition = {
      name: '',
      type: 'string',
      description: '',
      required: false,
      constraints: {}
    }
    setEditableFields([...editableFields, newField])
    setEditingFieldIndex(editableFields.length)
  }

  const handleDeleteField = (index: number) => {
    const newFields = editableFields.filter((_, i) => i !== index)
    setEditableFields(newFields)
    if (editingFieldIndex === index) {
      setEditingFieldIndex(null)
    } else if (editingFieldIndex !== null && editingFieldIndex > index) {
      setEditingFieldIndex(editingFieldIndex - 1)
    }
  }

  const handleConfirm = () => {
    // Validate fields
    const errors: string[] = []
    const fieldNames = new Set<string>()
    
    editableFields.forEach((field, index) => {
      if (!field.name || field.name.trim().length === 0) {
        errors.push(`字段 ${index + 1} 的名称不能为空`)
      } else if (fieldNames.has(field.name)) {
        errors.push(`字段名称 "${field.name}" 重复`)
      } else {
        fieldNames.add(field.name)
      }
      
      if (!field.type) {
        errors.push(`字段 "${field.name || `字段 ${index + 1}`}" 必须指定类型`)
      }
    })
    
    if (errors.length > 0) {
      message.error(errors.join('; '))
      return
    }
    
    if (editableFields.length === 0) {
      message.error('至少需要有一个字段')
      return
    }

    // Only call onChange if this tab is active
    if (!isActive) {
      message.warning('请先切换到JSON导入标签页')
      return
    }
    
    // Generate schema with updated fields
    const schema = generateSchemaFromFields(editableFields)

    onChange({
      schema,
      field_definitions: editableFields
    })

    setCurrentStep(2)
    message.success('模板数据已准备就绪，可以在上方填写模板名称和描述后创建')
  }

  const handleReset = () => {
    setJsonString('')
    setParsedData(null)
    setEditableFields([])
    setEditingFieldIndex(null)
    setUseAgent(false)
    setCurrentStep(0)
  }

  const handleNestedPropertiesChange = (fieldIndex: number, properties: FieldDefinition[]) => {
    const newFields = [...editableFields]
    newFields[fieldIndex] = {
      ...newFields[fieldIndex],
      properties
    }
    setEditableFields(newFields)
  }

  const handleArrayItemsPropertiesChange = (fieldIndex: number, properties: FieldDefinition[]) => {
    const newFields = [...editableFields]
    const field = newFields[fieldIndex]
    newFields[fieldIndex] = {
      ...field,
      items: {
        ...field.items,
        properties
      }
    }
    setEditableFields(newFields)
  }

  const toggleNestedField = (fieldKey: string) => {
    const newExpanded = new Set(expandedNestedFields)
    if (newExpanded.has(fieldKey)) {
      newExpanded.delete(fieldKey)
    } else {
      newExpanded.add(fieldKey)
    }
    setExpandedNestedFields(newExpanded)
  }

  const renderNestedFields = (
    fields: FieldDefinition[],
    fieldPath: string,
    level: number = 0,
    onFieldsChange: (fields: FieldDefinition[]) => void
  ) => {
    if (!fields || fields.length === 0) {
      return (
        <div style={{ 
          padding: '8px', 
          background: '#fafafa', 
          borderRadius: '4px', 
          marginTop: '8px',
          marginLeft: level * 24,
          fontSize: '12px',
          color: '#999'
        }}>
          暂无嵌套字段
        </div>
      )
    }

    return (
      <div style={{ marginLeft: level * 24, marginTop: '8px' }}>
        {fields.map((nestedField, nestedIndex) => {
          const nestedPath = fieldPath ? `${fieldPath}.${nestedField.name}` : nestedField.name
          const nestedKey = `${fieldPath}-${nestedIndex}`
          const isExpanded = expandedNestedFields.has(nestedKey)
          const hasNestedProperties = nestedField.type === 'object' && nestedField.properties && nestedField.properties.length > 0
          const hasArrayObjectItems = nestedField.type === 'array' && nestedField.items?.type === 'object' && nestedField.items?.properties && nestedField.items.properties.length > 0

          return (
            <Card
              key={nestedIndex}
              size="small"
              style={{ 
                marginBottom: '8px',
                borderLeft: `3px solid ${level % 2 === 0 ? '#1890ff' : '#52c41a'}`
              }}
              title={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space>
                    {(hasNestedProperties || hasArrayObjectItems) && (
                      <Button
                        type="text"
                        size="small"
                        icon={isExpanded ? <CaretDownOutlined /> : <CaretRightOutlined />}
                        onClick={() => toggleNestedField(nestedKey)}
                        style={{ padding: 0, width: '20px' }}
                      />
                    )}
                    <Text strong style={{ fontSize: '13px' }}>
                      {nestedField.name || '(未命名)'}
                    </Text>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      ({nestedField.type})
                    </Text>
                    {fieldPath && (
                      <Text type="secondary" style={{ fontSize: '11px' }}>
                        {formatFieldPath(nestedPath)}
                      </Text>
                    )}
                  </Space>
                </div>
              }
            >
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                {nestedField.description && (
                  <div>
                    <Text type="secondary" style={{ fontSize: '12px' }}>描述: </Text>
                    <Text style={{ fontSize: '12px' }}>{nestedField.description}</Text>
                  </div>
                )}
                <div>
                  <Text type="secondary" style={{ fontSize: '12px' }}>必填: </Text>
                  <Text style={{ fontSize: '12px' }}>{nestedField.required ? '是' : '否'}</Text>
                </div>
              </Space>

              {/* Render nested properties for object type */}
              {hasNestedProperties && isExpanded && (
                <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px dashed #e8e8e8' }}>
                  <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: '8px' }}>
                    嵌套属性 ({nestedField.properties!.length} 个)
                  </Text>
                  {renderNestedFields(
                    nestedField.properties!,
                    nestedPath,
                    level + 1,
                    (properties) => {
                      const updatedFields = [...fields]
                      updatedFields[nestedIndex] = { ...nestedField, properties }
                      onFieldsChange(updatedFields)
                    }
                  )}
                </div>
              )}

              {/* Render nested properties for array with object items */}
              {hasArrayObjectItems && isExpanded && (
                <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px dashed #e8e8e8' }}>
                  <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: '8px' }}>
                    数组元素属性 ({nestedField.items!.properties!.length} 个)
                  </Text>
                  {renderNestedFields(
                    nestedField.items!.properties!,
                    `${nestedPath}[]`,
                    level + 1,
                    (properties) => {
                      const updatedFields = [...fields]
                      updatedFields[nestedIndex] = {
                        ...nestedField,
                        items: {
                          ...nestedField.items!,
                          properties
                        }
                      }
                      onFieldsChange(updatedFields)
                    }
                  )}
                </div>
              )}
            </Card>
          )
        })}
      </div>
    )
  }

  const renderFieldEditor = (field: FieldDefinition, index: number) => {
    const isEditing = editingFieldIndex === index
    const fieldKey = `field-${index}`
    const isExpanded = expandedNestedFields.has(fieldKey)
    const hasNestedProperties = field.type === 'object' && field.properties && field.properties.length > 0
    const hasArrayObjectItems = field.type === 'array' && field.items?.type === 'object' && field.items?.properties && field.items.properties.length > 0
    
    return (
      <Card
        key={index}
        size="small"
        style={{ marginBottom: '8px' }}
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              {(hasNestedProperties || hasArrayObjectItems) && (
                <Button
                  type="text"
                  size="small"
                  icon={isExpanded ? <CaretDownOutlined /> : <CaretRightOutlined />}
                  onClick={() => toggleNestedField(fieldKey)}
                  style={{ padding: 0, width: '20px' }}
                />
              )}
              <span>字段 {index + 1}: {field.name || '(未命名)'}</span>
            </Space>
            <Space>
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={() => setEditingFieldIndex(isEditing ? null : index)}
              >
                {isEditing ? '完成编辑' : '编辑'}
              </Button>
              <Popconfirm
                title="确定要删除这个字段吗？"
                onConfirm={() => handleDeleteField(index)}
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
          </div>
        }
      >
        {isEditing ? (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Form.Item label="字段名称" required>
              <Input
                value={field.name}
                onChange={(e) => handleFieldChange(index, { name: e.target.value })}
                placeholder="请输入字段名称"
              />
            </Form.Item>
            
            <Form.Item label="字段类型" required>
              <Select
                value={field.type}
                onChange={(value) => handleFieldChange(index, { type: value })}
                style={{ width: '100%' }}
              >
                <Option value="string">string</Option>
                <Option value="number">number</Option>
                <Option value="integer">integer</Option>
                <Option value="boolean">boolean</Option>
                <Option value="object">object</Option>
                <Option value="array">array</Option>
                <Option value="date">date</Option>
                <Option value="datetime">datetime</Option>
              </Select>
            </Form.Item>
            
            <Form.Item label="字段描述">
              <Input.TextArea
                value={field.description}
                onChange={(e) => handleFieldChange(index, { description: e.target.value })}
                placeholder="请输入字段描述"
                rows={2}
              />
            </Form.Item>
            
            <Form.Item label="是否必填">
              <Radio.Group
                value={field.required}
                onChange={(e) => handleFieldChange(index, { required: e.target.value })}
              >
                <Radio value={true}>是</Radio>
                <Radio value={false}>否</Radio>
              </Radio.Group>
            </Form.Item>
          </Space>
        ) : (
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            <div>
              <Text type="secondary">类型: </Text>
              <Text strong>{field.type}</Text>
            </div>
            {field.description && (
              <div>
                <Text type="secondary">描述: </Text>
                <Text>{field.description}</Text>
              </div>
            )}
            <div>
              <Text type="secondary">必填: </Text>
              <Text>{field.required ? '是' : '否'}</Text>
            </div>
            {hasNestedProperties && (
              <div>
                <Text type="secondary">嵌套字段: </Text>
                <Text>{field.properties!.length} 个</Text>
              </div>
            )}
            {hasArrayObjectItems && (
              <div>
                <Text type="secondary">数组元素字段: </Text>
                <Text>{field.items!.properties!.length} 个</Text>
              </div>
            )}
          </Space>
        )}

        {/* Render nested properties for object type */}
        {hasNestedProperties && isExpanded && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <div>
              <Text strong style={{ display: 'block', marginBottom: '8px' }}>
                嵌套属性 ({field.properties!.length} 个)
              </Text>
              {renderNestedFields(
                field.properties!,
                field.name,
                0,
                (properties) => handleNestedPropertiesChange(index, properties)
              )}
            </div>
          </>
        )}

        {/* Render nested properties for array with object items */}
        {hasArrayObjectItems && isExpanded && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <div>
              <Text strong style={{ display: 'block', marginBottom: '8px' }}>
                数组元素属性 ({field.items!.properties!.length} 个)
              </Text>
              {renderNestedFields(
                field.items!.properties!,
                `${field.name}[]`,
                0,
                (properties) => handleArrayItemsPropertiesChange(index, properties)
              )}
            </div>
          </>
        )}
      </Card>
    )
  }

  return (
    <div style={{ padding: '16px 0' }}>
      <Steps current={currentStep} items={steps} style={{ marginBottom: '24px' }} />

      {currentStep === 0 && (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Text strong>步骤1: 粘贴JSON示例</Text>
          </div>
          
          <div>
            <Text>解析方式: </Text>
            <Radio.Group
              value={useAgent}
              onChange={(e) => setUseAgent(e.target.value)}
              style={{ marginLeft: '8px' }}
            >
              <Radio value={false}>基础解析（快速）</Radio>
              <Radio value={true}>智能解析（AI Agent，更准确）</Radio>
            </Radio.Group>
          </div>
          
          <div style={{ border: '1px solid #d9d9d9', borderRadius: '4px', overflow: 'hidden' }}>
            <Editor
              height="400px"
              language="json"
              theme="vs"
              value={jsonString || ''}
              onChange={(value) => setJsonString(value || '')}
              options={{
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
                lineNumbers: 'on',
                formatOnPaste: true,
                formatOnType: true,
                automaticLayout: true,
                tabSize: 2,
                wordWrap: 'on'
              }}
            />
            {!jsonString && (
              <div style={{
                marginTop: '8px',
                color: '#999',
                fontSize: '12px',
                fontStyle: 'italic',
                padding: '8px'
              }}>
                提示：例如 {'{"name": "张三", "age": 25, "email": "zhangsan@example.com"}'}
              </div>
            )}
          </div>
          <Button
            type="primary"
            onClick={handleParseJson}
            loading={loading}
            disabled={!jsonString.trim()}
          >
            {useAgent ? '智能解析JSON' : '解析JSON'}
          </Button>
        </Space>
      )}

      {currentStep === 1 && editableFields.length > 0 && (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text strong>步骤2: 编辑字段定义</Text>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddField}
            >
              添加字段
            </Button>
          </div>
          
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {editableFields.map((field, index) => renderFieldEditor(field, index))}
          </div>
          
          <Space>
            <Button onClick={() => setCurrentStep(0)}>上一步</Button>
            <Button type="primary" onClick={handleConfirm}>
              确认并继续
            </Button>
          </Space>
        </Space>
      )}

      {currentStep === 2 && (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Card>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div style={{ textAlign: 'center' }}>
                <CheckOutlined style={{ fontSize: '48px', color: '#52c41a' }} />
                <div style={{ marginTop: '16px' }}>
                  <Text strong>模板数据已准备就绪</Text>
                </div>
                <div style={{ marginTop: '8px' }}>
                  <Text type="secondary">
                    请在上方填写模板名称和描述，然后点击"创建"按钮
                  </Text>
                </div>
              </div>
            </Space>
          </Card>
          <Button onClick={handleReset}>重新开始</Button>
        </Space>
      )}
    </div>
  )
}
