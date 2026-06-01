import { useEffect, useState, type CSSProperties } from 'react'
import { prefersReducedMotion } from './homePageMotion'

type TrueFocusProps = {
  animationDuration?: number
  blurAmount?: number
  borderColor?: string
  className?: string
  glowColor?: string
  manualMode?: boolean
  pauseBetweenAnimations?: number
  sentence: string
}

export function TrueFocus({
  animationDuration = 0.45,
  blurAmount = 2.4,
  borderColor = 'rgba(11, 87, 208, .52)',
  className = '',
  glowColor = 'rgba(11, 87, 208, .14)',
  manualMode = false,
  pauseBetweenAnimations = 1.1,
  sentence,
}: TrueFocusProps) {
  const words = sentence.split(' ')
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    if (manualMode || words.length <= 1 || prefersReducedMotion()) return undefined

    const interval = window.setInterval(() => {
      setActiveIndex((index) => (index + 1) % words.length)
    }, (animationDuration + pauseBetweenAnimations) * 1000)

    return () => window.clearInterval(interval)
  }, [animationDuration, manualMode, pauseBetweenAnimations, words.length])

  return (
    <span
      aria-label={sentence}
      className={`landing-true-focus ${className}`.trim()}
      role="text"
      style={{
        '--true-focus-blur': `${blurAmount}px`,
        '--true-focus-border': borderColor,
        '--true-focus-duration': `${animationDuration}s`,
        '--true-focus-glow': glowColor,
      } as CSSProperties}
    >
      {words.map((word, index) => (
        <span
          aria-hidden="true"
          className={`landing-true-focus-word${index === activeIndex ? ' landing-true-focus-word-active' : ''}`}
          key={`${word}-${index}`}
        >
          <span>{word}</span>
        </span>
      ))}
    </span>
  )
}
