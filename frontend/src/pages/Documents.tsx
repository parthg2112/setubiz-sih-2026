import { useCallback, useEffect, useRef, useState } from 'react'
import {
  api,
  type DocumentCheckResult,
  type DocumentFields,
  type DocumentKind,
  type QuotedLineInput,
} from '../api'
import { inr, type Strings } from '../format'
import { readImage, releaseOcr } from '../ocr'
import type { Language } from '../types'

interface Props {
  language: Language
  strings: Strings
}

type Stage = 'capture' | 'reading' | 'confirm' | 'result'

const digits = (s: string) => Number(String(s).replace(/[^\d]/g, '')) || 0

/** The document readiness flow.
 *
 *  Three rules shape this screen, all from the spec:
 *
 *  1. The image never leaves the device. OCR is WebAssembly in this browser, and the backend has
 *     no route that accepts a file, so the guarantee cannot erode by accident later.
 *  2. Nothing is checked until the applicant has confirmed it. Extraction is calibrated on typed
 *     text rather than photographs, so a misread has to degrade into a form field rather than
 *     into a wrong verdict.
 *  3. Nothing is auto-rejected. A red finding means stop and fix, and a person decides.
 */
export function Documents({ language, strings }: Props) {
  const [stage, setStage] = useState<Stage>('capture')
  const [kind, setKind] = useState<DocumentKind>('unknown')
  const [fields, setFields] = useState<DocumentFields>({})
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DocumentCheckResult | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement | null>(null)

  // The worker holds roughly 12 MB; let it go when the applicant leaves this screen.
  useEffect(() => () => void releaseOcr(), [])
  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview)
  }, [preview])

  const scan = useCallback(
    async (file: File) => {
      setError(null)
      setStage('reading')
      setProgress(0)
      // Shown back to the applicant so they can see whether the photo is legible at all. It is an
      // object URL into this tab's memory, never an upload.
      setPreview((old) => {
        if (old) URL.revokeObjectURL(old)
        return URL.createObjectURL(file)
      })
      try {
        const { text } = await readImage(file, setProgress)
        const read = await api.documentsRead(text)
        setKind(read.kind)
        setFields(read.proposed ?? {})
        setStage('confirm')
      } catch {
        setError(strings.docReadFailed)
        setStage('capture')
      }
    },
    [strings],
  )

  async function check() {
    const body: Record<string, unknown> = {
      kind: kind === 'unknown' ? 'quotation' : kind,
      business_category: 'dairy',
      social_category: 'sc',
      margin: 100000,
    }
    if (kind === 'income_certificate') body.income_certificate = fields
    else if (kind === 'caste_certificate') body.caste_certificate = fields
    else body.quotation = fields
    try {
      setResult(await api.documentsCheck(body))
      setStage('result')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const kindLabel =
    kind === 'quotation'
      ? strings.docKindQuotation
      : kind === 'income_certificate'
        ? strings.docKindIncome
        : kind === 'caste_certificate'
          ? strings.docKindCaste
          : strings.docKindUnknown

  return (
    <div className="ux4g-container ux4g-py-xl">
      <h1 className="ux4g-heading-xl-strong">{strings.docTitle}</h1>
      <p className="ux4g-body-l-default setubiz-measure ux4g-mt-xs">{strings.docHelp}</p>

      {/* Stated at the point of upload, in the reader's language, not buried in a policy page. */}
      <div className="ux4g-alert ux4g-alert-info ux4g-mt-m" role="note">
        <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
          lock
        </span>
        <div className="ux4g-alert-content">
          <p className="ux4g-alert-message setubiz-measure">{strings.docPrivacy}</p>
        </div>
      </div>

      {error && (
        <div className="ux4g-alert ux4g-alert-error ux4g-mt-m" role="alert">
          <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
            error
          </span>
          <div className="ux4g-alert-content">
            <p className="ux4g-alert-message setubiz-measure">{error}</p>
          </div>
        </div>
      )}

      {(stage === 'capture' || stage === 'reading') && (
        <div className="ux4g-card ux4g-card-outline ux4g-mt-l">
          <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
            <input
              ref={fileInput}
              className="ux4g-d-none"
              type="file"
              accept="image/*"
              capture="environment"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) void scan(file)
                e.target.value = ''
              }}
            />
            <button
              type="button"
              className="ux4g-btn ux4g-btn-primary ux4g-btn-lg ux4g-gap-x-xs"
              disabled={stage === 'reading'}
              onClick={() => fileInput.current?.click()}
            >
              <span className="ux4g-icon-outlined" aria-hidden="true">
                photo_camera
              </span>
              {strings.docScan}
            </button>

            {stage === 'reading' && (
              <div role="status" className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
                <p className="ux4g-body-l-default ux4g-d-flex ux4g-ai-center ux4g-gap-x-s">
                  <span className="ux4g-spinner ux4g-spinner-sm" aria-hidden="true" />
                  {strings.docReading}
                </p>
                <div className="ux4g-progress-bar">
                  <div className="ux4g-progress-bar-track">
                    <div
                      className="ux4g-progress-bar-fill"
                      style={{ '--ux4g-progress-value': Math.round(progress * 100) } as never}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {stage === 'confirm' && (
        <Confirm
          kind={kind}
          kindLabel={kindLabel}
          fields={fields}
          preview={preview}
          language={language}
          strings={strings}
          onChange={setFields}
          onRetake={() => setStage('capture')}
          onConfirm={() => void check()}
        />
      )}

      {stage === 'result' && result && (
        <Results
          result={result}
          language={language}
          strings={strings}
          onRetake={() => {
            setResult(null)
            setStage('capture')
          }}
        />
      )}
    </div>
  )
}

function Confirm({
  kind,
  kindLabel,
  fields,
  preview,
  language,
  strings,
  onChange,
  onRetake,
  onConfirm,
}: {
  kind: DocumentKind
  kindLabel: string
  fields: DocumentFields
  preview: string | null
  language: Language
  strings: Strings
  onChange: (f: DocumentFields) => void
  onRetake: () => void
  onConfirm: () => void
}) {
  const lines = fields.lines ?? []

  function setLine(index: number, patch: Partial<QuotedLineInput>) {
    onChange({
      ...fields,
      lines: lines.map((l, i) => (i === index ? { ...l, ...patch } : l)),
    })
  }

  return (
    <section className="ux4g-card ux4g-card-outline ux4g-card-vertical ux4g-mt-l">
      <div className="ux4g-card-header">
        <h2 className="ux4g-heading-m-strong ux4g-card-title">{strings.docConfirmTitle}</h2>
        <p className="ux4g-body-l-default ux4g-card-sub-title setubiz-measure">
          {strings.docKind} {kindLabel}. {strings.docConfirmHelp}
        </p>
      </div>

      <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
        <div className="ux4g-alert ux4g-alert-warning" role="note">
          <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
            visibility
          </span>
          <div className="ux4g-alert-content">
            <p className="ux4g-alert-message setubiz-measure">{strings.docUnvalidated}</p>
          </div>
        </div>

        {preview && (
          <img
            className="setubiz-preview"
            src={preview}
            alt={kindLabel}
            /* Rendered from this tab's own memory. It is never uploaded and never persisted. */
          />
        )}

        {kind === 'quotation' ? (
          <>
            <Text
              id="vendor"
              label={strings.docVendor}
              value={fields.vendor_name ?? ''}
              onChange={(v) => onChange({ ...fields, vendor_name: v })}
            />
            <Text
              id="qdate"
              label={strings.docQuotationDate}
              value={fields.quotation_date ?? ''}
              onChange={(v) => onChange({ ...fields, quotation_date: v })}
            />
            <div className="ux4g-table-responsive">
              <table className="ux4g-table ux4g-table-m ux4g-table-rounded">
                <thead>
                  <tr>
                    <th scope="col">
                      <span className="ux4g-table-th-content">{strings.docLine}</span>
                    </th>
                    <th scope="col">
                      <span className="ux4g-table-th-content">{strings.docTotal}</span>
                    </th>
                    <th scope="col">
                      <span className="ux4g-table-th-content">{strings.docRemove}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {lines.map((line, i) => (
                    <tr key={i}>
                      <td>
                        <input
                          className="ux4g-input-input"
                          type="text"
                          aria-label={strings.docLine}
                          value={line.description}
                          onChange={(e) => setLine(i, { description: e.target.value })}
                        />
                      </td>
                      <td>
                        <input
                          className="ux4g-input-input setubiz-tabular"
                          type="text"
                          inputMode="numeric"
                          aria-label={strings.docTotal}
                          value={String(line.amount ?? '')}
                          onChange={(e) => setLine(i, { amount: digits(e.target.value) })}
                        />
                      </td>
                      <td>
                        <button
                          type="button"
                          className="ux4g-btn ux4g-btn-text-danger ux4g-btn-lg"
                          onClick={() =>
                            onChange({ ...fields, lines: lines.filter((_, j) => j !== i) })
                          }
                        >
                          {strings.docRemove}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button
              type="button"
              className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
              onClick={() =>
                onChange({ ...fields, lines: [...lines, { description: '', amount: 0 }] })
              }
            >
              {strings.docAddLine}
            </button>
            <Money
              id="total"
              label={strings.docTotal}
              value={fields.total_amount ?? 0}
              onChange={(v) => onChange({ ...fields, total_amount: v })}
            />
          </>
        ) : (
          <>
            <Text
              id="name"
              label={strings.memberName}
              value={fields.applicant_name ?? ''}
              onChange={(v) => onChange({ ...fields, applicant_name: v })}
            />
            {kind === 'income_certificate' && (
              <Money
                id="income"
                label={strings.income}
                value={fields.annual_family_income ?? 0}
                onChange={(v) => onChange({ ...fields, annual_family_income: v })}
              />
            )}
            {kind === 'caste_certificate' && (
              <div className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
                <label className="ux4g-label-l-strong" htmlFor="category">
                  {strings.docCategory}
                </label>
                <select
                  id="category"
                  className="ux4g-form-select ux4g-form-select-lg"
                  value={fields.category ?? ''}
                  onChange={(e) => onChange({ ...fields, category: e.target.value })}
                >
                  <option value="">{strings.docAbsent}</option>
                  {['sc', 'st', 'obc', 'ebc', 'safai_karamchari'].map((c) => (
                    <option key={c} value={c}>
                      {c.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <Text
              id="authority"
              label={strings.docAuthority}
              value={fields.issuing_authority ?? ''}
              onChange={(v) => onChange({ ...fields, issuing_authority: v })}
            />
            <Text
              id="certno"
              label={strings.docCertNumber}
              value={fields.certificate_number ?? ''}
              onChange={(v) => onChange({ ...fields, certificate_number: v })}
            />
            {kind === 'caste_certificate' && (
              <label className="ux4g-checkbox ux4g-checkbox-md">
                <input
                  className="ux4g-checkbox-input"
                  type="checkbox"
                  checked={fields.attestation_present ?? false}
                  onChange={(e) => onChange({ ...fields, attestation_present: e.target.checked })}
                />
                <div className="ux4g-checkbox-control">
                  <span className="ux4g-checkmark" />
                </div>
                <div className="ux4g-checkbox-content">
                  <div className="ux4g-checkbox-header">
                    <span className="ux4g-checkbox-label">{strings.docAttestation}</span>
                  </div>
                </div>
              </label>
            )}
          </>
        )}
      </div>

      <div className="ux4g-card-footer ux4g-d-flex ux4g-jc-between ux4g-gap-x-m ux4g-flex-wrap">
        <button
          type="button"
          className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
          onClick={onRetake}
          lang={language}
        >
          {strings.docRetake}
        </button>
        <button
          type="button"
          className="ux4g-btn ux4g-btn-primary ux4g-btn-lg"
          onClick={onConfirm}
        >
          {strings.docConfirm}
        </button>
      </div>
    </section>
  )
}

function Results({
  result,
  language,
  strings,
  onRetake,
}: {
  result: DocumentCheckResult
  language: Language
  strings: Strings
  onRetake: () => void
}) {
  const heading =
    result.severity === 'ok'
      ? strings.docReady
      : result.severity === 'warning'
        ? strings.docNeedsWork
        : strings.docNotReady
  const tone =
    result.severity === 'ok' ? 'success' : result.severity === 'warning' ? 'warning' : 'error'

  return (
    <section
      className="ux4g-card ux4g-card-outline ux4g-card-vertical ux4g-mt-l setubiz-print-block"
      aria-labelledby="doc-result"
    >
      <div className="ux4g-card-header">
        {/* Icon and word, never colour alone. */}
        <h2
          className="ux4g-heading-m-strong ux4g-card-title ux4g-d-flex ux4g-ai-center ux4g-gap-x-xs"
          id="doc-result"
        >
          <span className={`ux4g-icon-outlined ux4g-text-${tone}`} aria-hidden="true">
            {result.severity === 'ok' ? 'check_circle' : result.severity === 'warning' ? 'error' : 'cancel'}
          </span>
          {heading}
        </h2>
      </div>

      <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
        <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
          {result.checks.map((c) => (
            <li className="ux4g-d-flex ux4g-ai-start ux4g-gap-x-s" key={c.id}>
              <span
                className={`ux4g-tag-tonal-${
                  c.severity === 'ok' ? 'success' : c.severity === 'warning' ? 'warning' : 'error'
                } ux4g-tag-s`}
              >
                <span className="ux4g-icon-outlined" aria-hidden="true">
                  {c.severity === 'ok' ? 'check' : c.severity === 'warning' ? 'error' : 'cancel'}
                </span>
              </span>
              <span className="ux4g-body-l-default setubiz-measure">
                {language === 'hi' ? c.text_hi : c.text_en}
              </span>
            </li>
          ))}
        </ul>

        {result.matched_lines.length > 0 && (
          <div className="ux4g-table-responsive">
            <table className="ux4g-table ux4g-table-m ux4g-table-zebra-rows ux4g-table-rounded">
              <thead>
                <tr>
                  <th scope="col">
                    <span className="ux4g-table-th-content">{strings.docLine}</span>
                  </th>
                  <th scope="col">
                    <span className="ux4g-table-th-content">{strings.docNorm}</span>
                  </th>
                  <th scope="col">
                    <span className="ux4g-table-th-content">{strings.docExcess}</span>
                  </th>
                </tr>
              </thead>
              <tbody className="setubiz-tabular">
                {result.matched_lines.map((m, i) => (
                  <tr key={i}>
                    <th scope="row">
                      {m.quoted.description}
                      <br />
                      {inr(m.quoted.amount)}
                    </th>
                    <td>
                      {m.template_amount ? (
                        <>
                          {m.template_item}
                          <br />
                          {inr(m.template_amount)}
                        </>
                      ) : (
                        strings.docUnmatched
                      )}
                    </td>
                    <td>
                      {m.excess_pct === null ? (
                        '-'
                      ) : (
                        <span
                          className={`ux4g-tag-tonal-${
                            m.severity === 'ok'
                              ? 'success'
                              : m.severity === 'warning'
                                ? 'warning'
                                : 'error'
                          } ux4g-tag-s`}
                        >
                          {Number(m.excess_pct) > 0 ? '+' : ''}
                          {m.excess_pct}%
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="ux4g-card-footer setubiz-no-print">
        <button
          type="button"
          className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
          onClick={onRetake}
        >
          {strings.docCheckAgain}
        </button>
      </div>
    </section>
  )
}

function Text({
  id,
  label,
  value,
  onChange,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="ux4g-input-container ux4g-input-lg">
      <label className="ux4g-label-l-strong" htmlFor={id}>
        {label}
      </label>
      <div className="ux4g-input">
        <input
          id={id}
          className="ux4g-input-input"
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    </div>
  )
}

function Money({
  id,
  label,
  value,
  onChange,
}: {
  id: string
  label: string
  value: number
  onChange: (v: number) => void
}) {
  return (
    <div className="ux4g-input-container ux4g-input-lg">
      <label className="ux4g-label-l-strong" htmlFor={id}>
        {label}
      </label>
      <div className="ux4g-input">
        <span className="ux4g-icon-outlined ux4g-input-leading-icon" aria-hidden="true">
          currency_rupee
        </span>
        <input
          id={id}
          className="ux4g-input-input setubiz-tabular"
          type="text"
          inputMode="numeric"
          value={String(value || '')}
          onChange={(e) => onChange(digits(e.target.value))}
        />
      </div>
      <div className="ux4g-input-helper">
        <span className="ux4g-input-helper-text setubiz-tabular">{inr(value)}</span>
      </div>
    </div>
  )
}
