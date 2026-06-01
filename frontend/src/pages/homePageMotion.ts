import { useEffect, type RefObject } from 'react'

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function useDotGridCanvas(canvasRef: RefObject<HTMLCanvasElement | null>) {
  useEffect(() => {
    const canvas = canvasRef.current
    const context = canvas?.getContext('2d')
    if (!canvas || !context) {
      return
    }

    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const dotSize = 1.35
    const gap = 24
    const proximity = 170
    const hoverStrength = 8
    const shockRadius = 230
    const shockStrength = 12
    const resistance = 0.88
    const returnSpeed = 0.055
    const baseColor = { r: 148, g: 163, b: 184 }
    const activeColor = { r: 11, g: 87, b: 208 }
    const pointer = { active: false, x: -9999, y: -9999 }
    type Dot = {
      originX: number
      originY: number
      xOffset: number
      yOffset: number
      velocityX: number
      velocityY: number
    }
    let dots: Dot[] = []
    let frameId = 0
    let width = 0
    let height = 0

    const setCanvasSize = () => {
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = Math.ceil(width * pixelRatio)
      canvas.height = Math.ceil(height * pixelRatio)
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)

      const columns = Math.ceil(width / gap) + 2
      const rows = Math.ceil(height / gap) + 2
      dots = []

      for (let row = 0; row < rows; row += 1) {
        for (let column = 0; column < columns; column += 1) {
          dots.push({
            originX: column * gap - gap / 2,
            originY: row * gap - gap / 2,
            velocityX: 0,
            velocityY: 0,
            xOffset: 0,
            yOffset: 0,
          })
        }
      }
    }

    const handlePointerMove = (event: WindowEventMap['pointermove']) => {
      if (motionQuery.matches) {
        return
      }

      const rect = canvas.getBoundingClientRect()
      pointer.active = true
      pointer.x = event.clientX - rect.left
      pointer.y = event.clientY - rect.top
    }

    const handlePointerLeave = () => {
      pointer.active = false
      pointer.x = -9999
      pointer.y = -9999
    }

    const handlePointerDown = (event: WindowEventMap['pointerdown']) => {
      if (motionQuery.matches) {
        return
      }

      dots.forEach((dot) => {
        const deltaX = dot.originX - event.clientX
        const deltaY = dot.originY - event.clientY
        const distance = Math.hypot(deltaX, deltaY)

        if (distance > shockRadius || distance === 0) {
          return
        }

        const falloff = 1 - distance / shockRadius
        dot.velocityX += (deltaX / distance) * shockStrength * falloff
        dot.velocityY += (deltaY / distance) * shockStrength * falloff
      })
    }

    const renderDotGrid = () => {
      context.clearRect(0, 0, width, height)

      dots.forEach((dot) => {
        dot.velocityX *= resistance
        dot.velocityY *= resistance
        dot.xOffset += dot.velocityX
        dot.yOffset += dot.velocityY
        dot.xOffset += (0 - dot.xOffset) * returnSpeed
        dot.yOffset += (0 - dot.yOffset) * returnSpeed

        const deltaX = pointer.active ? dot.originX - pointer.x : 0
        const deltaY = pointer.active ? dot.originY - pointer.y : 0
        const distance = pointer.active ? Math.hypot(deltaX, deltaY) : Infinity
        const influence = Math.max(0, 1 - distance / proximity)
        const easedInfluence = influence * influence * (3 - 2 * influence)
        const hoverX = distance > 0 && distance < proximity ? (deltaX / distance) * easedInfluence * hoverStrength : 0
        const hoverY = distance > 0 && distance < proximity ? (deltaY / distance) * easedInfluence * hoverStrength : 0
        const x = dot.originX + dot.xOffset + hoverX
        const y = dot.originY + dot.yOffset + hoverY
        const radius = dotSize + easedInfluence * 2.2
        const opacity = 0.18 + easedInfluence * 0.56
        const red = Math.round(baseColor.r + (activeColor.r - baseColor.r) * easedInfluence)
        const green = Math.round(baseColor.g + (activeColor.g - baseColor.g) * easedInfluence)
        const blue = Math.round(baseColor.b + (activeColor.b - baseColor.b) * easedInfluence)

        context.beginPath()
        context.fillStyle = `rgba(${red}, ${green}, ${blue}, ${opacity})`
        context.arc(x, y, radius, 0, Math.PI * 2)
        context.fill()
      })

      frameId = window.requestAnimationFrame(renderDotGrid)
    }

    setCanvasSize()
    frameId = window.requestAnimationFrame(renderDotGrid)
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerdown', handlePointerDown)
    window.addEventListener('resize', setCanvasSize)
    window.addEventListener('blur', handlePointerLeave)
    document.addEventListener('pointerleave', handlePointerLeave)

    return () => {
      window.cancelAnimationFrame(frameId)
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerdown', handlePointerDown)
      window.removeEventListener('resize', setCanvasSize)
      window.removeEventListener('blur', handlePointerLeave)
      document.removeEventListener('pointerleave', handlePointerLeave)
    }
  }, [canvasRef])
}
