import { useState, useEffect, useRef } from 'react'
import { Table, Button, Space, message, Popconfirm, Tag, Pagination, Input, Modal, Progress, Tabs, Typography, Collapse } from 'antd'
import { SearchOutlined, DeleteOutlined, EyeOutlined, ReloadOutlined, UploadOutlined, CopyOutlined } from '@ant-design/icons'
import { documentService, Document } from '../../services/documentService'
import AddDocumentModal from '../../components/DocumentUpload/AddDocumentModal'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Text, Paragraph } = Typography
const { Panel } = Collapse

/**
 * Format file size in bytes to human-readable format
 * @param bytes File size in bytes
 * @returns Formatted string (e.g., "1.5 MB", "500 KB", "2.3 GB")
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

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

export default function DocumentListPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  })
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewDocument, setPreviewDocument] = useState<Document | null>(null)
  const [uploadModalVisible, setUploadModalVisible] = useState(false)

  useEffect(() => {
    loadDocuments()
  }, [pagination.current, pagination.pageSize, searchKeyword])

  // Polling for parsing status
  useEffect(() => {
    // Check for documents that are parsing or pending (pending documents may start parsing soon)
    const activeDocs = documents.filter(doc => 
      doc.parse_status === 'parsing' || doc.parse_status === 'pending'
    )
    if (activeDocs.length === 0) return

    const interval = setInterval(() => {
      // Poll to update parsing status
      loadDocuments()
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documents])

  const loadDocuments = async () => {
    setLoading(true)
    try {
      const response = await documentService.getList(
        pagination.current,
        pagination.pageSize,
        searchKeyword || undefined
      )
      console.log('Documents API response:', response)
      if (response.success && response.data) {
        // Ensure items is an array
        const items = Array.isArray(response.data.items) ? response.data.items : []
        console.log('Setting documents:', items.length, 'items')
        setDocuments(items)
        setPagination((prev) => ({ ...prev, total: response.data.total || 0 }))
      } else {
        console.error('Failed to load documents - response:', response)
        message.error('加载文档列表失败')
        setDocuments([])
      }
    } catch (error: any) {
      console.error('Error loading documents:', error)
      const errorMessage = error?.response?.data?.detail || error?.message || '加载文档列表失败'
      console.error('Error details:', {
        message: errorMessage,
        response: error?.response,
        status: error?.response?.status,
      })
      message.error(errorMessage)
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      const response = await documentService.delete(id)
      if (response.success) {
        message.success('删除成功')
        loadDocuments()
      } else {
        throw new Error(response.message)
      }
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }


  const handlePreview = async (record: Document) => {
    // If document is not fully loaded, fetch the latest data
    if (!record.parse_result && record.parse_status === 'success') {
      try {
        const response = await documentService.getById(record.id)
        if (response.success) {
          setPreviewDocument(response.data)
        } else {
          setPreviewDocument(record)
        }
      } catch (error) {
        setPreviewDocument(record)
      }
    } else {
      setPreviewDocument(record)
    }
    setPreviewVisible(true)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      message.success('已复制到剪贴板')
    }).catch(() => {
      message.error('复制失败')
    })
  }

  const handleSearch = (value: string) => {
    setSearchKeyword(value)
    setPagination((prev) => ({ ...prev, current: 1 }))
  }

  const columns: ColumnsType<Document> = [
    {
      title: '文档名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      width: 300,
      render: (text: string) => <span title={text}>{text}</span>,
    },
    {
      title: '文件类型',
      dataIndex: 'file_type',
      key: 'file_type',
      width: 100,
      render: (type: string) => <Tag>{type.toUpperCase()}</Tag>,
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 120,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: '解析状态',
      dataIndex: 'parse_status',
      key: 'parse_status',
      width: 150,
      render: (status: string) => {
        // Show progress bar for parsing or pending status
        if (status === 'parsing' || status === 'pending') {
          return (
            <Progress
              percent={undefined}
              status="active"
              size="small"
              format={() => status === 'parsing' ? '解析中...' : '准备解析...'}
              style={{ minWidth: 100 }}
            />
          )
        }
        return (
          <Tag color={PARSE_STATUS_COLORS[status]}>
            {PARSE_STATUS_LABELS[status]}
          </Tag>
        )
      },
    },
    {
      title: '文档类型',
      dataIndex: 'document_type',
      key: 'document_type',
      width: 120,
      render: (type: string) => {
        if (!type) return '-'
        return type === 'api' ? '接口文档' : type === 'requirement' ? '需求文档' : '未知'
      },
    },
    {
      title: '上传时间',
      dataIndex: 'upload_time',
      key: 'upload_time',
      width: 180,
      render: (time: string) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 250,
      render: (_: any, record: Document) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
          >
            预览
          </Button>
          <Popconfirm
            title="确定要删除这个文档吗？"
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

  return (
    <div className="pt-2 pb-3 h-full flex flex-col">
      {/* 第一层：标题 */}
      <div className="flex items-center justify-between py-4 px-6">
        <div className="text-[20px] font-medium leading-6 coz-fg-plus">数据文档</div>
      </div>
      
      {/* 第二层：搜索框和操作按钮 */}
      <div className="box-border coz-fg-secondary pt-1 pb-3 px-6">
        <div className="flex items-center justify-between gap-4">
          <Space size="middle">
            <Input
              placeholder="搜索文档..."
              prefix={<SearchOutlined />}
              value={searchKeyword}
              onChange={(e) => handleSearch(e.target.value)}
              allowClear
              style={{ width: 300 }}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={loadDocuments}
            >
              刷新
            </Button>
          </Space>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadModalVisible(true)}
          >
            上传文档
          </Button>
        </div>
      </div>
      
      {/* 第三层：内容区 */}
      <div className="flex-1 overflow-hidden px-6 flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <Table
            columns={columns}
            dataSource={documents || []}
            rowKey="id"
            loading={loading}
            pagination={false}
            locale={{ emptyText: '暂无文档数据' }}
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

      {/* Preview Modal */}
      <Modal
        title={previewDocument?.name}
        open={previewVisible}
        onCancel={() => {
          setPreviewVisible(false)
          setPreviewDocument(null)
        }}
        footer={null}
        width={900}
      >
        {previewDocument && (
          <Tabs
            defaultActiveKey="basic"
            items={[
              {
                key: 'basic',
                label: '基本信息',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <div>
                      <Text strong>文件类型：</Text>
                      <Text>{previewDocument.file_type.toUpperCase()}</Text>
                    </div>
                    <div>
                      <Text strong>文件大小：</Text>
                      <Text>{formatFileSize(previewDocument.file_size)}</Text>
                    </div>
                    <div>
                      <Text strong>上传时间：</Text>
                      <Text>{dayjs(previewDocument.upload_time).format('YYYY-MM-DD HH:mm:ss')}</Text>
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
                        <Text>{previewDocument.document_type === 'api' ? '接口文档' : previewDocument.document_type === 'requirement' ? '需求文档' : '未知'}</Text>
                      </div>
                    )}
                  </Space>
                ),
              },
              {
                key: 'content',
                label: '解析内容',
                children: previewDocument.parse_result ? (
                  <div>
                    {previewDocument.parse_result.raw_content ? (
                      <div style={{ marginBottom: 16 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <Text strong>原始内容</Text>
                          <Button
                            type="text"
                            size="small"
                            icon={<CopyOutlined />}
                            onClick={() => copyToClipboard(previewDocument.parse_result.raw_content)}
                          >
                            复制
                          </Button>
                        </div>
                        <div
                          style={{
                            maxHeight: '400px',
                            overflow: 'auto',
                            padding: '12px',
                            backgroundColor: '#f5f5f5',
                            borderRadius: '4px',
                            border: '1px solid #d9d9d9',
                          }}
                        >
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', fontSize: '12px' }}>
                            {previewDocument.parse_result.raw_content}
                          </pre>
                        </div>
                      </div>
                    ) : (
                      <Text type="secondary">暂无原始内容</Text>
                    )}
                    
                    {previewDocument.parse_result.structured_content && (
                      <Collapse>
                        <Panel header="结构化内容" key="structured">
                          <Space direction="vertical" style={{ width: '100%' }}>
                            {previewDocument.parse_result.structured_content.sections && previewDocument.parse_result.structured_content.sections.length > 0 && (
                              <div>
                                <Text strong>章节 ({previewDocument.parse_result.structured_content.sections.length} 个)：</Text>
                                <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                                  {previewDocument.parse_result.structured_content.sections.slice(0, 10).map((section: any, index: number) => (
                                    <li key={index}>
                                      <Text>{section.title || `章节 ${index + 1}`}</Text>
                                    </li>
                                  ))}
                                  {previewDocument.parse_result.structured_content.sections.length > 10 && (
                                    <li>
                                      <Text type="secondary">...还有 {previewDocument.parse_result.structured_content.sections.length - 10} 个章节</Text>
                                    </li>
                                  )}
                                </ul>
                              </div>
                            )}
                            {previewDocument.parse_result.structured_content.code_blocks && previewDocument.parse_result.structured_content.code_blocks.length > 0 && (
                              <div>
                                <Text strong>代码块 ({previewDocument.parse_result.structured_content.code_blocks.length} 个)</Text>
                              </div>
                            )}
                          </Space>
                        </Panel>
                      </Collapse>
                    )}
                  </div>
                ) : (
                  <Text type="secondary">
                    {previewDocument.parse_status === 'parsing' ? '正在解析中...' : 
                     previewDocument.parse_status === 'pending' ? '尚未开始解析' :
                     previewDocument.parse_status === 'failed' ? '解析失败，请重试' :
                     '暂无解析内容'}
                  </Text>
                ),
              },
              {
                key: 'metadata',
                label: '元数据',
                children: previewDocument.parse_result?.metadata ? (
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    {previewDocument.parse_result.metadata.title && (
                      <div>
                        <Text strong>标题：</Text>
                        <Text>{previewDocument.parse_result.metadata.title}</Text>
                      </div>
                    )}
                    <div>
                      <Text strong>字数：</Text>
                      <Text>{previewDocument.parse_result.metadata.word_count || 0}</Text>
                    </div>
                    <div>
                      <Text strong>行数：</Text>
                      <Text>{previewDocument.parse_result.metadata.line_count || 0}</Text>
                    </div>
                    {previewDocument.parse_result.metadata.keywords && previewDocument.parse_result.metadata.keywords.length > 0 && (
                      <div>
                        <Text strong>关键词：</Text>
                        <div style={{ marginTop: 8 }}>
                          {previewDocument.parse_result.metadata.keywords.slice(0, 20).map((keyword: string, index: number) => (
                            <Tag key={index} style={{ marginBottom: 4 }}>{keyword}</Tag>
                          ))}
                          {previewDocument.parse_result.metadata.keywords.length > 20 && (
                            <Tag>...还有 {previewDocument.parse_result.metadata.keywords.length - 20} 个</Tag>
                          )}
                        </div>
                      </div>
                    )}
                  </Space>
                ) : (
                  <Text type="secondary">暂无元数据</Text>
                ),
              },
              {
                key: 'intent',
                label: '意图识别',
                children: (() => {
                  // Check if intent_recognition exists in parse_result
                  const intentRecognition = previewDocument.parse_result?.intent_recognition
                  
                  // If intent_recognition exists, show full details
                  if (intentRecognition) {
                    return (
                      <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        <div>
                          <Text strong>文档类型：</Text>
                          <Tag color={intentRecognition.document_type === 'api' ? 'blue' : 'green'}>
                            {intentRecognition.document_type === 'api' ? '接口文档' : 
                             intentRecognition.document_type === 'requirement' ? '需求文档' : '未知'}
                          </Tag>
                        </div>
                        <div>
                          <Text strong>置信度：</Text>
                          <Text>{(intentRecognition.confidence * 100).toFixed(1)}%</Text>
                        </div>
                        {intentRecognition.reasoning && (
                          <div>
                            <Text strong>识别理由：</Text>
                            <Paragraph style={{ marginTop: 8, marginBottom: 0 }}>
                              {intentRecognition.reasoning}
                            </Paragraph>
                          </div>
                        )}
                      </Space>
                    )
                  }
                  
                  // If document_type exists but intent_recognition doesn't, show basic info
                  if (previewDocument.document_type) {
                    return (
                      <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        <div>
                          <Text strong>文档类型：</Text>
                          <Tag color={previewDocument.document_type === 'api' ? 'blue' : 'green'}>
                            {previewDocument.document_type === 'api' ? '接口文档' : 
                             previewDocument.document_type === 'requirement' ? '需求文档' : '未知'}
                          </Tag>
                        </div>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          注：此文档的意图识别信息不完整，仅显示文档类型
                        </Text>
                      </Space>
                    )
                  }
                  
                  // No intent recognition data at all
                  return <Text type="secondary">未进行意图识别</Text>
                })(),
              },
            ]}
          />
        )}
      </Modal>

      {/* Upload Document Modal */}
      <AddDocumentModal
        visible={uploadModalVisible}
        onCancel={() => setUploadModalVisible(false)}
        showLibraryTab={false}
        onSelect={(document) => {
          // 上传成功后刷新列表
          message.success('文档上传成功，正在解析...')
          loadDocuments()
          setUploadModalVisible(false)
        }}
      />
    </div>
  )
}
