import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Button, Input, Space, message, Select, DatePicker, Pagination } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { eventLogService } from '../../services/eventLogService'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

interface Trace {
  trace_id: string
  service_name: string
  operation_name: string
  start_time: string
  end_time?: string
  duration_ms?: number
  status_code?: string
}

export default function EventLogPage() {
  const navigate = useNavigate()
  const [traces, setTraces] = useState<Trace[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTraceId, setSearchTraceId] = useState('')
  const [serviceFilter, setServiceFilter] = useState<string | undefined>()
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  })

  useEffect(() => {
    loadTraces()
  }, [pagination.current, pagination.pageSize, serviceFilter, dateRange])

  const loadTraces = async () => {
    setLoading(true)
    try {
      const skip = (pagination.current - 1) * pagination.pageSize
      const apiParams: any = {
        skip,
        limit: pagination.pageSize,
      }
      if (serviceFilter) {
        apiParams.service_name = serviceFilter
      }
      if (dateRange) {
        apiParams.start_time = dateRange[0].toISOString()
        apiParams.end_time = dateRange[1].toISOString()
      }
      const response = await eventLogService.listTraces(apiParams)
      if (response.success) {
        setTraces(response.traces || [])
        setPagination((prev) => ({ ...prev, total: response.total || 0 }))
      } else {
        setTraces([])
        setPagination((prev) => ({ ...prev, total: 0 }))
      }
    } catch (error) {
      message.error('加载事件日志失败')
      setTraces([])
    } finally {
      setLoading(false)
    }
  }

  const handleSearchTraceId = async (traceId: string) => {
    if (!traceId) {
      loadTraces()
      return
    }
    try {
      const response = await eventLogService.getTrace(traceId)
      if (response.success && response.trace) {
        setTraces([response.trace])
        setPagination((prev) => ({ ...prev, total: 1, current: 1 }))
      } else {
        setTraces([])
        setPagination((prev) => ({ ...prev, total: 0 }))
        message.warning('未找到Trace')
      }
    } catch (error) {
      message.error('查询Trace失败')
    }
  }

  const uniqueServices = useMemo(() => {
    const services = new Set(traces.map((t) => t.service_name).filter(Boolean))
    return Array.from(services)
  }, [traces])

  const formatTimestamp = (time: string) => {
    return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
  }

  const columns: ColumnsType<Trace> = [
    {
      title: 'Trace ID',
      dataIndex: 'trace_id',
      key: 'trace_id',
      ellipsis: true,
      render: (text: string) => (
        <Button
          type="link"
          onClick={() => {
            console.log('Navigating to trace detail with trace_id:', text)
            navigate(`/event-log/traces/${text}`)
          }}
          className="p-0 font-mono text-xs"
        >
          {text}
        </Button>
      ),
    },
    {
      title: '服务名',
      dataIndex: 'service_name',
      key: 'service_name',
      width: 150,
    },
    {
      title: '操作名',
      dataIndex: 'operation_name',
      key: 'operation_name',
      width: 200,
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 180,
      sorter: (a, b) =>
        new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
      render: (text: string) => formatTimestamp(text),
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
      render: (code: string) => code || '-',
    },
  ]

  return (
    <div className="pt-2 pb-3 h-full flex flex-col">
      <div className="text-[20px] font-medium leading-6 coz-fg-plus py-4 px-6">事件日志</div>
      <div className="px-6 mb-4">
        <Space wrap>
          <Input
            placeholder="搜索Trace ID"
            prefix={<SearchOutlined />}
            value={searchTraceId}
            onChange={(e) => setSearchTraceId(e.target.value)}
            onPressEnter={() => handleSearchTraceId(searchTraceId)}
            allowClear
            style={{ width: 300 }}
          />
          <Select
            placeholder="筛选服务"
            allowClear
            value={serviceFilter}
            onChange={setServiceFilter}
            style={{ width: 200 }}
          >
            {uniqueServices.map((service) => (
              <Select.Option key={service} value={service}>
                {service}
              </Select.Option>
            ))}
          </Select>
          <RangePicker
            showTime
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
          />
        </Space>
      </div>
      <div className="flex-1 overflow-hidden px-6 flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <Table
            columns={columns}
            dataSource={traces}
            rowKey="trace_id"
            loading={loading}
            pagination={false}
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
    </div>
  )
}
