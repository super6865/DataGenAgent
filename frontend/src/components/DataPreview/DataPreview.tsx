import { Typography } from 'antd'
import { Editor } from '@monaco-editor/react'

const { Text } = Typography

interface DataPreviewProps {
  data: string
  format?: string
}

export default function DataPreview({ data, format = 'json' }: DataPreviewProps) {
  if (format === 'json') {
    try {
      // Try to format JSON
      const parsed = JSON.parse(data)
      const formatted = JSON.stringify(parsed, null, 2)
      return (
        <Editor
          height="300px"
          defaultLanguage="json"
          value={formatted}
          theme="vs-light"
          options={{
            readOnly: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 12,
            wordWrap: 'on',
            automaticLayout: true,
          }}
        />
      )
    } catch {
      // If not valid JSON, show as text
      return (
        <Text style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', display: 'block' }}>
          {data}
        </Text>
      )
    }
  } else if (format === 'csv') {
    return (
      <Text style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', display: 'block' }}>
        {data}
      </Text>
    )
  } else {
    return (
      <Text style={{ whiteSpace: 'pre-wrap', display: 'block' }}>
        {data}
      </Text>
    )
  }
}
