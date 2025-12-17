import { useState } from 'react'
import { Collapse, Button, Space, Card, Typography, message } from 'antd'
import { PlusOutlined, DeleteOutlined, CopyOutlined } from '@ant-design/icons'
import FieldConfigForm from './FieldConfigForm'
import { FieldDefinition, formatFieldPath } from '../../utils/templateUtils'

const { Panel } = Collapse
const { Text } = Typography

interface NestedFieldConfigProps {
  fields: FieldDefinition[]
  onChange: (fields: FieldDefinition[]) => void
  fieldPath?: string
  level?: number
  maxVisibleLevel?: number
}

export default function NestedFieldConfig({
  fields,
  onChange,
  fieldPath = '',
  level = 0,
  maxVisibleLevel = 3
}: NestedFieldConfigProps) {
  const [activeKeys, setActiveKeys] = useState<string[]>([])

  const handleAddField = () => {
    const newField: FieldDefinition = {
      name: '',
      type: 'string',
      description: '',
      required: false,
      constraints: {}
    }
    onChange([...fields, newField])
  }

  const handleDeleteField = (index: number) => {
    const newFields = fields.filter((_, i) => i !== index)
    onChange(newFields)
  }

  const handleCopyField = (index: number) => {
    const field = fields[index]
    const newField = { ...field, name: `${field.name}_copy` }
    const newFields = [...fields]
    newFields.splice(index + 1, 0, newField)
    onChange(newFields)
  }

  const handleFieldChange = (index: number, field: FieldDefinition) => {
    const newFields = [...fields]
    newFields[index] = field
    onChange(newFields)
  }

  const handleFieldNameChange = (index: number, name: string) => {
    const duplicate = fields.some((f, i) => i !== index && f.name === name)
    if (duplicate) {
      message.warning('字段名称不能重复')
      return
    }
    const newFields = [...fields]
    newFields[index].name = name
    onChange(newFields)
  }

  const handleNestedPropertiesChange = (index: number, properties: FieldDefinition[]) => {
    const newFields = [...fields]
    newFields[index] = {
      ...newFields[index],
      properties
    }
    onChange(newFields)
  }

  const handleArrayItemsChange = (index: number, items: { type: string; properties?: FieldDefinition[] }) => {
    const newFields = [...fields]
    newFields[index] = {
      ...newFields[index],
      items
    }
    onChange(newFields)
  }

  const shouldCollapse = level >= maxVisibleLevel

  if (fields.length === 0) {
    return (
      <div style={{ padding: '12px', background: '#fafafa', borderRadius: '4px', marginTop: '8px' }}>
        <div style={{ textAlign: 'center', color: '#999', marginBottom: '8px' }}>
          暂无嵌套字段
        </div>
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={handleAddField}
          size="small"
          block
        >
          添加字段
        </Button>
      </div>
    )
  }

  const content = (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {fields.map((field, index) => {
        const currentPath = fieldPath ? `${fieldPath}.${field.name}` : field.name
        const hasNestedProperties = field.type === 'object' && field.properties
        const hasArrayObjectItems = field.type === 'array' && field.items?.type === 'object' && field.items?.properties

        return (
          <Card
            key={index}
            size="small"
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>
                  {field.name || '(未命名)'}
                  {fieldPath && (
                    <Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>
                      ({formatFieldPath(currentPath)})
                    </Text>
                  )}
                </span>
                <Space>
                  <Button
                    type="text"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => handleCopyField(index)}
                  >
                    复制
                  </Button>
                  <Button
                    type="text"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleDeleteField(index)}
                  >
                    删除
                  </Button>
                </Space>
              </div>
            }
            style={{ marginBottom: '8px' }}
          >
            <FieldConfigForm
              field={field}
              onChange={(updatedField) => handleFieldChange(index, updatedField)}
              onNameChange={(name) => handleFieldNameChange(index, name)}
            />

            {/* Nested properties for object type */}
            {field.type === 'object' && (
              <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #f0f0f0' }}>
                <Text strong style={{ display: 'block', marginBottom: '8px' }}>
                  嵌套属性
                </Text>
                <NestedFieldConfig
                  fields={field.properties || []}
                  onChange={(properties) => handleNestedPropertiesChange(index, properties)}
                  fieldPath={currentPath}
                  level={level + 1}
                  maxVisibleLevel={maxVisibleLevel}
                />
              </div>
            )}

            {/* Nested properties for array with object items */}
            {field.type === 'array' && field.items?.type === 'object' && (
              <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #f0f0f0' }}>
                <Text strong style={{ display: 'block', marginBottom: '8px' }}>
                  数组元素属性
                </Text>
                <NestedFieldConfig
                  fields={field.items.properties || []}
                  onChange={(properties) => {
                    handleArrayItemsChange(index, {
                      ...field.items!,
                      properties
                    })
                  }}
                  fieldPath={`${currentPath}[]`}
                  level={level + 1}
                  maxVisibleLevel={maxVisibleLevel}
                />
              </div>
            )}
          </Card>
        )
      })}

      <Button
        type="dashed"
        icon={<PlusOutlined />}
        onClick={handleAddField}
        block
      >
        添加字段
      </Button>
    </Space>
  )

  if (shouldCollapse) {
    return (
      <Collapse
        activeKey={activeKeys}
        onChange={setActiveKeys}
        style={{ marginTop: '8px' }}
      >
        <Panel
          header={
            <Text strong>
              {fieldPath ? `嵌套字段 (${formatFieldPath(fieldPath)})` : '嵌套字段'} ({fields.length} 个)
            </Text>
          }
          key="nested"
        >
          {content}
        </Panel>
      </Collapse>
    )
  }

  return <div style={{ marginTop: '8px' }}>{content}</div>
}
