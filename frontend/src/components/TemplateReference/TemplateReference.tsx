import { Tag, Space } from 'antd'
import { CloseOutlined, FormOutlined } from '@ant-design/icons'
import { DataTemplate } from '../../services/dataTemplateService'

interface TemplateReferenceProps {
  template: DataTemplate
  onRemove: (templateId: number) => void
}

export default function TemplateReference({ template, onRemove }: TemplateReferenceProps) {
  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation()
    onRemove(template.id)
  }

  return (
    <Tag
      closable
      onClose={handleRemove}
      icon={<FormOutlined />}
      style={{
        margin: 0,
        marginRight: '4px',
        padding: '2px 8px',
        backgroundColor: '#fff7e6',
        borderColor: '#ffd591',
        color: '#fa8c16',
        cursor: 'default',
        display: 'inline-flex',
        alignItems: 'center',
        height: '22px',
        lineHeight: '22px',
        verticalAlign: 'middle',
      }}
    >
      @模板:{template.name}
    </Tag>
  )
}

interface TemplateReferencesProps {
  templates: DataTemplate[]
  onRemove: (templateId: number) => void
}

export function TemplateReferences({ templates, onRemove }: TemplateReferencesProps) {
  if (templates.length === 0) {
    return null
  }

  return (
    <Space wrap style={{ marginBottom: '8px' }}>
      {templates.map((template) => (
        <TemplateReference key={template.id} template={template} onRemove={onRemove} />
      ))}
    </Space>
  )
}
