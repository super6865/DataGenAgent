import { useState, useEffect, useRef } from 'react'
import { flushSync } from 'react-dom'
import { Card, Button, Space, Typography, Select, message, Spin, Avatar } from 'antd'
import { 
  SendOutlined, 
  DownloadOutlined, 
  CopyOutlined, 
  RobotOutlined,
  FileTextOutlined,
  UserOutlined,
  DatabaseOutlined,
  PlusOutlined,
  FormOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { dataGenerationService, GenerateDataRequest } from '../../services/dataGenerationService'
import { modelConfigService, ModelConfig } from '../../services/modelConfigService'
import { Document } from '../../services/documentService'
import { DataTemplate } from '../../services/dataTemplateService'
import { AddDocumentModal } from '../../components/DocumentUpload'
import { TemplateSelectModal } from '../../components/TemplateSelect'
import DataPreview from '../../components/DataPreview/DataPreview'
import robotIconUrl from '../../assets/images/AI 机器人.svg'

const { Text } = Typography
const { Option } = Select

// localStorage 键名
const STORAGE_KEY_INPUT = 'dataGen_inputContent'
const STORAGE_KEY_MESSAGES = 'dataGen_messages'

interface Message {
  role: 'user' | 'assistant'
  content: string
  htmlContent?: string // 保存 HTML 内容，用于用户消息显示
  format?: string
  usage?: {
    input_tokens: number
    output_tokens: number
  }
  references?: Document[]
}

export default function DataGenerationPage() {
  // 不再需要 input 状态，contentEditable 的内容直接保存在 DOM 中
  const [messages, setMessages] = useState<Message[]>([])
  const [isGenerating, setIsGenerating] = useState(false)
  const [modelConfigs, setModelConfigs] = useState<ModelConfig[]>([])
  const [selectedModelId, setSelectedModelId] = useState<number | undefined>()
  const [format, setFormat] = useState<string>('json')
  const [selectedDocuments, setSelectedDocuments] = useState<Document[]>([])
  const [selectedTemplates, setSelectedTemplates] = useState<DataTemplate[]>([])
  const [documentModalVisible, setDocumentModalVisible] = useState(false)
  const [templateModalVisible, setTemplateModalVisible] = useState(false)
  const inputRef = useRef<HTMLDivElement>(null)
  const cursorPositionRef = useRef<number | null>(null)

  useEffect(() => {
    loadModelConfigs()
    
    // 恢复聊天记录
    try {
      const savedMessages = localStorage.getItem(STORAGE_KEY_MESSAGES)
      if (savedMessages) {
        const parsed = JSON.parse(savedMessages)
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed)
        }
      }
    } catch (error) {
      console.error('Failed to restore messages:', error)
    }
    
    // 恢复输入框内容
    try {
      const savedInput = localStorage.getItem(STORAGE_KEY_INPUT)
      if (savedInput && inputRef.current) {
        inputRef.current.innerHTML = savedInput
        // 从 HTML 中提取文档和模板信息，创建基本对象
        const tempDiv = document.createElement('div')
        tempDiv.innerHTML = savedInput
        
        const documentElements = tempDiv.querySelectorAll('[data-document-id]')
        const documents: Document[] = []
        documentElements.forEach(el => {
          const docId = parseInt((el as HTMLElement).getAttribute('data-document-id') || '0')
          const docName = (el as HTMLElement).getAttribute('data-document-name') || ''
          if (docId > 0 && docName) {
            documents.push({
              id: docId,
              name: docName,
              file_path: '',
              file_type: '',
              file_size: 0,
              upload_time: '',
              parse_status: 'success',
            } as Document)
          }
        })
        if (documents.length > 0) {
          setSelectedDocuments(documents)
        }
        
        const templateElements = tempDiv.querySelectorAll('[data-template-id]')
        const templates: DataTemplate[] = []
        templateElements.forEach(el => {
          const templateId = parseInt((el as HTMLElement).getAttribute('data-template-id') || '0')
          const templateName = (el as HTMLElement).getAttribute('data-template-name') || ''
          if (templateId > 0 && templateName) {
            templates.push({
              id: templateId,
              name: templateName,
              schema: {},
              field_definitions: [],
              field_count: 0,
            } as DataTemplate)
          }
        })
        if (templates.length > 0) {
          setSelectedTemplates(templates)
        }
        
        // 恢复后需要重新绑定删除按钮的事件
        restoreInputEventHandlers()
      }
    } catch (error) {
      console.error('Failed to restore input:', error)
    }
  }, [])

  // 同步输入框中的文档和模板元素与状态的辅助函数
  const syncStateWithInput = () => {
    if (!inputRef.current) return
    
    // 检查输入框中的实际文档元素
    const documentElements = inputRef.current.querySelectorAll('[data-document-id]')
    const documentIdsInInput = Array.from(documentElements).map(el => {
      const docId = (el as HTMLElement).getAttribute('data-document-id')
      return docId ? parseInt(docId, 10) : 0
    }).filter(id => id > 0)
    
    // 检查输入框中的实际模板元素
    const templateElements = inputRef.current.querySelectorAll('[data-template-id]')
    const templateIdsInInput = Array.from(templateElements).map(el => {
      const templateId = (el as HTMLElement).getAttribute('data-template-id')
      return templateId ? parseInt(templateId, 10) : 0
    }).filter(id => id > 0)
    
    // 同步文档状态：直接基于输入框中的实际元素更新状态
    setSelectedDocuments(prev => {
      // 如果输入框中没有文档，总是返回新数组，确保 React 检测到变化
      // 即使之前也是空数组，也返回新的空数组引用
      if (documentIdsInInput.length === 0) {
        return []
      }
      // 从之前的状态中找到输入框中存在的文档，返回新数组
      const validDocs = prev.filter(doc => documentIdsInInput.includes(doc.id))
      // 如果找到的文档数量与输入框中的ID数量不一致，说明状态不同步，需要更新
      if (validDocs.length !== documentIdsInInput.length) {
        return validDocs
      }
      // 检查ID是否完全匹配
      const idsMatch = validDocs.length === documentIdsInInput.length &&
                       validDocs.every(doc => documentIdsInInput.includes(doc.id)) &&
                       documentIdsInInput.every(id => validDocs.some(doc => doc.id === id))
      // 如果完全匹配且长度相同，检查是否与prev相同
      if (idsMatch && validDocs.length === prev.length) {
        const sameOrder = validDocs.every((doc, idx) => doc.id === prev[idx]?.id)
        return sameOrder ? prev : validDocs
      }
      return validDocs
    })
    
    // 同步模板状态：直接基于输入框中的实际元素更新状态
    setSelectedTemplates(prev => {
      // 如果输入框中没有模板
      if (templateIdsInInput.length === 0) {
        // 总是返回新数组，确保 React 检测到变化
        // 即使之前也是空数组，也返回新的空数组引用
        return []
      }
      // 从之前的状态中找到输入框中存在的模板，返回新数组
      const validTemplates = prev.filter(t => templateIdsInInput.includes(t.id))
      // 如果找到的模板数量与输入框中的ID数量不一致，说明状态不同步，需要更新
      if (validTemplates.length !== templateIdsInInput.length) {
        // 这种情况不应该发生，但为了安全，返回找到的模板
        return validTemplates
      }
      // 检查ID是否完全匹配
      const idsMatch = validTemplates.length === templateIdsInInput.length &&
                       validTemplates.every(t => templateIdsInInput.includes(t.id)) &&
                       templateIdsInInput.every(id => validTemplates.some(t => t.id === id))
      // 如果完全匹配且长度相同，检查是否与prev相同
      if (idsMatch && validTemplates.length === prev.length) {
        const sameOrder = validTemplates.every((t, idx) => t.id === prev[idx]?.id)
        return sameOrder ? prev : validTemplates
      }
      return validTemplates
    })
  }

  // 恢复输入框中的事件处理器（用于删除按钮）
  const restoreInputEventHandlers = () => {
    if (!inputRef.current) return
    
    // 为所有文档标签的删除按钮重新绑定事件
    const documentElements = inputRef.current.querySelectorAll('[data-document-id]')
    documentElements.forEach(element => {
      const docId = parseInt((element as HTMLElement).getAttribute('data-document-id') || '0')
      if (docId > 0) {
        const closeBtn = element.querySelector('span[style*="cursor: pointer"]')
        if (closeBtn) {
          (closeBtn as HTMLElement).onclick = (e: MouseEvent) => {
            e.preventDefault()
            e.stopPropagation()
            handleDocumentRemoveFromInput(docId)
          }
        }
      }
    })
    
    // 为所有模板标签的删除按钮重新绑定事件
    const templateElements = inputRef.current.querySelectorAll('[data-template-id]')
    templateElements.forEach(element => {
      const templateId = parseInt((element as HTMLElement).getAttribute('data-template-id') || '0')
      if (templateId > 0) {
        const closeBtn = element.querySelector('span[style*="cursor: pointer"]')
        if (closeBtn) {
          (closeBtn as HTMLElement).onclick = (e: MouseEvent) => {
            e.preventDefault()
            e.stopPropagation()
            handleTemplateRemoveFromInput(templateId)
          }
        }
      }
    })
  }

  // 保存光标位置 - 使用精确的字符计数方法
  const saveCursorPosition = () => {
    if (!inputRef.current) return
    
    const selection = window.getSelection()
    if (!selection || selection.rangeCount === 0) return
    
    const range = selection.getRangeAt(0)
    
    // 确保 range 在 inputRef.current 内部
    if (!inputRef.current.contains(range.commonAncestorContainer)) {
      return
    }
    
    // 使用精确的字符计数方法，只计算文本节点的字符
    let charCount = 0
    const walker = window.document.createTreeWalker(
      inputRef.current,
      NodeFilter.SHOW_TEXT,
      null
    )
    
    let node: Node | null
    let found = false
    
    while ((node = walker.nextNode())) {
      if (node === range.startContainer) {
        // 找到光标所在的文本节点
        charCount += range.startOffset
        found = true
        break
      } else {
        // 累加文本节点的长度
        charCount += node.textContent?.length || 0
      }
    }
    
    // 如果没有找到（startContainer 不是文本节点），尝试找到最近的文本节点
    if (!found) {
      // 如果 startContainer 是元素节点，找到它内部的第一个文本节点
      if (range.startContainer.nodeType === Node.ELEMENT_NODE) {
        const element = range.startContainer as HTMLElement
        const firstTextNode = Array.from(element.childNodes).find(n => n.nodeType === Node.TEXT_NODE)
        if (firstTextNode) {
          // 重新计算到这个文本节点的位置
          charCount = 0
          const walker2 = window.document.createTreeWalker(
            inputRef.current,
            NodeFilter.SHOW_TEXT,
            null
          )
          let node2: Node | null
          while ((node2 = walker2.nextNode())) {
            if (node2 === firstTextNode) {
              charCount += Math.min(range.startOffset, firstTextNode.textContent?.length || 0)
              break
            } else {
              charCount += node2.textContent?.length || 0
            }
          }
        }
      }
    }
    
    cursorPositionRef.current = charCount
  }


  // 从 contentEditable 中提取文本和文档引用
  const extractContent = () => {
    if (!inputRef.current) return { text: '', documents: [] as Document[], templates: [] as DataTemplate[] }
    
    const textParts: string[] = []
    const documents: Document[] = []
    const templates: DataTemplate[] = []
    const processedDocs = new Set<number>()
    const processedTemplates = new Set<number>()
    
    // 递归遍历所有节点
    const traverse = (node: Node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        textParts.push(node.textContent || '')
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const element = node as HTMLElement
        if (element.dataset.documentId) {
          const docId = parseInt(element.dataset.documentId)
          if (!processedDocs.has(docId)) {
            const existingDoc = selectedDocuments.find(d => d.id === docId)
            if (existingDoc) {
              documents.push(existingDoc)
              processedDocs.add(docId)
            }
          }
          // 文档标签在文本中显示为 @文档:名称
          textParts.push(`@文档:${element.dataset.documentName || ''}`)
        } else if (element.dataset.templateId) {
          const templateId = parseInt(element.dataset.templateId)
          if (!processedTemplates.has(templateId)) {
            const existingTemplate = selectedTemplates.find(t => t.id === templateId)
            if (existingTemplate) {
              templates.push(existingTemplate)
              processedTemplates.add(templateId)
            }
          }
          // 模板标签在文本中显示为 @模板:名称
          textParts.push(`@模板:${element.dataset.templateName || ''}`)
        } else {
          // 继续遍历子节点
          for (let i = 0; i < node.childNodes.length; i++) {
            traverse(node.childNodes[i])
          }
        }
      }
    }
    
    // 遍历所有子节点
    if (inputRef.current) {
      for (let i = 0; i < inputRef.current.childNodes.length; i++) {
        traverse(inputRef.current.childNodes[i])
      }
    }
    
    const text = textParts.join('').trim()
    
    // 如果没有文本内容，尝试使用 innerText
    if (!text && inputRef.current.innerText) {
      return { text: inputRef.current.innerText.trim(), documents, templates }
    }
    
    return { text, documents, templates }
  }

  const loadModelConfigs = async () => {
    try {
      const response = await modelConfigService.getAll(false)
      if (response.success) {
        setModelConfigs(response.data)
        // Set default model if available
        const defaultConfig = response.data.find((c: ModelConfig) => c.is_default)
        if (defaultConfig) {
          setSelectedModelId(defaultConfig.id)
        } else if (response.data.length > 0) {
          setSelectedModelId(response.data[0].id)
        }
      }
    } catch (error) {
      console.error('Failed to load model configs:', error)
    }
  }

  const handleGenerate = async () => {
    // 提取内容
    const { text, documents, templates } = extractContent()
    
    if (!text.trim()) {
      message.warning('请输入数据生成需求')
      return
    }

    if (!selectedModelId) {
      message.warning('请先选择模型配置')
      return
    }

    setIsGenerating(true)
    
    // 保存输入框的 HTML 内容，以便在消息中显示
    let htmlContent = ''
    if (inputRef.current) {
      // 克隆 HTML 内容，移除删除按钮的 onclick 事件
      const tempDiv = window.document.createElement('div')
      tempDiv.innerHTML = inputRef.current.innerHTML
      
      // 移除所有删除按钮的 onclick 事件和样式
      const closeButtons = tempDiv.querySelectorAll('span[onclick]')
      closeButtons.forEach(btn => {
        const span = btn as HTMLElement
        // 检查是否是删除按钮（包含 × 符号）
        if (span.textContent?.includes('×')) {
          span.removeAttribute('onclick')
          // 移除点击样式，改为不可点击
          span.style.cursor = 'default'
          span.style.pointerEvents = 'none'
        }
      })
      
      htmlContent = tempDiv.innerHTML
    }
    
    const userMessage: Message = {
      role: 'user',
      content: text,
      htmlContent: htmlContent, // 保存 HTML 内容
      references: documents.length > 0 ? [...documents] : undefined,
    }
    setMessages((prev) => {
      const newMessages = [...prev, userMessage]
      // 保存聊天记录到 localStorage
      try {
        localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(newMessages))
      } catch (error) {
        console.error('Failed to save messages to localStorage:', error)
      }
      return newMessages
    })
    
    // 立即清空输入框
    if (inputRef.current) {
      inputRef.current.innerHTML = ''
    }
    setSelectedDocuments([])
    setSelectedTemplates([])
    cursorPositionRef.current = null
    
    // 清空输入框的 localStorage
    try {
      localStorage.removeItem(STORAGE_KEY_INPUT)
    } catch (error) {
      console.error('Failed to clear input from localStorage:', error)
    }

    try {
      // 构建引用列表（文档和模板）
      const references: any[] = []
      if (documents.length > 0) {
        references.push(...documents.map(doc => ({
          type: 'document',
          id: doc.id,
          name: doc.name,
        })))
      }
      if (templates.length > 0) {
        references.push(...templates.map(t => ({
          type: 'template',
          id: t.id,
          name: t.name,
        })))
      }

      const request: GenerateDataRequest = {
        user_query: text,
        model_config_id: selectedModelId,
        format: format,
        references: references.length > 0 ? references : undefined,
      }

      const response = await dataGenerationService.generateData(request)
      
      if (response.success) {
        const assistantMessage: Message = {
          role: 'assistant',
          content: response.data.generated_data,
          format: response.data.format,
          usage: response.data.usage,
        }
        setMessages((prev) => {
          const newMessages = [...prev, assistantMessage]
          // 保存聊天记录到 localStorage
          try {
            localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(newMessages))
          } catch (error) {
            console.error('Failed to save messages to localStorage:', error)
          }
          return newMessages
        })
        message.success('数据生成成功')
      } else {
        throw new Error(response.message || '生成失败')
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || error.message || '生成失败')
      const errorMessage: Message = {
        role: 'assistant',
        content: `错误: ${error.response?.data?.detail || error.message || '生成失败'}`,
      }
      setMessages((prev) => {
        const newMessages = [...prev, errorMessage]
        // 保存聊天记录到 localStorage
        try {
          localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(newMessages))
        } catch (error) {
          console.error('Failed to save messages to localStorage:', error)
        }
        return newMessages
      })
    } finally {
      setIsGenerating(false)
      // 确保输入框已清空（在发送时已经清空，这里再次确认）
      if (inputRef.current && inputRef.current.innerHTML.trim()) {
        inputRef.current.innerHTML = ''
      }
      if (selectedDocuments.length > 0) {
        setSelectedDocuments([])
      }
      if (selectedTemplates.length > 0) {
        setSelectedTemplates([])
      }
      cursorPositionRef.current = null
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const { text } = extractContent()
      if (!isGenerating && text.trim()) {
        handleGenerate()
      }
    } else if (e.key === 'Backspace' && inputRef.current) {
      // 处理Backspace键删除标签
      const selection = window.getSelection()
      if (!selection || selection.rangeCount === 0) return
      
      const range = selection.getRangeAt(0)
      if (range.collapsed) {
        // 光标在某个位置，检查前面是否是标签
        const container = range.startContainer
        const offset = range.startOffset
        
        // 如果光标在文本节点中，检查前面的节点
        if (container.nodeType === Node.TEXT_NODE && offset === 0) {
          const prevSibling = container.previousSibling
          if (prevSibling && prevSibling.nodeType === Node.ELEMENT_NODE) {
            const element = prevSibling as HTMLElement
            // 检查是否是文档或模板标签
            if (element.hasAttribute('data-document-id')) {
              e.preventDefault()
              const documentId = parseInt(element.getAttribute('data-document-id') || '0')
              handleDocumentRemoveFromInput(documentId)
              return
            } else if (element.hasAttribute('data-template-id')) {
              e.preventDefault()
              const templateId = parseInt(element.getAttribute('data-template-id') || '0')
              handleTemplateRemoveFromInput(templateId)
              return
            }
          }
        } else if (container.nodeType === Node.ELEMENT_NODE) {
          // 如果光标在元素中，检查是否是标签本身
          const element = container as HTMLElement
          if (element.hasAttribute('data-document-id') || element.hasAttribute('data-template-id')) {
            e.preventDefault()
            if (element.hasAttribute('data-document-id')) {
              const documentId = parseInt(element.getAttribute('data-document-id') || '0')
              handleDocumentRemoveFromInput(documentId)
            } else if (element.hasAttribute('data-template-id')) {
              const templateId = parseInt(element.getAttribute('data-template-id') || '0')
              handleTemplateRemoveFromInput(templateId)
            }
            return
          }
          
          // 检查前一个兄弟节点
          const prevSibling = element.previousSibling
          if (prevSibling && prevSibling.nodeType === Node.ELEMENT_NODE) {
            const prevElement = prevSibling as HTMLElement
            if (prevElement.hasAttribute('data-document-id')) {
              e.preventDefault()
              const documentId = parseInt(prevElement.getAttribute('data-document-id') || '0')
              handleDocumentRemoveFromInput(documentId)
              return
            } else if (prevElement.hasAttribute('data-template-id')) {
              e.preventDefault()
              const templateId = parseInt(prevElement.getAttribute('data-template-id') || '0')
              handleTemplateRemoveFromInput(templateId)
              return
            }
          }
        }
      }
    }
  }

  const handleInput = () => {
    // 不再使用 innerText 更新状态，避免丢失 HTML 结构（文档标签）
    // contentEditable 的内容直接保存在 DOM 中，不需要通过 React 状态同步
    // 只在需要时通过 extractContent() 提取内容
    
    // 保存输入框内容到 localStorage
    if (inputRef.current) {
      try {
        localStorage.setItem(STORAGE_KEY_INPUT, inputRef.current.innerHTML)
      } catch (error) {
        console.error('Failed to save input to localStorage:', error)
      }
    }
  }
  
  // 检查输入框是否有内容（用于发送按钮状态）
  const hasContent = () => {
    if (!inputRef.current) return false
    const { text } = extractContent()
    return text.trim().length > 0 || selectedDocuments.length > 0 || selectedTemplates.length > 0
  }

  const handlePaste = (e: React.ClipboardEvent<HTMLDivElement>) => {
    e.preventDefault()
    const text = e.clipboardData.getData('text/plain')
    const selection = window.getSelection()
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0)
      range.deleteContents()
      const textNode = document.createTextNode(text)
      range.insertNode(textNode)
      range.setStartAfter(textNode)
      range.collapse(true)
      selection.removeAllRanges()
      selection.addRange(range)
    }
    handleInput()
  }

  const handleDownload = (content: string, format: string) => {
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `generated_data.${format === 'json' ? 'json' : format === 'csv' ? 'csv' : 'txt'}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    message.success('下载成功')
  }

  const handleCopy = (content: string, format?: string) => {
    try {
      // 确保内容是字符串
      let textToCopy: string
      if (typeof content !== 'string') {
        textToCopy = JSON.stringify(content, null, 2)
      } else {
        textToCopy = content
      }

      // 如果是 JSON 格式，尝试格式化和验证
      if (format === 'json' || (!format && textToCopy.trim().startsWith('{'))) {
        try {
          const parsed = JSON.parse(textToCopy)
          textToCopy = JSON.stringify(parsed, null, 2)
        } catch {
          // 如果不是有效的 JSON，保持原样
        }
      }

      // 优先使用现代 Clipboard API
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textToCopy).then(() => {
          message.success('已复制到剪贴板')
        }).catch((err) => {
          console.error('Clipboard API failed:', err)
          // 降级到传统方法
          fallbackCopy(textToCopy)
        })
      } else {
        // 降级到传统方法
        fallbackCopy(textToCopy)
      }
    } catch (error) {
      console.error('Copy failed:', error)
      message.error('复制失败，请手动选择文本复制')
    }
  }

  // 降级复制方案（兼容旧浏览器）
  const fallbackCopy = (text: string) => {
    try {
      // 创建临时 textarea 元素
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.left = '-999999px'
      textarea.style.top = '-999999px'
      document.body.appendChild(textarea)
      textarea.focus()
      textarea.select()
      
      const successful = document.execCommand('copy')
      document.body.removeChild(textarea)
      
      if (successful) {
        message.success('已复制到剪贴板')
      } else {
        throw new Error('execCommand failed')
      }
    } catch (err) {
      console.error('Fallback copy failed:', err)
      message.error('复制失败，请手动选择文本复制')
    }
  }

  const handleAddDocument = () => {
    // 在打开模态框前保存光标位置
    saveCursorPosition()
    setDocumentModalVisible(true)
  }

  const handleDocumentSelect = (document: Document) => {
    // 互斥选择：如果已选择模板，清空模板
    if (selectedTemplates.length > 0) {
      // 清空所有模板标签
      if (inputRef.current) {
        const templateTags = inputRef.current.querySelectorAll('[data-template-id]')
        templateTags.forEach(tag => {
          const parent = tag.parentNode
          if (parent) {
            // 删除元素前后的空格
            const nextSibling = tag.nextSibling
            const prevSibling = tag.previousSibling
            
            if (nextSibling && nextSibling.nodeType === Node.TEXT_NODE && nextSibling.textContent === ' ') {
              parent.removeChild(nextSibling)
            }
            if (prevSibling && prevSibling.nodeType === Node.TEXT_NODE && prevSibling.textContent === ' ') {
              parent.removeChild(prevSibling)
            }
            
            parent.removeChild(tag)
          }
        })
      }
      setSelectedTemplates([])
      message.info('已清空模板，选择文档后无法同时选择模板')
    }
    
    // 使用 setTimeout 确保模态框关闭后再插入，避免 React 重新渲染导致内容丢失
    setTimeout(() => {
      if (!inputRef.current) return
      
      // 检查输入框中是否已存在该文档标签（通过 DOM 检查，更准确）
      const existingTag = inputRef.current.querySelector(`[data-document-id="${document.id}"]`)
      if (existingTag) {
        message.warning('文档已添加')
        return
      }
      
      // 恢复光标位置或使用当前选择
      const selection = window.getSelection()
      let range: Range | null = null
      
      // 首先尝试使用保存的光标位置
      if (cursorPositionRef.current !== null && inputRef.current) {
        // 使用与保存时相同的方法恢复位置（只遍历文本节点）
        range = window.document.createRange()
        let charCount = 0
        let found = false
        
        const walker = window.document.createTreeWalker(
          inputRef.current,
          NodeFilter.SHOW_TEXT,
          null
        )
        
        let node: Node | null
        while ((node = walker.nextNode())) {
          const nodeLength = node.textContent?.length || 0
          const nextCharCount = charCount + nodeLength
          
          if (cursorPositionRef.current <= nextCharCount) {
            // 找到光标应该插入的文本节点
            const offset = cursorPositionRef.current - charCount
            range.setStart(node, offset)
            range.setEnd(node, offset)
            found = true
            break
          } else {
            charCount = nextCharCount
          }
        }
        
        if (!found) {
          // 如果无法恢复（光标位置超出文本长度），插入到文本末尾
          range = window.document.createRange()
          range.selectNodeContents(inputRef.current)
          range.collapse(false)
        }
      } else if (selection && selection.rangeCount > 0) {
        // 如果没有保存的位置，使用当前选择
        range = selection.getRangeAt(0)
        // 确保 range 在 inputRef.current 内部
        if (!inputRef.current.contains(range.commonAncestorContainer)) {
          // 如果不在内部，插入到文本末尾
          range = window.document.createRange()
          range.selectNodeContents(inputRef.current)
          range.collapse(false)
        }
      } else {
        // 如果都没有，插入到文本末尾（用户最后输入的位置）
        range = window.document.createRange()
        range.selectNodeContents(inputRef.current)
        range.collapse(false)
      }
      
      // 确保 range 在 inputRef.current 内部
      if (!range || !inputRef.current.contains(range.commonAncestorContainer)) {
        // 如果 range 不在内部，插入到文本末尾
        range = window.document.createRange()
        range.selectNodeContents(inputRef.current)
        range.collapse(false)
      }
      
      if (!range) return
      
      // 在光标位置插入文档标签
      if (inputRef.current) {
        // 不删除内容，直接插入
        // range.deleteContents() // 移除这行，避免删除已有内容
        
        // 创建文档标签元素
        const tagElement = window.document.createElement('span')
        tagElement.contentEditable = 'false'
        tagElement.dataset.documentId = document.id.toString()
        tagElement.dataset.documentName = document.name
        tagElement.style.cssText = `
          display: inline-flex;
          align-items: center;
          height: 22px;
          line-height: 22px;
          padding: 2px 8px;
          margin: 0;
          margin-right: 4px;
          background-color: #e6f7ff;
          border: 1px solid #91d5ff;
          color: #1890ff;
          border-radius: 4px;
          cursor: default;
          vertical-align: middle;
          font-size: 12px;
        `
        
        // 添加图标 (使用 SVG)
        const iconSvg = window.document.createElementNS('http://www.w3.org/2000/svg', 'svg')
        iconSvg.setAttribute('width', '14')
        iconSvg.setAttribute('height', '14')
        iconSvg.setAttribute('viewBox', '0 0 1024 1024')
        iconSvg.setAttribute('fill', 'currentColor')
        iconSvg.style.cssText = 'margin-right: 4px; flex-shrink: 0;'
        const iconPath = window.document.createElementNS('http://www.w3.org/2000/svg', 'path')
        iconPath.setAttribute('d', 'M854.6 288.6L639.4 73.4c-6-6-14.1-9.4-22.6-9.4H192c-17.7 0-32 14.3-32 32v832c0 17.7 14.3 32 32 32h640c17.7 0 32-14.3 32-32V311.3c0-8.5-3.4-16.6-9.4-22.7zM790.2 326H602V137.8L790.2 326zm1.8 562H232V136h302v240c0 17.7 14.3 32 32 32h240v520z')
        iconSvg.appendChild(iconPath)
        tagElement.appendChild(iconSvg)
        
        // 添加文本
        const text = window.document.createTextNode(`@文档:${document.name}`)
        tagElement.appendChild(text)
        
        // 添加删除按钮
        const closeBtn = window.document.createElement('span')
        closeBtn.innerHTML = ' ×'
        closeBtn.style.cssText = `
          margin-left: 4px;
          cursor: pointer;
          font-weight: bold;
          color: #1890ff;
          user-select: none;
        `
        closeBtn.onclick = (e: MouseEvent) => {
          e.preventDefault()
          e.stopPropagation()
          handleDocumentRemoveFromInput(document.id)
        }
        tagElement.appendChild(closeBtn)
        
        // 插入元素
        range.insertNode(tagElement)
        
        // 在标签后添加一个空格，并将光标移到空格后
        const space = window.document.createTextNode(' ')
        range.setStartAfter(tagElement)
        range.insertNode(space)
        range.setStartAfter(space)
        range.collapse(true)
        
        // 更新选择
        if (selection) {
          selection.removeAllRanges()
          selection.addRange(range)
        }
        
        // 更新状态
        setSelectedDocuments(prev => {
          // 再次检查，确保不会重复添加
          if (prev.find(doc => doc.id === document.id)) {
            return prev
          }
          return [...prev, document]
        })
        
        // 保存输入框内容到 localStorage
        try {
          localStorage.setItem(STORAGE_KEY_INPUT, inputRef.current.innerHTML)
        } catch (error) {
          console.error('Failed to save input to localStorage:', error)
        }
        
        // 确保输入框获得焦点
        inputRef.current.focus()
        
        // 使用 requestAnimationFrame 确保 DOM 更新完成后再显示消息
        requestAnimationFrame(() => {
          message.success(`已添加文档: ${document.name}`)
        })
      }
    }, 100) // 延迟 100ms 确保模态框已关闭
  }

  // 从输入框中删除文档
  const handleDocumentRemoveFromInput = (documentId: number) => {
    if (!inputRef.current) return
    
    // 查找并删除对应的文档标签元素
    const docElement = inputRef.current.querySelector(`[data-document-id="${documentId}"]`)
    
    if (docElement) {
      const parent = docElement.parentNode
      if (parent) {
        // 删除元素前后的空格
        const nextSibling = docElement.nextSibling
        const prevSibling = docElement.previousSibling
        
        if (nextSibling && nextSibling.nodeType === Node.TEXT_NODE && nextSibling.textContent === ' ') {
          parent.removeChild(nextSibling)
        }
        if (prevSibling && prevSibling.nodeType === Node.TEXT_NODE && prevSibling.textContent === ' ') {
          parent.removeChild(prevSibling)
        }
        
        parent.removeChild(docElement)
      }
    }
    
    // 直接从状态中移除对应的文档，使用 flushSync 强制同步更新状态
    flushSync(() => {
      setSelectedDocuments(prev => {
        const updated = prev.filter(doc => doc.id !== documentId)
        // filter 已经返回新数组，确保 React 检测到变化
        return updated
      })
    })
    
    // 更新 localStorage 中的输入框内容
    if (inputRef.current) {
      try {
        localStorage.setItem(STORAGE_KEY_INPUT, inputRef.current.innerHTML)
      } catch (error) {
        console.error('Failed to save input to localStorage:', error)
      }
    }
  }

  const handleAddTemplate = () => {
    // 在打开模态框前保存光标位置
    saveCursorPosition()
    setTemplateModalVisible(true)
  }

  const handleTemplateSelect = (template: DataTemplate) => {
    // 互斥选择：如果已选择文档，清空文档
    if (selectedDocuments.length > 0) {
      // 清空所有文档标签
      if (inputRef.current) {
        const documentTags = inputRef.current.querySelectorAll('[data-document-id]')
        documentTags.forEach(tag => {
          const parent = tag.parentNode
          if (parent) {
            // 删除元素前后的空格
            const nextSibling = tag.nextSibling
            const prevSibling = tag.previousSibling
            
            if (nextSibling && nextSibling.nodeType === Node.TEXT_NODE && nextSibling.textContent === ' ') {
              parent.removeChild(nextSibling)
            }
            if (prevSibling && prevSibling.nodeType === Node.TEXT_NODE && prevSibling.textContent === ' ') {
              parent.removeChild(prevSibling)
            }
            
            parent.removeChild(tag)
          }
        })
      }
      setSelectedDocuments([])
      message.info('已清空文档，选择模板后无法同时选择文档')
    }
    
    // 使用 setTimeout 确保模态框关闭后再插入，避免 React 重新渲染导致内容丢失
    setTimeout(() => {
      if (!inputRef.current) return
      
      // 检查输入框中是否已存在该模板标签
      const existingTag = inputRef.current.querySelector(`[data-template-id="${template.id}"]`)
      if (existingTag) {
        message.warning('模板已添加')
        return
      }
      
      // 恢复光标位置或使用当前选择
      const selection = window.getSelection()
      let range: Range | null = null
      
      // 首先尝试使用保存的光标位置
      if (cursorPositionRef.current !== null && inputRef.current) {
        range = window.document.createRange()
        let charCount = 0
        let found = false
        
        const walker = window.document.createTreeWalker(
          inputRef.current,
          NodeFilter.SHOW_TEXT,
          null
        )
        
        let node: Node | null
        while ((node = walker.nextNode())) {
          const nodeLength = node.textContent?.length || 0
          const nextCharCount = charCount + nodeLength
          
          if (cursorPositionRef.current <= nextCharCount) {
            const offset = cursorPositionRef.current - charCount
            range.setStart(node, offset)
            range.setEnd(node, offset)
            found = true
            break
          } else {
            charCount = nextCharCount
          }
        }
        
        if (!found) {
          range = window.document.createRange()
          range.selectNodeContents(inputRef.current)
          range.collapse(false)
        }
      } else if (selection && selection.rangeCount > 0) {
        range = selection.getRangeAt(0)
        if (!inputRef.current.contains(range.commonAncestorContainer)) {
          range = window.document.createRange()
          range.selectNodeContents(inputRef.current)
          range.collapse(false)
        }
      } else {
        range = window.document.createRange()
        range.selectNodeContents(inputRef.current)
        range.collapse(false)
      }
      
      if (!range || !inputRef.current.contains(range.commonAncestorContainer)) {
        range = window.document.createRange()
        range.selectNodeContents(inputRef.current)
        range.collapse(false)
      }
      
      if (!range) return
      
      // 在光标位置插入模板标签
      if (inputRef.current) {
        // 创建模板标签元素
        const tagElement = window.document.createElement('span')
        tagElement.contentEditable = 'false'
        tagElement.dataset.templateId = template.id.toString()
        tagElement.dataset.templateName = template.name
        tagElement.style.cssText = `
          display: inline-flex;
          align-items: center;
          height: 22px;
          line-height: 22px;
          padding: 2px 8px;
          margin: 0;
          margin-right: 4px;
          background-color: #fff7e6;
          border: 1px solid #ffd591;
          color: #fa8c16;
          border-radius: 4px;
          cursor: default;
          vertical-align: middle;
          font-size: 12px;
        `
        
        // 添加图标 (使用 SVG)
        const iconSvg = window.document.createElementNS('http://www.w3.org/2000/svg', 'svg')
        iconSvg.setAttribute('width', '14')
        iconSvg.setAttribute('height', '14')
        iconSvg.setAttribute('viewBox', '0 0 1024 1024')
        iconSvg.setAttribute('fill', 'currentColor')
        iconSvg.style.cssText = 'margin-right: 4px; flex-shrink: 0;'
        const iconPath = window.document.createElementNS('http://www.w3.org/2000/svg', 'path')
        iconPath.setAttribute('d', 'M880 112H144c-17.7 0-32 14.3-32 32v736c0 17.7 14.3 32 32 32h736c17.7 0 32-14.3 32-32V144c0-17.7-14.3-32-32-32zM513.1 518.1l-192 161c-5.2 4.4-13.1.7-13.1-6.1v-62.7c0-2.3 1.1-4.6 2.9-6.1L420.7 512l-109.8-92.2a7.95 7.95 0 0 1-2.9-6.1V351c0-6.8 7.9-10.5 13.1-6.1l192 160.9c3.9 3.2 3.9 9.1 0 12.3zM716 673c0 4.4-3.4 8-7.5 8h-185c-4.1 0-7.5-3.6-7.5-8v-48c0-4.4 3.4-8 7.5-8h185c4.1 0 7.5 3.6 7.5 8v48z')
        iconSvg.appendChild(iconPath)
        tagElement.appendChild(iconSvg)
        
        // 添加文本
        const text = window.document.createTextNode(`@模板:${template.name}`)
        tagElement.appendChild(text)
        
        // 添加删除按钮
        const closeBtn = window.document.createElement('span')
        closeBtn.innerHTML = ' ×'
        closeBtn.style.cssText = `
          margin-left: 4px;
          cursor: pointer;
          font-weight: bold;
          color: #fa8c16;
          user-select: none;
        `
        closeBtn.onclick = (e: MouseEvent) => {
          e.preventDefault()
          e.stopPropagation()
          handleTemplateRemoveFromInput(template.id)
        }
        tagElement.appendChild(closeBtn)
        
        // 插入元素
        range.insertNode(tagElement)
        
        // 在标签后添加一个空格，并将光标移到空格后
        const space = window.document.createTextNode(' ')
        range.setStartAfter(tagElement)
        range.insertNode(space)
        range.setStartAfter(space)
        range.collapse(true)
        
        // 更新选择
        if (selection) {
          selection.removeAllRanges()
          selection.addRange(range)
        }
        
        // 更新状态
        setSelectedTemplates(prev => {
          if (prev.find(t => t.id === template.id)) {
            return prev
          }
          return [...prev, template]
        })
        
        // 保存输入框内容到 localStorage
        try {
          localStorage.setItem(STORAGE_KEY_INPUT, inputRef.current.innerHTML)
        } catch (error) {
          console.error('Failed to save input to localStorage:', error)
        }
        
        // 确保输入框获得焦点
        inputRef.current.focus()
        
        // 使用 requestAnimationFrame 确保 DOM 更新完成后再显示消息
        requestAnimationFrame(() => {
          message.success(`已添加模板: ${template.name}`)
        })
      }
    }, 100) // 延迟 100ms 确保模态框已关闭
  }

  // 从输入框中删除模板
  const handleTemplateRemoveFromInput = (templateId: number) => {
    if (!inputRef.current) return
    
    // 查找并删除对应的模板标签元素
    const templateElement = inputRef.current.querySelector(`[data-template-id="${templateId}"]`)
    
    if (templateElement) {
      const parent = templateElement.parentNode
      if (parent) {
        // 删除元素前后的空格
        const nextSibling = templateElement.nextSibling
        const prevSibling = templateElement.previousSibling
        
        if (nextSibling && nextSibling.nodeType === Node.TEXT_NODE && nextSibling.textContent === ' ') {
          parent.removeChild(nextSibling)
        }
        if (prevSibling && prevSibling.nodeType === Node.TEXT_NODE && prevSibling.textContent === ' ') {
          parent.removeChild(prevSibling)
        }
        
        parent.removeChild(templateElement)
      }
    }
    
    // 直接从状态中移除对应的模板，使用 flushSync 强制同步更新状态
    flushSync(() => {
      setSelectedTemplates(prev => {
        const updated = prev.filter(t => t.id !== templateId)
        // filter 已经返回新数组，确保 React 检测到变化
        return updated
      })
    })
    
    // 更新 localStorage 中的输入框内容
    if (inputRef.current) {
      try {
        localStorage.setItem(STORAGE_KEY_INPUT, inputRef.current.innerHTML)
      } catch (error) {
        console.error('Failed to save input to localStorage:', error)
      }
    }
  }

  // 清空聊天记录
  const handleClearMessages = () => {
    setMessages([])
    try {
      localStorage.removeItem(STORAGE_KEY_MESSAGES)
    } catch (error) {
      console.error('Failed to clear messages from localStorage:', error)
    }
    message.success('聊天记录已清空')
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Top Bar */}
      <div className="flex justify-between items-center px-6 py-4 bg-gray-50 border-b border-gray-100">
        <span className="text-lg font-medium text-gray-800">AI生成数据</span>
        <Space>
          <Select
            value={selectedModelId}
            onChange={setSelectedModelId}
            placeholder="选择模型"
            style={{ width: 150 }}
            suffixIcon={<span className="text-gray-400">▼</span>}
          >
            {modelConfigs.map((config) => (
              <Option key={config.id} value={config.id}>
                {config.config_name} ({config.model_version})
              </Option>
            ))}
          </Select>
          <Select
            value={format}
            onChange={setFormat}
            style={{ width: 100 }}
            suffixIcon={<span className="text-gray-400">▼</span>}
          >
            <Option value="json">JSON</Option>
            <Option value="csv">CSV</Option>
            <Option value="excel">Excel</Option>
            <Option value="text">文本</Option>
          </Select>
        </Space>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden flex flex-col relative bg-gray-50">
        {messages.length === 0 ? (
          /* Welcome View */
          <div className="flex-1 flex flex-col items-center justify-center px-6">
            {/* Robot Icon */}
            <div className="relative mb-8">
              <img 
                src={robotIconUrl}
                alt="AI Robot"
                style={{ 
                  width: '80px',
                  height: '80px',
                  filter: 'drop-shadow(0 4px 12px rgba(99, 102, 241, 0.2))'
                }} 
              />
            </div>
            
            {/* Greeting */}
            <p className="text-base text-gray-800 mb-2">你好，我是DG</p>
            <h3 className="text-xl font-bold text-gray-900">输入您的需求, 我将为您生成数据</h3>
          </div>
        ) : (
          /* Messages Area */
          <div className="flex-1 overflow-y-auto px-6 py-4">
            <div className="max-w-4xl mx-auto flex flex-col gap-4">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex items-start gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  <Avatar
                    size={36}
                    icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    style={{
                      backgroundColor: msg.role === 'user' ? '#1890ff' : '#6366f1',
                      flexShrink: 0
                    }}
                  />
                  <Card
                    size="small"
                    className={msg.role === 'user' ? 'max-w-[80%]' : 'w-full'}
                    style={{
                      textAlign: msg.role === 'user' ? 'right' : 'left',
                      background: msg.role === 'user' ? 'rgba(var(--coze-bg-0), 1)' : 'rgba(var(--coze-bg-1), 1)',
                    }}
                  >
                    {msg.role === 'user' ? (
                      <div 
                        className="whitespace-pre-wrap break-words"
                        style={{ lineHeight: '22px' }}
                        dangerouslySetInnerHTML={{ __html: msg.htmlContent || msg.content }}
                      />
                    ) : (
                      <div>
                        <div className="mb-2 flex justify-between items-center">
                          <Space>
                            {msg.format && (
                              <Text type="secondary" className="text-xs">
                                格式: {msg.format.toUpperCase()}
                              </Text>
                            )}
                            {msg.usage && (
                              <Text type="secondary" className="text-xs">
                                Tokens: {msg.usage.input_tokens + msg.usage.output_tokens}
                              </Text>
                            )}
                          </Space>
                          <Space>
                            <Button
                              type="text"
                              size="small"
                              icon={<CopyOutlined />}
                              onClick={() => handleCopy(msg.content, msg.format)}
                            >
                              复制
                            </Button>
                            <Button
                              type="text"
                              size="small"
                              icon={<DownloadOutlined />}
                              onClick={() => handleDownload(msg.content, msg.format || 'json')}
                            >
                              下载
                            </Button>
                          </Space>
                        </div>
                        <DataPreview data={msg.content} format={msg.format || 'json'} />
                      </div>
                    )}
                  </Card>
                </div>
              ))}
              {isGenerating && (
                <div className="flex items-start gap-3 flex-row">
                  <Avatar
                    size={36}
                    icon={<RobotOutlined />}
                    style={{
                      backgroundColor: '#6366f1',
                      flexShrink: 0
                    }}
                  />
                  <Card
                    size="small"
                    className="w-full"
                    style={{
                      textAlign: 'left',
                      background: 'rgba(var(--coze-bg-1), 1)',
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <Spin size="small" />
                      <Text type="secondary">正在生成数据...</Text>
                    </div>
                  </Card>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Input Area - Fixed Bottom */}
      <div className="px-6 py-5 bg-gray-50 border-t border-gray-100">
        <div className="w-4/5 mx-auto">
          {/* Action Cards */}
          <div className="flex gap-2 mb-3 items-center justify-between">
            <div className="flex gap-2">
              <div 
                className={`rounded-lg px-2 py-1 shadow-sm transition-shadow flex items-center gap-2 ${
                  selectedTemplates.length > 0 
                    ? 'cursor-not-allowed opacity-50 border border-gray-200 bg-gray-50' 
                    : 'cursor-pointer hover:shadow-md border border-blue-100'
                }`}
                style={selectedTemplates.length > 0 ? {} : { backgroundColor: '#f0f4ff' }}
                onClick={selectedTemplates.length > 0 ? undefined : handleAddDocument}
                title={selectedTemplates.length > 0 ? '已选择模板，无法同时选择文档' : '添加文档'}
              >
                <FileTextOutlined 
                  style={{ 
                    fontSize: '14px', 
                    color: selectedTemplates.length > 0 ? '#999' : '#3b82f6'
                  }} 
                />
                <span className={`text-xs font-medium whitespace-nowrap ${
                  selectedTemplates.length > 0 ? 'text-gray-400' : 'text-gray-700'
                }`}>添加文档</span>
              </div>
              
              <div 
                className={`rounded-lg px-2 py-1 shadow-sm transition-shadow flex items-center gap-2 ${
                  selectedDocuments.length > 0 
                    ? 'cursor-not-allowed opacity-50 border border-gray-200 bg-gray-50' 
                    : 'cursor-pointer hover:shadow-md border border-orange-100'
                }`}
                style={selectedDocuments.length > 0 ? {} : { backgroundColor: '#fff7ed' }}
                onClick={selectedDocuments.length > 0 ? undefined : handleAddTemplate}
                title={selectedDocuments.length > 0 ? '已选择文档，无法同时选择模板' : '添加数据模板'}
              >
                <FormOutlined 
                  style={{ 
                    fontSize: '14px', 
                    color: selectedDocuments.length > 0 ? '#999' : '#fa8c16'
                  }} 
                />
                <span className={`text-xs font-medium whitespace-nowrap ${
                  selectedDocuments.length > 0 ? 'text-gray-400' : 'text-gray-700'
                }`}>添加数据模板</span>
              </div>
              
              <div 
                className="bg-white rounded-lg px-2 py-1 shadow-sm hover:shadow-md transition-shadow cursor-pointer border border-pink-100 flex items-center gap-2"
                style={{ backgroundColor: '#fef2f2' }}
                onClick={() => message.info('此功能正在开发中')}
              >
                <DatabaseOutlined 
                  style={{ 
                    fontSize: '14px', 
                    color: '#ec4899'
                  }} 
                />
                <span className="text-xs text-gray-700 font-medium whitespace-nowrap">添加数据源</span>
              </div>
            </div>
            
            {/* 清空聊天记录按钮 */}
            {messages.length > 0 && (
              <Button
                type="default"
                size="small"
                icon={<DeleteOutlined />}
                onClick={handleClearMessages}
                danger
              >
                清空聊天记录
              </Button>
            )}
          </div>
          
          <div className="relative bg-white rounded-lg shadow-md p-4">
            <div className="relative">
              {/* Input area with inline document references */}
              <div 
                className="relative"
                style={{
                  padding: '4px 60px 4px 4px',
                }}
              >
                {/* ContentEditable div for input with inline document tags */}
                <div
                  ref={inputRef}
                  contentEditable={!isGenerating}
                  onInput={handleInput}
                  onKeyDown={handleKeyDown}
                  onPaste={handlePaste}
                  onSelect={saveCursorPosition}
                  onClick={saveCursorPosition}
                  onKeyUp={saveCursorPosition}
                  suppressContentEditableWarning
                  data-placeholder={selectedDocuments.length === 0 && selectedTemplates.length === 0 ? "请输入内容..." : ""}
                  className="border-0 bg-transparent resize-none outline-none"
                  style={{ 
                    minHeight: '50px',
                    padding: '8px',
                    margin: '0',
                    boxShadow: 'none',
                    outline: 'none',
                    lineHeight: '22px',
                    wordWrap: 'break-word',
                    whiteSpace: 'pre-wrap',
                    overflowY: 'auto',
                    maxHeight: '200px',
                    color: '#000',
                  }}
                />
                <style>{`
                  div[contenteditable][data-placeholder]:empty:before {
                    content: attr(data-placeholder);
                    color: #bfbfbf;
                    pointer-events: none;
                  }
                  div[contenteditable]:focus {
                    outline: none;
                  }
                `}</style>
              </div>
            </div>
            <div className="absolute bottom-6 right-4 flex items-center">
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleGenerate}
                loading={isGenerating}
                disabled={!hasContent() || !selectedModelId}
                style={{
                  backgroundColor: hasContent() ? '#3b82f6' : '#93c5fd',
                  borderColor: hasContent() ? '#3b82f6' : '#93c5fd',
                  borderRadius: '8px',
                  height: '36px',
                  paddingLeft: '16px',
                  paddingRight: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              />
            </div>
          </div>
          
          {/* 会话提示信息 - 放在文本框下方最底部 */}
          {messages.length > 0 && (
            <div className="mt-2">
              <Text type="secondary" className="text-xs">
                提示：聊天记录不记入当前会话中，目前仅支持当次会话
              </Text>
            </div>
          )}
        </div>
      </div>

      {/* Document Upload Modal */}
      <AddDocumentModal
        visible={documentModalVisible}
        onCancel={() => setDocumentModalVisible(false)}
        onSelect={handleDocumentSelect}
      />

      {/* Template Select Modal */}
      <TemplateSelectModal
        visible={templateModalVisible}
        onCancel={() => setTemplateModalVisible(false)}
        onSelect={handleTemplateSelect}
      />
    </div>
  )
}
