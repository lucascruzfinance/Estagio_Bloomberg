import { date } from '../lib/format'

const PUBLISHER: Record<string, string> = {
  cvm_cad_adm_cart: 'Cadastro de gestores (CVM)',
  cvm_registro_fundo_classe: 'Registro de fundos (CVM)',
  cvm_inf_diario: 'Informe diário (CVM)',
  osm_nominatim: 'Nominatim (OpenStreetMap)',
  model_config: 'Modelo de priorização',
  curated_signal: 'Sinal curado',
  workbook: 'Planilha de networking',
}

interface Source {
  source_type: string
  url?: string | null
  as_of_date?: string | null
  collected_at?: string | null
}

export function sourceName(type: string): string {
  return PUBLISHER[type] ?? type
}

export function SourceLink({ source }: { source: Source }) {
  const name = sourceName(source.source_type)
  const when = source.as_of_date ? ` (${date(source.as_of_date)})` : ''
  if (source.url && /^https?:\/\//.test(source.url)) {
    return (
      <a href={source.url} target="_blank" rel="noreferrer noopener" title={source.url}>
        {name}
        {when}
      </a>
    )
  }
  return (
    <span className="secondary">
      {name}
      {when}
    </span>
  )
}

/** Evidence strings carry "Publisher …: url" — render any URL as a link. */
export function EvidenceText({ text }: { text: string }) {
  const match = text.match(/https?:\/\/\S+/)
  if (!match) return <span>{text}</span>
  const [url] = match
  const [before, after] = text.split(url)
  return (
    <span>
      {before}
      <a href={url} target="_blank" rel="noreferrer noopener">
        {new URL(url).hostname}
      </a>
      {after}
    </span>
  )
}
