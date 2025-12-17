import { Form, Input, Select, Switch, InputNumber, Space, Button, Typography, Divider } from 'antd'
import { FieldDefinition } from '../../utils/templateUtils'
import NestedFieldConfig from './NestedFieldConfig'

const { TextArea } = Input
const { Text } = Typography

interface FieldConfigFormProps {
  field: FieldDefinition
  onChange: (field: FieldDefinition) => void
  onNameChange: (name: string) => void
}

const FIELD_TYPES = [
  { value: 'string', label: '字符串 (string)' },
  { value: 'number', label: '数字 (number)' },
  { value: 'integer', label: '整数 (integer)' },
  { value: 'boolean', label: '布尔值 (boolean)' },
  { value: 'array', label: '数组 (array)' },
  { value: 'object', label: '对象 (object)' },
  { value: 'date', label: '日期 (date)' },
  { value: 'datetime', label: '日期时间 (datetime)' }
]

export default function FieldConfigForm({ field, onChange, onNameChange }: FieldConfigFormProps) {
  const handleFieldChange = (key: string, value: any) => {
    const updatedField = { ...field, [key]: value }
    
    // Reset constraints and nested properties when type changes
    if (key === 'type' && value !== field.type) {
      updatedField.constraints = {}
      // Clear nested properties when changing from object/array
      if (field.type === 'object') {
        updatedField.properties = undefined
      }
      if (field.type === 'array') {
        updatedField.items = undefined
      }
      // Initialize nested structure for new types
      if (value === 'object') {
        updatedField.properties = []
      }
      if (value === 'array') {
        updatedField.items = { type: 'string' }
      }
    }
    
    onChange(updatedField)
  }

  const handleConstraintChange = (key: string, value: any) => {
    const constraints = { ...(field.constraints || {}), [key]: value }
    onChange({ ...field, constraints })
  }

  const handleRemoveConstraint = (key: string) => {
    const constraints = { ...(field.constraints || {}) }
    delete constraints[key]
    onChange({ ...field, constraints })
  }

  const renderStringConstraints = () => {
    return (
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <div>
          <Text strong>字符串约束：</Text>
        </div>
        <Space wrap>
          <InputNumber
            placeholder="最小长度"
            min={0}
            value={field.constraints?.minLength}
            onChange={(value) => handleConstraintChange('minLength', value)}
            style={{ width: 120 }}
          />
          <InputNumber
            placeholder="最大长度"
            min={0}
            value={field.constraints?.maxLength}
            onChange={(value) => handleConstraintChange('maxLength', value)}
            style={{ width: 120 }}
          />
          <Input
            placeholder="正则表达式"
            value={field.constraints?.pattern}
            onChange={(e) => handleConstraintChange('pattern', e.target.value)}
            style={{ width: 200 }}
          />
        </Space>
        {field.constraints?.pattern && (
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleRemoveConstraint('pattern')}
          >
            移除正则表达式
          </Button>
        )}
      </Space>
    )
  }

  const renderNumberConstraints = () => {
    return (
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <div>
          <Text strong>数值约束：</Text>
        </div>
        <Space wrap>
          <InputNumber
            placeholder="最小值"
            value={field.constraints?.minimum}
            onChange={(value) => handleConstraintChange('minimum', value)}
            style={{ width: 120 }}
          />
          <InputNumber
            placeholder="最大值"
            value={field.constraints?.maximum}
            onChange={(value) => handleConstraintChange('maximum', value)}
            style={{ width: 120 }}
          />
          <InputNumber
            placeholder="步长"
            min={0}
            value={field.constraints?.multipleOf}
            onChange={(value) => handleConstraintChange('multipleOf', value)}
            style={{ width: 120 }}
          />
        </Space>
      </Space>
    )
  }

  const renderArrayConstraints = () => {
    return (
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <div>
          <Text strong>数组约束：</Text>
        </div>
        <Space wrap>
          <InputNumber
            placeholder="最小元素数"
            min={0}
            value={field.constraints?.minItems}
            onChange={(value) => handleConstraintChange('minItems', value)}
            style={{ width: 120 }}
          />
          <InputNumber
            placeholder="最大元素数"
            min={0}
            value={field.constraints?.maxItems}
            onChange={(value) => handleConstraintChange('maxItems', value)}
            style={{ width: 120 }}
          />
        </Space>
      </Space>
    )
  }

  const renderArrayItemType = () => {
    const arrayItemTypes = [
      { value: 'string', label: '字符串' },
      { value: 'number', label: '数字' },
      { value: 'integer', label: '整数' },
      { value: 'boolean', label: '布尔值' },
      { value: 'object', label: '对象' },
      { value: 'array', label: '数组' }
    ]

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <div>
          <Text strong>数组元素类型：</Text>
        </div>
        <Select
          value={field.items?.type || 'string'}
          onChange={(value) => {
            const newItems = {
              type: value,
              ...(value === 'object' ? { properties: [] } : {})
            }
            onChange({ ...field, items: newItems })
          }}
          style={{ width: '100%' }}
        >
          {arrayItemTypes.map(type => (
            <Select.Option key={type.value} value={type.value}>
              {type.label}
            </Select.Option>
          ))}
        </Select>
      </Space>
    )
  }

  const handleNestedPropertiesChange = (properties: FieldDefinition[]) => {
    onChange({ ...field, properties })
  }

  const handleArrayItemsPropertiesChange = (properties: FieldDefinition[]) => {
    onChange({
      ...field,
      items: {
        ...field.items!,
        properties
      }
    })
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Form.Item label="字段名称" required>
        <Input
          value={field.name}
          onChange={(e) => {
            onNameChange(e.target.value)
          }}
          placeholder="请输入字段名称"
        />
      </Form.Item>

      <Form.Item label="字段类型" required>
        <Select
          value={field.type}
          onChange={(value) => handleFieldChange('type', value)}
          style={{ width: '100%' }}
        >
          {FIELD_TYPES.map(type => (
            <Select.Option key={type.value} value={type.value}>
              {type.label}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item label="字段描述">
        <TextArea
          value={field.description}
          onChange={(e) => handleFieldChange('description', e.target.value)}
          placeholder="请输入字段描述（可选）"
          rows={2}
        />
      </Form.Item>

      <Form.Item label="是否必填">
        <Switch
          checked={field.required}
          onChange={(checked) => handleFieldChange('required', checked)}
        />
      </Form.Item>

      <Form.Item label="默认值">
        <Input
          value={field.default !== undefined ? String(field.default) : ''}
          onChange={(e) => {
            const value = e.target.value
            // Try to parse as appropriate type
            let parsedValue: any = value
            if (field.type === 'number' || field.type === 'integer') {
              parsedValue = value ? Number(value) : undefined
            } else if (field.type === 'boolean') {
              parsedValue = value === 'true'
            }
            handleFieldChange('default', parsedValue)
          }}
          placeholder="请输入默认值（可选）"
        />
      </Form.Item>

      {/* Constraints based on type */}
      {field.type === 'string' && renderStringConstraints()}
      {(field.type === 'number' || field.type === 'integer') && renderNumberConstraints()}
      {field.type === 'array' && (
        <>
          {renderArrayItemType()}
          {renderArrayConstraints()}
        </>
      )}

      {/* Nested properties for object type */}
      {field.type === 'object' && (
        <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #f0f0f0' }}>
          <Text strong style={{ display: 'block', marginBottom: '8px' }}>
            嵌套属性
          </Text>
          <NestedFieldConfig
            fields={field.properties || []}
            onChange={handleNestedPropertiesChange}
            fieldPath={field.name}
            level={0}
            maxVisibleLevel={3}
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
            onChange={handleArrayItemsPropertiesChange}
            fieldPath={`${field.name}[]`}
            level={0}
            maxVisibleLevel={3}
          />
        </div>
      )}
    </Space>
  )
}
