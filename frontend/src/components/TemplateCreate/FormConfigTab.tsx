import { useState, useEffect } from 'react'
import { Button, Space, Card, Typography, message } from 'antd'
import { PlusOutlined, CopyOutlined, DragOutlined } from '@ant-design/icons'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import FieldConfigForm from './FieldConfigForm'
import { generateSchemaFromFields, FieldDefinition } from '../../utils/templateUtils'

const { Title } = Typography

interface FormConfigTabProps {
  initialData?: {
    schema?: any
    field_definitions?: any[]
  }
  isActive?: boolean
  onChange: (data: { schema: any; field_definitions: any[] }) => void
}

interface SortableFieldItemProps {
  field: FieldDefinition
  index: number
  fieldId: string
  onFieldChange: (field: FieldDefinition) => void
  onFieldNameChange: (name: string) => void
  onDelete: () => void
  onCopy: () => void
}

function SortableFieldItem({
  field,
  index,
  fieldId,
  onFieldChange,
  onFieldNameChange,
  onDelete,
  onCopy
}: SortableFieldItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: fieldId })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1
  }

  return (
    <div ref={setNodeRef} style={style}>
      <Card
        size="small"
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <div
                {...attributes}
                {...listeners}
                style={{
                  cursor: 'grab',
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '4px',
                  marginRight: '8px'
                }}
              >
                <DragOutlined style={{ color: '#999' }} />
              </div>
              <span>字段 {index + 1}: {field.name || '(未命名)'}</span>
            </Space>
            <Space>
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={onCopy}
              >
                复制
              </Button>
              <Button
                type="text"
                size="small"
                danger
                onClick={onDelete}
              >
                删除
              </Button>
            </Space>
          </div>
        }
        style={{
          marginBottom: '8px',
          border: isDragging ? '2px dashed #1890ff' : undefined
        }}
      >
        <FieldConfigForm
          field={field}
          onChange={onFieldChange}
          onNameChange={onFieldNameChange}
        />
      </Card>
    </div>
  )
}

export default function FormConfigTab({ initialData, isActive = true, onChange }: FormConfigTabProps) {
  const [fields, setFields] = useState<FieldDefinition[]>(
    initialData?.field_definitions || []
  )

  // Generate stable ID for field based on index
  // Using index as part of ID since fields array order matters
  const getFieldId = (index: number) => {
    return `field-${index}`
  }

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates
    })
  )

  useEffect(() => {
    // Only notify parent if this tab is active
    if (!isActive) {
      return
    }
    
    // Generate schema from fields and notify parent
    // Only notify if there are fields or if initialData was provided (edit mode)
    if (fields.length > 0 || initialData) {
      const schema = generateSchemaFromFields(fields)
      onChange({
        schema,
        field_definitions: fields
      })
    } else {
      // Clear formData when no fields
      onChange({
        schema: { type: 'object', properties: {}, required: [] },
        field_definitions: []
      })
    }
  }, [fields, onChange, initialData, isActive])

  const handleAddField = () => {
    const newField: FieldDefinition = {
      name: '',
      type: 'string',
      description: '',
      required: false,
      constraints: {}
    }
    setFields([...fields, newField])
  }

  const handleDeleteField = (index: number) => {
    const newFields = fields.filter((_, i) => i !== index)
    setFields(newFields)
  }

  const handleCopyField = (index: number) => {
    const field = fields[index]
    const newField = { ...field, name: `${field.name}_copy` }
    const newFields = [...fields]
    newFields.splice(index + 1, 0, newField)
    setFields(newFields)
  }

  const handleFieldChange = (index: number, field: FieldDefinition) => {
    const newFields = [...fields]
    newFields[index] = field
    setFields(newFields)
  }

  const handleFieldNameChange = (index: number, name: string) => {
    // Check for duplicate names
    const duplicate = fields.some((f, i) => i !== index && f.name === name)
    if (duplicate) {
      message.warning('字段名称不能重复')
      return
    }
    const newFields = [...fields]
    newFields[index].name = name
    setFields(newFields)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      setFields((items) => {
        const oldIndex = parseInt(active.id.toString().replace('field-', ''))
        const newIndex = parseInt(over.id.toString().replace('field-', ''))

        if (!isNaN(oldIndex) && !isNaN(newIndex)) {
          return arrayMove(items, oldIndex, newIndex)
        }
        return items
      })
    }
  }

  const schema = generateSchemaFromFields(fields)

  return (
    <div style={{ padding: '16px 0' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Fields List */}
        <div>
          <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={5} style={{ margin: 0 }}>字段列表</Title>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddField}>
              添加字段
            </Button>
          </div>

          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {fields.length === 0 ? (
              <Card>
                <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                  暂无字段，点击"添加字段"开始配置
                </div>
              </Card>
            ) : (
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={fields.map((_, index) => getFieldId(index))}
                  strategy={verticalListSortingStrategy}
                >
                  {fields.map((field, index) => (
                    <SortableFieldItem
                      key={getFieldId(index)}
                      field={field}
                      index={index}
                      fieldId={getFieldId(index)}
                      onFieldChange={(updatedField) => handleFieldChange(index, updatedField)}
                      onFieldNameChange={(name) => handleFieldNameChange(index, name)}
                      onDelete={() => handleDeleteField(index)}
                      onCopy={() => handleCopyField(index)}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            )}
          </Space>
        </div>

        {/* JSON Schema Preview */}
        <div>
          <Title level={5}>JSON Schema 预览</Title>
          <Card>
            <div style={{ maxHeight: '300px', overflow: 'auto' }}>
              {fields.length > 0 ? (
                <pre style={{
                  background: '#f5f5f5',
                  padding: '12px',
                  borderRadius: '4px',
                  margin: 0,
                  fontSize: '12px',
                  lineHeight: '1.5'
                }}>
                  {JSON.stringify(schema, null, 2)}
                </pre>
              ) : (
                <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                  添加字段后，将显示JSON Schema预览
                </div>
              )}
            </div>
          </Card>
        </div>
      </Space>
    </div>
  )
}
