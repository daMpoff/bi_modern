/**
 * Общий модуль типов полей и операторов для фильтров (дашборд и пайплайн).
 */
export const FIELD_TYPE_STRING = 'string'
export const FIELD_TYPE_NUMBER = 'number'
export const FIELD_TYPE_DATE = 'date'
export const FIELD_TYPE_BOOLEAN = 'boolean'

const OPERATORS_STRING = [
  { value: '=', label: '=' },
  { value: '!=', label: '!=' },
  { value: 'contains', label: 'Содержит' },
  { value: 'startswith', label: 'Начинается с' },
  { value: 'endswith', label: 'Заканчивается на' },
  { value: 'isnull', label: 'Пустое' },
  { value: 'notnull', label: 'Не пустое' }
]

const OPERATORS_NUMBER_DATE = [
  { value: '=', label: '=' },
  { value: '!=', label: '!=' },
  { value: '>', label: '>' },
  { value: '>=', label: '>=' },
  { value: '<', label: '<' },
  { value: '<=', label: '<=' },
  { value: 'between', label: 'Между' },
  { value: 'isnull', label: 'Пустое' },
  { value: 'notnull', label: 'Не пустое' }
]

const OPERATORS_BOOLEAN = [
  { value: '=', label: '=' },
  { value: '!=', label: '!=' },
  { value: 'isnull', label: 'Пустое' },
  { value: 'notnull', label: 'Не пустое' }
]

const OPERATORS_FALLBACK = [
  ...OPERATORS_STRING,
  { value: '>', label: '>' },
  { value: '>=', label: '>=' },
  { value: '<', label: '<' },
  { value: '<=', label: '<=' },
  { value: 'between', label: 'Между' }
]

export function getOperatorsForFieldType(fieldType) {
  switch (fieldType) {
    case FIELD_TYPE_STRING:
      return OPERATORS_STRING
    case FIELD_TYPE_NUMBER:
    case FIELD_TYPE_DATE:
      return OPERATORS_NUMBER_DATE
    case FIELD_TYPE_BOOLEAN:
      return OPERATORS_BOOLEAN
    default:
      return OPERATORS_FALLBACK
  }
}

export function needsValue(operator) {
  return operator !== 'isnull' && operator !== 'notnull'
}

export function isBetweenOperator(operator) {
  return operator === 'between'
}

export function getValueInputType(fieldType, operator) {
  if (!needsValue(operator)) return null
  if (operator === 'between') return 'between'
  switch (fieldType) {
    case FIELD_TYPE_NUMBER:
      return 'number'
    case FIELD_TYPE_DATE:
      return 'date'
    case FIELD_TYPE_BOOLEAN:
      return 'boolean'
    case FIELD_TYPE_STRING:
    default:
      return 'text'
  }
}

export const BOOLEAN_OPTIONS = [
  { value: true, label: 'Да' },
  { value: false, label: 'Нет' }
]
