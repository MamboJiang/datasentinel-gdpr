import defaultMdxComponents from 'fumadocs-ui/mdx'
import type { MDXComponents } from 'mdx/types'
import {
  DocsScreenshot,
  FastTrack,
  GuideHero,
  HomeTopBar,
  QuickStartHero,
  QuickStartPath,
  ReadinessChecklist,
  SafetyBand,
  SurfaceCards,
  UserTracks,
  VisualTour,
} from './guide-sections'

export function getMDXComponents(components?: MDXComponents): MDXComponents {
  return {
    ...defaultMdxComponents,
    DocsScreenshot,
    FastTrack,
    GuideHero,
    HomeTopBar,
    QuickStartHero,
    QuickStartPath,
    ReadinessChecklist,
    SafetyBand,
    SurfaceCards,
    UserTracks,
    VisualTour,
    ...components,
  }
}
