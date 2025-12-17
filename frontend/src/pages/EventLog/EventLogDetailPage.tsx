import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Descriptions, Tag, Button, Space, Table, message, Spin, Collapse, Tabs, Empty } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons'
import { eventLogService } from '../../services/eventLogService'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Panel } = Collapse

// 解析包含 Unicode 转义序列的字符串
const parseUnicodeString = (str: string | undefined | null): string => {
  if (!str || typeof str !== 'string') return str || ''
  try {
    // 如果字符串看起来像 JSON 对象，尝试解析
    if (str.trim().startsWith('{') && str.trim().endsWith('}')) {
      try {
        const parsed = JSON.parse(str)
        // 如果解析后是对象，提取 reason 字段
        if (typeof parsed === 'object' && parsed.reason) {
          return parsed.reason
        }
        // 如果解析后是对象但没有 reason，返回格式化的 JSON
        if (typeof parsed === 'object') {
          return JSON.stringify(parsed, null, 2)
        }
      } catch {
        // 解析失败，继续处理
      }
    }
    
    // 如果字符串包含 Unicode 转义序列，尝试解析
    if (str.includes('\\u')) {
      // 尝试将整个字符串作为 JSON 字符串解析
      try {
        const parsed = JSON.parse(`"${str}"`)
        return parsed
      } catch {
        // 如果失败，尝试直接替换 Unicode 转义
        return str.replace(/\\u([0-9a-fA-F]{4})/g, (match, code) => {
          return String.fromCharCode(parseInt(code, 16))
        })
      }
    }
    
    // 如果是普通字符串，直接返回
    return str
  } catch {
    return str
  }
}

// 递归处理 JSON 对象，解析所有字符串中的 Unicode 转义序列
const formatJsonWithUnicode = (obj: any): any => {
  if (obj === null || obj === undefined) {
    return obj
  }
  
  if (typeof obj === 'string') {
    return parseUnicodeString(obj)
  }
  
  if (Array.isArray(obj)) {
    return obj.map(item => formatJsonWithUnicode(item))
  }
  
  if (typeof obj === 'object') {
    const result: any = {}
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        result[key] = formatJsonWithUnicode(obj[key])
      }
    }
    return result
  }
  
  return obj
}

const formatTimestampWithMs = (time: string) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss.SSS')
}

interface Span {
  span_id: string
  parent_span_id?: string
  name: string
  kind?: string
  start_time: string
  end_time?: string
  duration_ms?: number
  status_code?: string
  status_message?: string
  attributes?: Record<string, any>
  events?: any[]
  links?: any[]
}

interface SpanTreeNode {
  span: Span
  children: SpanTreeNode[]
}

