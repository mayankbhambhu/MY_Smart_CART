import { useEffect, useRef, useState } from 'react'

import { cn } from '../lib/cn'

export interface MapPin {
  key: string | number
  aisle: number
  row: number
  step?: number
  status: 'todo' | 'picked' | 'missing' | 'focus'
  title?: string
}

interface StoreMapProps {
  aisles: { number: number; name: string }[]
  rows: number
  pins: MapPin[]
  showRoute?: boolean
  className?: string
}

interface Point {
  x: number
  y: number
}

interface Rect extends Point {
  w: number
  h: number
}

type Lane = 'front' | 'back'

interface Geometry {
  width: number
  height: number
  floor: Rect
  shelf: (aisle: number) => Rect
  divider: (aisle: number, index: number) => { x1: number; y1: number; x2: number; y2: number }
  badge: (aisle: number) => Point
  rowLabel: (row: number) => Point & { anchor: 'start' | 'middle' }
  spot: (aisle: number, row: number) => Point
  lanePoint: (lane: Lane, near: Point) => Point
  isBackHalf: (point: Point) => boolean
  entrance: Rect & { anchor: Point; label: string }
  billing: Rect & { anchor: Point }
}

/** Floor plan with aisles as columns and the entrance at the bottom (wide screens). */
function verticalGeometry(count: number, rows: number): Geometry {
  const LEFT = 36
  const TOP = 54
  const AISLE = 58
  const ROW = 34
  const INSET = 9
  const floorBottom = TOP + rows * ROW
  const width = LEFT + count * AISLE + 14
  const centerX = (aisle: number) => LEFT + (aisle - 1) * AISLE + AISLE / 2
  const billingX = LEFT + count * AISLE - 30
  return {
    width,
    height: floorBottom + 70,
    floor: { x: 4, y: 8, w: width - 8, h: floorBottom + 50 },
    shelf: (aisle) => ({ x: LEFT + (aisle - 1) * AISLE + INSET, y: TOP, w: AISLE - INSET * 2, h: rows * ROW }),
    divider: (aisle, i) => {
      const x = LEFT + (aisle - 1) * AISLE + INSET
      return { x1: x, x2: x + AISLE - INSET * 2, y1: TOP + i * ROW, y2: TOP + i * ROW }
    },
    badge: (aisle) => ({ x: centerX(aisle), y: TOP - 30 }),
    rowLabel: (row) => ({ x: LEFT - 24, y: floorBottom - (row - 0.5) * ROW + 4, anchor: 'start' }),
    spot: (aisle, row) => ({ x: centerX(aisle), y: floorBottom - (row - 0.5) * ROW }),
    lanePoint: (lane, near) => ({ x: near.x, y: lane === 'front' ? floorBottom + 10 : TOP - 9 }),
    isBackHalf: (point) => point.y < (TOP + floorBottom) / 2,
    entrance: { x: LEFT - 30, y: floorBottom + 32, w: 66, h: 22, anchor: { x: LEFT - 14, y: floorBottom + 24 }, label: '⬆ Entrance' },
    billing: { x: billingX - 34, y: floorBottom + 32, w: 68, h: 22, anchor: { x: billingX, y: floorBottom + 24 } },
  }
}

