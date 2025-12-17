import { useState, useCallback } from 'react'
import { Modal, Tabs, Upload, Button, message, Input, List, Card, Space, Typography, Spin } from 'antd'
import { InboxOutlined, FileTextOutlined, SearchOutlined, CheckOutlined } from '@ant-design/icons'
import type { UploadFile, UploadProps } from 'antd/es/upload'
import { documentService, Document } from '../../services/documentService'

const { Dragger } = Upload
const { Text } = Typography

interface AddDocumentModalProps {
  visible: boolean
  onCancel: () => void
  onSelect?: (document: Document) => void  // 可选，如果不提供则只上传不选择
  showLibraryTab?: boolean  // 是否显示"从资源库选择"Tab，默认为true
}

const ALLOWED_TYPES = ['.md', '.docx', '.pdf', '.txt']
const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB

export default function AddDocumentModal({ visible, onCancel, onSelect, showLibraryTab = true }: AddDocumentModalProps) {
  const [activeTab, setActiveTab] = useState('upload')
  const [uploading, setUploading] = useState(false)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null)

  // Load documents list
  const loadDocuments = useCallback(async (search?: string) => {
    setLoading(true)
    try {
      const response = await documentService.getList(1, 100, search)
      if (response.success) {
        setDocuments(response.data.items)
      }
    } catch (error: any) {
      message.error('加载文档列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // Load documents when switching to library tab
  const handleTabChange = (key: string) => {
    setActiveTab(key)
    if (key === 'library') {
      loadDocuments()
    }
  }

  // Handle file upload
  const handleUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options
    
    setUploading(true)
    try {
      const response = await documentService.upload(file as File)
      if (response.success) {
        message.success('文档上传成功')
        onSuccess?.(response.data, file as any)
        // Auto-select uploaded document if onSelect is provided
        if (onSelect) {
          onSelect(response.data)
        }
        handleCancel()
      } else {
        throw new Error(response.message || '上传失败')
      }
    } catch (error: any) {
      // Extract error message from response
      const errorMessage = error.response?.data?.detail || error.message || '上传失败'
      message.error(errorMessage)
      onError?.(error)
    } finally {
      setUploading(false)
      setFileList([])
    }
  }

  // Validate file before upload
  const beforeUpload = (file: File) => {
    // Check file type
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ALLOWED_TYPES.includes(fileExt)) {
      message.error(`不支持的文件格式。支持的格式：${ALLOWED_TYPES.join(', ')}`)
      return false
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      message.error(`文件大小不能超过 ${MAX_FILE_SIZE / (1024 * 1024)}MB`)
      return false
    }

    return true
  }

  // Handle file list change
  const handleFileListChange: UploadProps['onChange'] = (info) => {
    setFileList(info.fileList)
  }

  // Handle document selection from library
  const handleSelectDocument = (document: Document) => {
    setSelectedDocId(document.id)
  }

  // Handle confirm selection
  const handleConfirmSelection = () => {
    if (selectedDocId) {
      const selectedDoc = documents.find(doc => doc.id === selectedDocId)
      if (selectedDoc) {
        if (onSelect) {
          onSelect(selectedDoc)
        }
        handleCancel()
      }
    } else {
      message.warning('请先选择一个文档')
    }
  }

  // Handle cancel
  const handleCancel = () => {
    setActiveTab('upload')
    setFileList([])
    setSearchKeyword('')
    setSelectedDocId(null)
    onCancel()
  }

  // Handle search
  const handleSearch = (value: string) => {
    setSearchKeyword(value)
    loadDocuments(value)
  }

  return (
    <Modal
      title="添加文档"
      open={visible}
      onCancel={handleCancel}
      width={700}
      footer={null}
    >
      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        items={[
          {
            key: 'upload',
            label: '上传文档',
            children: (
              <div style={{ padding: '20px 0' }}>
                <Dragger
                  name="file"
                  multiple={false}
                  fileList={fileList}
                  beforeUpload={beforeUpload}
                  customRequest={handleUpload}
                  onChange={handleFileListChange}
                  disabled={uploading}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
                  </p>
                  <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                  <p className="ant-upload-hint">
                    支持格式：.md, .docx, .pdf, .txt
                    <br />
                    最大文件：50MB
                  </p>
                </Dragger>
                
                {uploading && (
                  <div style={{ textAlign: 'center', marginTop: 16 }}>
                    <Spin /> <Text type="secondary">正在上传...</Text>
                  </div>
                )}
              </div>
            ),
          },
          ...(showLibraryTab ? [{
            key: 'library',
            label: '从资源库选择',
            children: (
          <div style={{ padding: '20px 0' }}>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {/* Search */}
              <Input
                placeholder="搜索文档..."
                prefix={<SearchOutlined />}
                value={searchKeyword}
                onChange={(e) => handleSearch(e.target.value)}
                allowClear
              />

              {/* Documents List */}
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {loading ? (
                  <div style={{ textAlign: 'center', padding: '40px' }}>
                    <Spin />
                  </div>
                ) : documents.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                    {searchKeyword ? '未找到匹配的文档' : '暂无文档'}
                  </div>
                ) : (
                  <List
                    dataSource={documents}
                    renderItem={(doc) => (
                      <List.Item
                        style={{
                          padding: '12px',
                          cursor: 'pointer',
                          backgroundColor: selectedDocId === doc.id ? '#e6f7ff' : 'transparent',
                          border: selectedDocId === doc.id ? '1px solid #1890ff' : '1px solid #f0f0f0',
                          borderRadius: '4px',
                          marginBottom: '8px',
                        }}
                        onClick={() => handleSelectDocument(doc)}
                      >
                        <Card
                          size="small"
                          style={{ width: '100%', border: 'none' }}
                          bodyStyle={{ padding: 0 }}
                        >
                          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                            <Space>
                              <FileTextOutlined style={{ fontSize: '20px', color: '#1890ff' }} />
                              <div>
                                <Text strong>{doc.name}</Text>
                                <br />
                                <Text type="secondary" style={{ fontSize: '12px' }}>
                                  {new Date(doc.upload_time).toLocaleString('zh-CN')} · {doc.file_type.toUpperCase()}
                                </Text>
                              </div>
                            </Space>
                            {selectedDocId === doc.id && (
                              <CheckOutlined style={{ color: '#1890ff', fontSize: '18px' }} />
                            )}
                          </Space>
                        </Card>
                      </List.Item>
                    )}
                  />
                )}
              </div>

              {/* Action Buttons */}
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button onClick={handleCancel}>取消</Button>
                <Button
                  type="primary"
                  onClick={handleConfirmSelection}
                  disabled={!selectedDocId}
                >
                  确认选择
                </Button>
              </Space>
            </Space>
          </div>
            ),
          }] : []),
        ]}
      />
    </Modal>
  )
}
