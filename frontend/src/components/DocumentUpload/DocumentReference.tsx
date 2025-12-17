import { Tag, Space } from 'antd'
import { CloseOutlined, FileTextOutlined } from '@ant-design/icons'
import { Document } from '../../services/documentService'

interface DocumentReferenceProps {
  document: Document
  onRemove: (documentId: number) => void
}

export default function DocumentReference({ document, onRemove }: DocumentReferenceProps) {
  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation()
    onRemove(document.id)
  }

  return (
    <Tag
      closable
      onClose={handleRemove}
      icon={<FileTextOutlined />}
      style={{
        margin: 0,
        marginRight: '4px',
        padding: '2px 8px',
        backgroundColor: '#e6f7ff',
        borderColor: '#91d5ff',
        color: '#1890ff',
        cursor: 'default',
        display: 'inline-flex',
        alignItems: 'center',
        height: '22px',
        lineHeight: '22px',
        verticalAlign: 'middle',
      }}
    >
      @文档:{document.name}
    </Tag>
  )
}

interface DocumentReferencesProps {
  documents: Document[]
  onRemove: (documentId: number) => void
}

export function DocumentReferences({ documents, onRemove }: DocumentReferencesProps) {
  if (documents.length === 0) {
    return null
  }

  return (
    <Space wrap style={{ marginBottom: '8px' }}>
      {documents.map((doc) => (
        <DocumentReference key={doc.id} document={doc} onRemove={onRemove} />
      ))}
    </Space>
  )
}