export default function EventLogDetailPage() {
  const { traceId } = useParams<{ traceId: string }>()
  const navigate = useNavigate()
  const [trace, setTrace] = useState<any>(null)
  const [spans, setSpans] = useState<Span[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('tree')

  useEffect(() => {
    if (traceId) {
      loadTrace()
    }
  }, [traceId])

  const loadTrace = async () => {
    if (!traceId) return
    setLoading(true)
    try {
      console.log('Loading trace detail for traceId:', traceId)
      const response = await eventLogService.getTraceDetail(traceId)
      if (response && response.success && response.trace) {
        setTrace(response.trace)
        setSpans(response.spans || [])
      } else {
        message.warning('Trace不存在或数据为空')
      }
    } catch (error: any) {
      console.error('Error loading trace detail:', error)
      const errorMessage = error.response?.data?.detail || error.message || '加载Trace失败'
      if (error.response?.status === 404) {
        message.error(`Trace不存在: ${traceId}。请检查Trace ID是否正确，或该Trace可能已被删除。`)
      } else {
        message.error(`加载Trace失败: ${errorMessage}`)
      }
    } finally {
      setLoading(false)
    }
  }

  // Build span tree
  const spanTree = useMemo(() => {
    if (!spans.length) return []
    
    const spanMap = new Map<string, Span>()
    spans.forEach(span => spanMap.set(span.span_id, span))
    
    const rootSpans: SpanTreeNode[] = []
    const nodeMap = new Map<string, SpanTreeNode>()
    
    // Create nodes
    spans.forEach(span => {
      nodeMap.set(span.span_id, {
        span,
        children: [],
      })
    })
    
    // Build tree
    spans.forEach(span => {
      const node = nodeMap.get(span.span_id)!
      if (!span.parent_span_id || !nodeMap.has(span.parent_span_id)) {
        rootSpans.push(node)
      } else {
        const parentNode = nodeMap.get(span.parent_span_id)!
        parentNode.children.push(node)
      }
    })
    
    // Sort by start time
    const sortByStartTime = (nodes: SpanTreeNode[]) => {
      nodes.sort((a, b) => 
        new Date(a.span.start_time).getTime() - new Date(b.span.start_time).getTime()
      )
      nodes.forEach(node => {
        if (node.children.length > 0) {
          sortByStartTime(node.children)
        }
      })
    }
    sortByStartTime(rootSpans)
    
    return rootSpans
  }, [spans])


  // Loading state with full page structure
  if (loading && !trace) {
    return (
      <div className="h-full overflow-y-auto overflow-x-hidden" style={{ height: '100%' }}>
        <div className="flex flex-col p-4">
          <Card className="mb-4 flex-shrink-0">
            <div className="flex items-center justify-between mb-4">
              <Space>
                <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/event-log')}>
                  返回
                </Button>
                <h2 className="text-xl font-semibold m-0">事件日志详情</h2>
                {traceId && <Tag className="font-mono">{traceId}</Tag>}
              </Space>
              <Button icon={<ReloadOutlined />} onClick={loadTrace} loading={loading}>
                刷新
              </Button>
            </div>
            <div className="flex justify-center items-center py-16">
              <Spin size="large" tip="加载中..." />
            </div>
          </Card>
        </div>
      </div>
    )
  }

  // Empty state with full page structure
  if (!loading && !trace) {
    return (
      <div className="h-full overflow-y-auto overflow-x-hidden" style={{ height: '100%' }}>
        <div className="flex flex-col p-4">
          <Card className="mb-4 flex-shrink-0">
            <div className="flex items-center justify-between mb-4">
              <Space>
                <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/event-log')}>
                  返回
                </Button>
                <h2 className="text-xl font-semibold m-0">事件日志详情</h2>
                {traceId && <Tag className="font-mono">{traceId}</Tag>}
              </Space>
              <Button icon={<ReloadOutlined />} onClick={loadTrace} loading={loading}>
                刷新
              </Button>
            </div>
            <Empty
              description={
                <div>
                  <p style={{ fontSize: '16px', marginBottom: '8px' }}>Trace不存在</p>
                  <p style={{ color: '#999', fontSize: '14px' }}>
                    Trace ID: <span className="font-mono">{traceId}</span>
                  </p>
                  <p style={{ color: '#999', fontSize: '14px', marginTop: '8px' }}>
                    请检查Trace ID是否正确，或该Trace可能已被删除
                  </p>
                </div>
              }
              style={{ padding: '40px 0' }}
            />
          </Card>
        </div>
      </div>
    )
  }

  const spanColumns: ColumnsType<Span> = [
    {
      title: 'Span ID',
      dataIndex: 'span_id',
      key: 'span_id',
      width: 200,
      render: (text: string) => (
        <span className="font-mono text-xs">{text}</span>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'kind',
      key: 'kind',
      width: 100,
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 180,
      render: (text: string) => formatTimestampWithMs(text),
    },
    {
      title: '持续时间(ms)',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 120,
      render: (ms: number) => (ms ? `${ms.toFixed(2)}ms` : '-'),
    },
    {
      title: '状态',
      dataIndex: 'status_code',
      key: 'status_code',
      width: 100,
      render: (code: string) => (
        <Tag color={code === 'OK' ? 'green' : 'red'}>{code || '-'}</Tag>
      ),
    },
  ]

  return (
    <div className="h-full overflow-y-auto overflow-x-hidden" style={{ height: '100%' }}>
      <div className="flex flex-col p-4">
        <Card className="mb-4 flex-shrink-0">
          <div className="flex items-center justify-between mb-4">
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/event-log')}>
                返回
              </Button>
              <h2 className="text-xl font-semibold m-0">事件日志详情</h2>
              <Tag className="font-mono">{trace.trace_id}</Tag>
            </Space>
            <Button icon={<ReloadOutlined />} onClick={loadTrace}>
              刷新
            </Button>
          </div>
          <Descriptions column={3} bordered>
            <Descriptions.Item label="Trace ID">
              <span className="font-mono text-xs break-all">{trace.trace_id}</span>
            </Descriptions.Item>
            <Descriptions.Item label="服务名">{trace.service_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="操作名">{trace.operation_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="开始时间">
              {formatTimestampWithMs(trace.start_time)}
            </Descriptions.Item>
            <Descriptions.Item label="结束时间">
              {trace.end_time ? formatTimestampWithMs(trace.end_time) : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="持续时间">
              {trace.duration_ms ? `${trace.duration_ms.toFixed(2)}ms` : '-'}
            </Descriptions.Item>
            {trace.attributes && Object.keys(trace.attributes).length > 0 && (
              <Descriptions.Item label="属性" span={3}>
                <Collapse size="small">
                  <Panel header="查看属性" key="attributes">
                    <pre className="text-xs m-0 whitespace-pre-wrap break-words overflow-x-auto">
                      {JSON.stringify(formatJsonWithUnicode(trace.attributes), null, 2)}
                    </pre>
                  </Panel>
                </Collapse>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>

        <Card 
          title={`Spans (${spans.length})`} 
          className="flex-shrink-0"
        >
          <Tabs 
            activeKey={activeTab} 
            onChange={setActiveTab}
            items={[
              {
                key: 'tree',
                label: '树形视图',
                children: (
                  <div className="overflow-x-auto p-4">
                    {spanTree.map((node, idx) => (
                      <RenderSpanTree key={idx} node={node} depth={0} />
                    ))}
                  </div>
                ),
              },
              {
                key: 'list',
                label: '列表视图',
                children: (
                  <Table
                    columns={spanColumns}
                    dataSource={spans}
                    rowKey="span_id"
                    pagination={{ pageSize: 20 }}
                    scroll={{ x: 'max-content' }}
                    expandable={{
                      expandedRowRender: (record) => (
                        <div className="p-4">
                          <Collapse>
                            {record.attributes && Object.keys(record.attributes).length > 0 && (
                              <Panel header="属性" key="attributes">
                                <pre className="text-xs m-0 whitespace-pre-wrap break-words overflow-x-auto">
                                  {JSON.stringify(formatJsonWithUnicode(record.attributes), null, 2)}
                                </pre>
                              </Panel>
                            )}
                            {record.events && record.events.length > 0 && (
                              <Panel header={`事件 (${record.events.length})`} key="events">
                                <pre className="text-xs m-0 whitespace-pre-wrap break-words overflow-x-auto">
                                  {JSON.stringify(formatJsonWithUnicode(record.events), null, 2)}
                                </pre>
                              </Panel>
                            )}
                            {record.status_message && (
                              <Panel header="状态消息" key="status">
                                <p className="break-words">{record.status_message}</p>
                              </Panel>
                            )}
                          </Collapse>
                        </div>
                      ),
                    }}
                  />
                ),
              },
            ]}
          />
        </Card>
      </div>
    </div>
  )
}

function RenderSpanTree({ node, depth }: { node: SpanTreeNode; depth: number }) {
  const [expanded, setExpanded] = useState(depth < 2)
  
  return (
    <div className="ml-4 border-l-2 border-gray-200 pl-4 mb-2">
      <div className="flex items-center gap-2">
        {node.children.length > 0 && (
          <Button
            type="text"
            size="small"
            onClick={() => setExpanded(!expanded)}
            className="w-6 h-6 p-0"
          >
            {expanded ? '−' : '+'}
          </Button>
        )}
        <Tag color={node.span.status_code === 'OK' || !node.span.status_code ? 'green' : 'red'}>
          {node.span.name}
        </Tag>
        <span className="text-xs text-gray-500">
          {node.span.duration_ms?.toFixed(2)}ms
        </span>
        {node.span.status_code && node.span.status_code !== 'OK' && (
          <Tag color="red" size="small">{node.span.status_code}</Tag>
        )}
      </div>
      {expanded && node.children.length > 0 && (
        <div className="mt-2">
          {node.children.map((child, idx) => (
            <RenderSpanTree key={idx} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
      {expanded && node.span.attributes && Object.keys(node.span.attributes).length > 0 && (
        <Collapse size="small" className="mt-2">
          <Panel header="属性" key="attributes">
            <pre className="text-xs m-0 whitespace-pre-wrap break-words overflow-x-auto">
              {JSON.stringify(formatJsonWithUnicode(node.span.attributes), null, 2)}
            </pre>
          </Panel>
        </Collapse>
      )}
    </div>
  )
}