/** The same plan turned sideways — aisles stacked top to bottom — so it fits a phone screen. */
function horizontalGeometry(count: number, rows: number): Geometry {
  const LEFT = 52
  const TOP = 40
  const AISLE = 44
  const ROW = 40
  const INSET = 8
  const floorRight = LEFT + rows * ROW
  const floorBottom = TOP + count * AISLE
  const centerY = (aisle: number) => TOP + (aisle - 1) * AISLE + AISLE / 2
  return {
    width: floorRight + 22,
    height: floorBottom + 40,
    floor: { x: 2, y: 2, w: floorRight + 18, h: floorBottom + 34 },
    shelf: (aisle) => ({ x: LEFT, y: TOP + (aisle - 1) * AISLE + INSET, w: rows * ROW, h: AISLE - INSET * 2 }),
    divider: (aisle, i) => {
      const y = TOP + (aisle - 1) * AISLE + INSET
      return { x1: LEFT + i * ROW, x2: LEFT + i * ROW, y1: y, y2: y + AISLE - INSET * 2 }
    },
    badge: (aisle) => ({ x: 16, y: centerY(aisle) }),
    rowLabel: (row) => ({ x: LEFT + (row - 0.5) * ROW, y: TOP - 10, anchor: 'middle' }),
    spot: (aisle, row) => ({ x: LEFT + (row - 0.5) * ROW, y: centerY(aisle) }),
    lanePoint: (lane, near) => ({ x: lane === 'front' ? LEFT - 10 : floorRight + 10, y: near.y }),
    isBackHalf: (point) => point.x > (LEFT + floorRight) / 2,
    entrance: { x: 4, y: 6, w: 62, h: 20, anchor: { x: LEFT - 10, y: TOP - 4 }, label: 'Entrance' },
    billing: { x: 4, y: floorBottom + 10, w: 62, h: 20, anchor: { x: LEFT - 10, y: floorBottom + 6 } },
  }
}

const PIN_COLORS: Record<MapPin['status'], string> = {
  todo: '#4f46e5',
  picked: '#0c831f',
  missing: '#9ca3af',
  focus: '#e11d48',
}

/**
 * Schematic floor plan of a store. Rows run from the front of each aisle (row 1, next to the
 * entrance) to the back. Pins mark items; the dashed line is the suggested walking route from
 * the entrance to the billing counter. Wide containers get the upright plan, narrow ones the
 * sideways plan, so nothing needs horizontal scrolling on a phone.
 */
