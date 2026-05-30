import { useEffect, useRef, useState } from 'react'
import './SidebarResizeHandle.css'

export const SIDEBAR_COLLAPSED_WIDTH = 74
export const SIDEBAR_DEFAULT_WIDTH = 260
export const SIDEBAR_MIN_EXPANDED_WIDTH = 220
export const SIDEBAR_MAX_WIDTH = 360
export const SIDEBAR_COLLAPSE_THRESHOLD = 180

const KEYBOARD_STEP = 20

function clampExpandedWidth(width: number) {
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_EXPANDED_WIDTH, width))
}

function getNextState(rawWidth: number) {
  if (rawWidth < SIDEBAR_COLLAPSE_THRESHOLD) {
    return {
      collapsed: true,
      width: SIDEBAR_COLLAPSED_WIDTH,
    }
  }

  return {
    collapsed: false,
    width: clampExpandedWidth(rawWidth),
  }
}

export function SidebarResizeHandle({
  collapsed,
  onInteractionStart,
  onResize,
  width,
}: {
  collapsed: boolean
  onInteractionStart: () => void
  onResize: (next: { collapsed: boolean; width: number }) => void
  width: number
}) {
  const [dragging, setDragging] = useState(false)
  const latestWidth = useRef(width)
  const latestCollapsed = useRef(collapsed)
  const onResizeRef = useRef(onResize)

  useEffect(() => {
    latestWidth.current = width
    latestCollapsed.current = collapsed
  }, [collapsed, width])

  useEffect(() => {
    onResizeRef.current = onResize
  }, [onResize])

  useEffect(() => {
    if (!dragging) {
      return
    }

    function handlePointerMove(event: PointerEvent) {
      event.preventDefault()
      onResizeRef.current(getNextState(event.clientX))
    }

    function stopDragging() {
      setDragging(false)
      document.body.classList.remove('sidebar-resizing')
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        stopDragging()
      }
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', stopDragging)
    window.addEventListener('keydown', handleKeyDown)
    document.body.classList.add('sidebar-resizing')

    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', stopDragging)
      window.removeEventListener('keydown', handleKeyDown)
      document.body.classList.remove('sidebar-resizing')
    }
  }, [dragging])

  function resizeByKeyboard(rawWidth: number) {
    onInteractionStart()
    onResize(getNextState(rawWidth))
  }

  const currentWidth = collapsed ? SIDEBAR_COLLAPSED_WIDTH : width

  return (
    <button
      aria-label="Resize sidebar"
      aria-orientation="vertical"
      aria-valuemax={SIDEBAR_MAX_WIDTH}
      aria-valuemin={SIDEBAR_COLLAPSED_WIDTH}
      aria-valuenow={currentWidth}
      className={`sidebar-resize-handle ${dragging ? 'sidebar-resize-handle-active' : ''}`}
      onKeyDown={(event) => {
        if (event.key === 'ArrowLeft') {
          event.preventDefault()
          resizeByKeyboard(latestCollapsed.current ? SIDEBAR_COLLAPSED_WIDTH : latestWidth.current - KEYBOARD_STEP)
        }

        if (event.key === 'ArrowRight') {
          event.preventDefault()
          resizeByKeyboard(latestCollapsed.current ? SIDEBAR_MIN_EXPANDED_WIDTH : latestWidth.current + KEYBOARD_STEP)
        }

        if (event.key === 'Home') {
          event.preventDefault()
          resizeByKeyboard(SIDEBAR_COLLAPSED_WIDTH)
        }

        if (event.key === 'End') {
          event.preventDefault()
          resizeByKeyboard(SIDEBAR_MAX_WIDTH)
        }

        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          resizeByKeyboard(latestCollapsed.current ? latestWidth.current : SIDEBAR_COLLAPSED_WIDTH)
        }
      }}
      onPointerDown={(event) => {
        if (event.button !== 0) {
          return
        }

        event.preventDefault()
        onInteractionStart()
        setDragging(true)
      }}
      role="separator"
      type="button"
    />
  )
}
