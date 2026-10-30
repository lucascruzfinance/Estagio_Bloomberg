import type { ReasonOut } from '../api/types'

const SIGN: Record<string, { text: string; className: string; label: string }> = {
  '+': { text: '+', className: 'reason__sign--plus', label: 'favorável' },
  '-': { text: '−', className: 'reason__sign--minus', label: 'desfavorável' },
  '?': { text: '?', className: 'reason__sign--missing', label: 'sem evidência' },
  '~': { text: '~', className: 'reason__sign--assumed', label: 'premissa' },
}

const ORDER = ['+', '-', '~', '?']

export function ReasonList({ reasons, limit }: { reasons: ReasonOut[]; limit?: number }) {
  const sorted = [...reasons].sort(
    (a, b) => ORDER.indexOf(a.polarity) - ORDER.indexOf(b.polarity) || (b.points ?? 0) - (a.points ?? 0),
  )
  const visible = limit ? sorted.slice(0, limit) : sorted
  return (
    <ul className="reasons">
      {visible.map((reason) => {
        const sign = SIGN[reason.polarity] ?? SIGN['?']!
        return (
          <li key={reason.code} className="reason">
            <span className={`reason__sign ${sign.className}`} aria-label={sign.label} title={reason.code}>
              {sign.text}
            </span>
            <span>{reason.text}</span>
            <span className="reason__points">
              {reason.points === null || reason.points === undefined ? '' : `${reason.points.toFixed(1).replace('.', ',')} pts`}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
