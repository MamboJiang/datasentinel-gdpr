import { useContext } from 'react'
import { DataContext } from './DataContext'

export function useData() {
  const context = useContext(DataContext)

  if (!context) {
    throw new Error('useData must be used inside DataProvider')
  }

  return context
}
