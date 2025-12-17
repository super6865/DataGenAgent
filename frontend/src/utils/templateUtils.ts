/**
 * Template utility functions
 */

export interface FieldDefinition {
  name: string
  type: string
  description?: string
  required?: boolean
  default?: any
  constraints?: Record<string, any>
  properties?: FieldDefinition[]
  items?: {
    type: string
    properties?: FieldDefinition[]
  }
}

/**
 * Generate JSON Schema from field definitions
 */
export function generateSchemaFromFields(fieldDefinitions: FieldDefinition[]): any {
  const schema: any = {
    type: 'object',
    properties: {},
    required: []
  }

  for (const field of fieldDefinitions) {
    const fieldSchema: any = {
      type: field.type,
      description: field.description || ''
    }

    // Add constraints
    if (field.constraints) {
      Object.assign(fieldSchema, field.constraints)
    }

    // Handle nested objects
    if (field.type === 'object' && field.properties) {
      const nestedSchema = generateSchemaFromFields(field.properties)
      fieldSchema.properties = nestedSchema.properties
      if (nestedSchema.required && nestedSchema.required.length > 0) {
        fieldSchema.required = nestedSchema.required
      }
    }

    // Handle arrays
    if (field.type === 'array' && field.items) {
      fieldSchema.items = {
        type: field.items.type
      }
      if (field.items.type === 'object' && field.items.properties) {
        const nestedSchema = generateSchemaFromFields(field.items.properties)
        fieldSchema.items.properties = nestedSchema.properties
        if (nestedSchema.required && nestedSchema.required.length > 0) {
          fieldSchema.items.required = nestedSchema.required
        }
      }
    }

    schema.properties[field.name] = fieldSchema

    // Add to required if marked as required
    if (field.required) {
      schema.required.push(field.name)
    }
  }

  return schema
}

/**
 * Validate template data
 */
export function validateTemplateData(template: {
  name: string
  description?: string
  schema: any
  field_definitions: any[]
}): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  // Validate name
  if (!template.name || template.name.trim().length === 0) {
    errors.push('模板名称不能为空')
  } else if (template.name.length > 50) {
    errors.push('模板名称不能超过50个字符')
  }

  // Validate description
  if (template.description && template.description.length > 200) {
    errors.push('模板描述不能超过200个字符')
  }

  // Validate schema
  if (!template.schema || typeof template.schema !== 'object') {
    errors.push('Schema必须是一个有效的对象')
  }

  // Validate field definitions
  if (!Array.isArray(template.field_definitions)) {
    errors.push('字段定义必须是一个数组')
  } else {
    // Check if there's at least one field
    if (template.field_definitions.length === 0) {
      errors.push('至少需要添加一个字段才能创建模板')
    } else {
      // Validate each field
      const fieldNames = new Set<string>()
      let validFieldCount = 0
      
      for (const field of template.field_definitions) {
        if (!field.name || field.name.trim().length === 0) {
          errors.push('字段名称不能为空')
          continue
        }
        
        if (fieldNames.has(field.name)) {
          errors.push(`字段名称 "${field.name}" 重复`)
          continue
        }
        
        if (!field.type) {
          errors.push(`字段 "${field.name}" 必须指定类型`)
          continue
        }
        
        fieldNames.add(field.name)
        validFieldCount++
      }
      
      // Ensure at least one valid field
      if (validFieldCount === 0) {
        errors.push('至少需要有一个有效的字段才能创建模板')
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors
  }
}

/**
 * Format field path for display
 */
export function formatFieldPath(path: string): string {
  return path.replace(/\./g, ' → ')
}