export function StoreMap({ aisles, rows, pins, showRoute = true, className }: StoreMapProps) {
  const wrapper = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(0)
  useEffect(() => {
    const element = wrapper.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => setContainerWidth(entry.contentRect.width))
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  const count = Math.max(aisles.length, 1)
  const upright = verticalGeometry(count, rows)
  const vertical = containerWidth >= upright.width * 0.85
  const g = vertical ? upright : horizontalGeometry(count, rows)

  // Pins that share a shelf cell fan out sideways so their numbers stay readable.
  const cellOf = (pin: MapPin) => `${pin.aisle}:${pin.row}`
  const totals = new Map<string, number>()
  for (const pin of pins) totals.set(cellOf(pin), (totals.get(cellOf(pin)) ?? 0) + 1)
  const seen = new Map<string, number>()
  const placed = pins.map((pin) => {
    const index = seen.get(cellOf(pin)) ?? 0
    seen.set(cellOf(pin), index + 1)
    const total = totals.get(cellOf(pin)) ?? 1
    const center = g.spot(pin.aisle, pin.row)
    return { pin, x: center.x + (total > 1 ? (index - (total - 1) / 2) * 13 : 0), y: center.y }
  })

  const ordered = placed.filter((p) => p.pin.step != null).sort((a, b) => (a.pin.step ?? 0) - (b.pin.step ?? 0))
  const points: Point[] = [g.entrance.anchor]
  let lane: Lane = 'front'
  let previousAisle: number | null = null
  for (const stop of ordered) {
    const last = points[points.length - 1]
    if (previousAisle !== stop.pin.aisle) points.push(g.lanePoint(lane, last), g.lanePoint(lane, stop))
    points.push({ x: stop.x, y: stop.y })
    previousAisle = stop.pin.aisle
    // Cross to the next aisle at whichever end of this one the shopper is nearer.
    lane = g.isBackHalf(stop) ? 'back' : 'front'
  }
  if (ordered.length) {
    const last = points[points.length - 1]
    points.push(g.lanePoint('front', last), g.lanePoint('front', g.billing.anchor), g.billing.anchor)
  }

  const visited = new Set(pins.map((p) => p.aisle))

  return (
    <div ref={wrapper} className={cn('w-full', className)}>
      <svg
        viewBox={`0 0 ${g.width} ${g.height}`}
        className={cn('mx-auto h-auto w-full', !vertical && 'max-w-[380px]')}
        role="img"
        aria-label={`Store map with ${pins.length} marked ${pins.length === 1 ? 'item' : 'items'}`}
      >
        <rect x={g.floor.x} y={g.floor.y} width={g.floor.w} height={g.floor.h} rx={14} fill="#f8fafc" stroke="#e2e8f0" />

        {Array.from({ length: rows }, (_, i) => {
          const label = g.rowLabel(i + 1)
          return (
            <text key={i} x={label.x} y={label.y} textAnchor={label.anchor} fontSize={10} fill="#94a3b8" fontWeight={600}>
              R{i + 1}
            </text>
          )
        })}

        {aisles.map((aisle) => {
          const shelf = g.shelf(aisle.number)
          const badge = g.badge(aisle.number)
          const active = visited.has(aisle.number)
          return (
            <g key={aisle.number}>
              <title>{`Aisle ${aisle.number}: ${aisle.name}`}</title>
              <rect
                x={shelf.x}
                y={shelf.y}
                width={shelf.w}
                height={shelf.h}
                rx={6}
                fill={active ? '#e0e7ff' : '#e2e8f0'}
                stroke={active ? '#a5b4fc' : '#cbd5e1'}
              />
              {Array.from({ length: rows - 1 }, (_, i) => {
                const line = g.divider(aisle.number, i + 1)
                return <line key={i} {...line} stroke={active ? '#c7d2fe' : '#cbd5e1'} />
              })}
              <circle cx={badge.x} cy={badge.y} r={10} fill={active ? '#4f46e5' : '#cbd5e1'} />
              <text x={badge.x} y={badge.y + 3.6} textAnchor="middle" fontSize={10.5} fontWeight={800} fill={active ? '#ffffff' : '#475569'}>
                {aisle.number}
              </text>
            </g>
          )
        })}

        {showRoute && ordered.length > 0 && (
          <polyline
            points={points.map((p) => `${p.x},${p.y}`).join(' ')}
            fill="none"
            stroke="#6366f1"
            strokeWidth={2.5}
            strokeDasharray="6 5"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={0.85}
          />
        )}

        <rect x={g.entrance.x} y={g.entrance.y} width={g.entrance.w} height={g.entrance.h} rx={6} fill="#dcfce7" />
        <text x={g.entrance.x + g.entrance.w / 2} y={g.entrance.y + g.entrance.h / 2 + 3.5} textAnchor="middle" fontSize={10} fontWeight={700} fill="#166534">
          {g.entrance.label}
        </text>
        <rect x={g.billing.x} y={g.billing.y} width={g.billing.w} height={g.billing.h} rx={6} fill="#fef3c7" />
        <text x={g.billing.x + g.billing.w / 2} y={g.billing.y + g.billing.h / 2 + 3.5} textAnchor="middle" fontSize={10} fontWeight={700} fill="#92400e">
          Billing
        </text>

        {placed.map(({ pin, x, y }) => (
          <g key={pin.key}>
            {pin.title && <title>{pin.title}</title>}
            {pin.status === 'focus' && (
              <circle cx={x} cy={y} r={16} fill={PIN_COLORS.focus} opacity={0.18} className="animate-ping" style={{ transformOrigin: `${x}px ${y}px` }} />
            )}
            <circle cx={x} cy={y} r={11} fill={PIN_COLORS[pin.status]} stroke="#ffffff" strokeWidth={2} />
            <text x={x} y={y + 3.8} textAnchor="middle" fontSize={10.5} fontWeight={800} fill="#ffffff">
              {pin.status === 'picked' ? '✓' : (pin.step ?? '•')}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}
