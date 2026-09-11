#!/usr/bin/env node
/**
 * Fails the build if any `ux4g-*` class used in src/ is not defined in the shipped stylesheet.
 *
 * UX4G is a CSS-class contract with no type safety: a misspelled class is not a compile error, it
 * is a silently unstyled control. Design.md section 12 names this as the trade-off of the
 * one-artifact model. This script is the missing compiler.
 *
 * Usage: node scripts/verify-ux4g-classes.mjs
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const CSS = 'node_modules/ux4g-web-components/styles/ux4g.css'
const SRC = 'src'

function walk(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry)
    return statSync(path).isDirectory() ? walk(path) : path.match(/\.tsx?$/) ? [path] : []
  })
}

const css = readFileSync(CSS, 'utf8')
// Every class selector the stylesheet actually defines.
const defined = new Set(css.match(/\.ux4g-[A-Za-z0-9_-]+/g)?.map((s) => s.slice(1)) ?? [])

/** Not classes: the npm package name, and `--ux4g-*` custom properties (which are tokens, and are
 *  parameterised inline by design — see the progress bar's --ux4g-progress-value). */
const NOT_A_CLASS = /^ux4g-web-components/

const problems = []
for (const file of walk(SRC)) {
  const source = readFileSync(file, 'utf8')
  const lines = source.split('\n')
  lines.forEach((line, i) => {
    // Capture the two preceding characters so `--ux4g-foo` can be told from a class name.
    for (const match of line.matchAll(/(^|.{1,2}?)\b(ux4g-[A-Za-z0-9_-]+)/g)) {
      const [, prefix, name] = match
      if (prefix.endsWith('--')) continue
      if (NOT_A_CLASS.test(name)) continue
      // Template-literal interpolation leaves stubs like `ux4g-text-`; the concrete branches are
      // checked separately, so a trailing hyphen is not a finding.
      if (name.endsWith('-')) continue
      if (!defined.has(name)) problems.push(`${file}:${i + 1}  ${name}`)
    }
  })
}

/**
 * Second check: no class from the old Tailwind build survives.
 *
 * A few documented UX4G state classes deliberately carry no prefix — the component contracts call
 * these out as "plain structural state classes included even when they do not start with ux4g-".
 */
const BARE_STATE_CLASSES = new Set([
  'active',
  'collapsed',
  'collapsing',
  'show',
  'is-open',
  'is-selected',
  'is-disabled',
])

const leftovers = []
for (const file of walk(SRC)) {
  if (!file.endsWith('.tsx')) continue
  const lines = readFileSync(file, 'utf8').split('\n')
  lines.forEach((line, i) => {
    for (const match of line.matchAll(/className=(?:"([^"]*)"|\{`([^`]*)`\})/g)) {
      const value = match[1] ?? match[2] ?? ''
      for (const token of value.split(/\s+/)) {
        // Skip interpolation fragments and the punctuation of an inline ternary.
        if (!token || !/^[a-z][a-z0-9_-]*$/.test(token)) continue
        if (token.startsWith('ux4g-') || token.startsWith('setubiz-')) continue
        if (BARE_STATE_CLASSES.has(token)) continue
        leftovers.push(`${file}:${i + 1}  ${token}`)
      }
    }
  })
}

let failed = false
if (problems.length) {
  console.error(`\n${problems.length} undefined UX4G class(es):\n`)
  for (const p of problems) console.error('  ' + p)
  console.error('\nCheck the component contract at https://doc.ux4g.gov.in/web/llms/components.md')
  failed = true
}
if (leftovers.length) {
  console.error(`\n${leftovers.length} non-design-system class(es) still in use:\n`)
  for (const l of leftovers) console.error('  ' + l)
  failed = true
}
if (failed) process.exit(1)

console.log(`All UX4G classes in ${SRC}/ are defined, and no foreign class names remain.`)
