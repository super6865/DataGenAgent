import { useState, useEffect, useCallback } from 'react'
import { Input, List, Card, Space, Typography, Button, Popconfirm, message, Pagination, Tag, Modal } from 'antd'
import { SearchOutlined, FileTextOutlined, DeleteOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons'
import { documentService, Document } from '../../services/documentService'

const { Text } = Typography

const PARSE_STATUS_COLORS: Record<string, string> = {
  success: 'green',
  parsing: 'orange',
  failed: 'red',
  pending: 'default',
}

const PARSE_STATUS_LABELS: Record<string, string> = {
  success: '已解析',
  parsing: '解析中',
  failed: '解析失败',
  pending: '待解析',
}

export default function DocumentList() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewDocument, setPreviewDocument] = useState<Document | null>(null)
  const [editingDoc, setEditingDoc] = useState<{ id: number; name: string } | null>(null)

  // Load documents
  const loadDocuments = useCallback(async (currentPage: number = 1, keyword?: string) => {
    setLoading(true)
    try {
      const response = await documentService.getList(currentPage, pageSize, keyword)
      if (response.success) {
        setDocuments(response.data.items)
        setTotal(response.data.total)
      }
    } catch (error: any) {
      message.error('加载文档列表失败')
    } finally {
      setLoading(false)
    }
  }, [pageSize])

  // Initial load
  useEffect(() => {
    loadDocuments(page, searchKeyword)
  }, [page, searchKeyword, loadDocuments])

  // Handle search
  const handleSearch = (value: string) => {
    setSearchKeyword(value)
    setPage(1) // Reset to first page when searching
  }

  // Handle delete
  const handleDelete = async (documentId: number) => {
    try {
      const response = await documentService.delete(documentId)
      if (response.success) {
        message.success('删除成功')
        loadDocuments(page, searchKeyword)
      }
    } catch (error: any) {
      message.error('删除失败')
    }
  }

  // Handle rename
  const handleRename = async (documentId: number, newName: string) => {
    try {
      const response = await documentService.rename(documentId, newName)
      if (response.success) {
        message.success('重命名成功')
        setEditingDoc(null)
        loadDocuments(page, searchKeyword)
      }
    } catch (error: any) {
      message.error('重命名失败')
    }
  }

  // Handle preview
  const handlePreview = (document: Document) => {
    setPreviewDocument(document)
    setPreviewVisible(true)
  }

  // Handle page change
  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  return (
    <div className="h-full flex flex-col">
      {/* Search */}
      <div className="p-4 border-b border-gray-200">
        <Input
          placeholder="搜索文档..."
          prefix={<SearchOutlined />}
          value={searchKeyword}
          onChange={(e) => handleSearch(e.target.value)}
          allowClear
        />
      </div>

      {/* Documents List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center">
            <Text type="secondary">加载中...</Text>
          </div>
        ) : documents.length === 0 ? (
          <div className="p-4 text-center text-gray-400">
            <p>暂无文档</p>
          </div>
        ) : (
          <List
            dataSource={documents}
            renderItem={(doc) => (
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
                    {/* Document Info */}
                    <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                      <Space>
                        <FileTextOutlined style={{ fontSize: '18px', color: '#1890ff' }} />
                        <div>
                          {editingDoc?.id === doc.id ? (
                            <Input
                              size="small"
                              value={editingDoc.name}
                              onChange={(e) => setEditingDoc({ ...editingDoc, name: e.target.value })}
                              onPressEnter={() => {
                                if (editingDoc.name.trim()) {
                                  handleRename(doc.id, editingDoc.name)
                                }
                              }}
                              onBlur={() => {
                                if (editingDoc.name.trim()) {
                                  handleRename(doc.id, editingDoc.name)
                                } else {
                                  setEditingDoc(null)
                                }
                              }}
                              autoFocus
                            />
                          ) : (
                            <Text strong style={{ cursor: 'pointer' }} onClick={() => handlePreview(doc)}>
                              {doc.name}
                            </Text>
                          )}
                          <br />
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {new Date(doc.upload_time).toLocaleString('zh-CN')} · {doc.file_type.toUpperCase()} · 
                            {(doc.file_size / 1024).toFixed(2)} KB
                          </Text>
                        </div>
                      </Space>
                      <Tag color={PARSE_STATUS_COLORS[doc.parse_status]}>
                        {PARSE_STATUS_LABELS[doc.parse_status]}
                      </Tag>
                    </Space>

                    {/* Actions */}
                    {editingDoc?.id !== doc.id && (
                      <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                        <Button
                          type="text"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={() => handlePreview(doc)}
                        >
                          预览
                        </Button>
                        <Button
                          type="text"
                          size="small"
                          icon={<EditOutlined />}
                          onClick={() => setEditingDoc({ id: doc.id, name: doc.name })}
                        >
                          重命名
                        </Button>
                        <Popconfirm
                          title="确定要删除这个文档吗？"
                          onConfirm={() => handleDelete(doc.id)}
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
        title={previewDocument?.name}
        open={previewVisible}
        onCancel={() => {
          setPreviewVisible(false)
          setPreviewDocument(null)
        }}
        footer={null}
        width={800}
      >
        {previewDocument && (
          <div>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>文件类型：</Text>
                <Text>{previewDocument.file_type.toUpperCase()}</Text>
              </div>
              <div>
                <Text strong>文件大小：</Text>
                <Text>{(previewDocument.file_size / 1024).toFixed(2)} KB</Text>
              </div>
              <div>
                <Text strong>上传时间：</Text>
                <Text>{new Date(previewDocument.upload_time).toLocaleString('zh-CN')}</Text>
              </div>
              <div>
                <Text strong>解析状态：</Text>
                <Tag color={PARSE_STATUS_COLORS[previewDocument.parse_status]}>
                  {PARSE_STATUS_LABELS[previewDocument.parse_status]}
                </Tag>
              </div>
              {previewDocument.document_type && (
                <div>
                  <Text strong>文档类型：</Text>
                  <Text>{previewDocument.document_type === 'api' ? '接口文档' : '需求文档'}</Text>
                </div>
              )}
            </Space>
          </div>
        )}
      </Modal>
    </div>
  )
}
