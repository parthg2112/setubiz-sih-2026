import type { Worker } from 'tesseract.js'

/** On-device OCR.
 *
 *  This module is the whole privacy claim. Tesseract runs as WebAssembly inside the applicant's
 *  own browser, so a caste certificate is read where it already is and no image is ever sent
 *  anywhere. The backend has no route that accepts a file, which is what stops that guarantee
 *  from quietly eroding later.
 *
 *  The engine is loaded lazily, on the first scan only. It is roughly 12 MB with the Devanagari
 *  traineddata, and this app is built for people on constrained connections, so nobody who never
 *  opens the camera pays for it.
 */

let workerPromise: Promise<Worker> | null = null

/** English plus Devanagari: certificates routinely mix both on the same page. */
const LANGS = 'eng+hin'

async function getWorker(onProgress?: (ratio: number) => void): Promise<Worker> {
  if (!workerPromise) {
    workerPromise = import('tesseract.js').then(({ createWorker }) =>
      createWorker(LANGS, 1, {
        logger: (m: { status: string; progress: number }) => {
          if (m.status === 'recognizing text') onProgress?.(m.progress)
        },
      }),
    )
  }
  return workerPromise
}

export interface OcrResult {
  text: string
  /** Tesseract's own mean confidence, 0-100. Low confidence means "check this carefully". */
  confidence: number
}

/** Read text from an image already held in the browser. The blob never leaves this function. */
export async function readImage(
  file: Blob,
  onProgress?: (ratio: number) => void,
): Promise<OcrResult> {
  const worker = await getWorker(onProgress)
  const { data } = await worker.recognize(file)
  return { text: data.text ?? '', confidence: data.confidence ?? 0 }
}

/** Free the worker. Called when the document flow closes, so the tab does not hold ~12 MB open. */
export async function releaseOcr(): Promise<void> {
  if (!workerPromise) return
  const worker = await workerPromise
  workerPromise = null
  await worker.terminate()
}
