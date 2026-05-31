import type { GoogleDrivePickerConfig } from './serverApi'

export type GoogleDrivePickerMode = 'files' | 'folders'

export type GoogleDrivePickedItem = {
  id: string
  mimeType: string
  name: string
  url?: string
}

type TokenResponse = {
  access_token?: string
  error?: string
}

type TokenClient = {
  callback: (response: TokenResponse) => void
  requestAccessToken: (options: { prompt: string }) => void
}

type DocsViewLike = {
  setEnableDrives: (enabled: boolean) => DocsViewLike
  setIncludeFolders: (included: boolean) => DocsViewLike
  setMode: (mode: string) => DocsViewLike
  setSelectFolderEnabled: (enabled: boolean) => DocsViewLike
}

type PickerLike = {
  setVisible: (visible: boolean) => void
}

type PickerBuilderLike = {
  addView: (view: DocsViewLike) => PickerBuilderLike
  build: () => PickerLike
  enableFeature: (feature: string) => PickerBuilderLike
  setAppId: (appId: string) => PickerBuilderLike
  setCallback: (callback: (data: Record<string, unknown>) => void) => PickerBuilderLike
  setDeveloperKey: (apiKey: string) => PickerBuilderLike
  setOAuthToken: (token: string) => PickerBuilderLike
}

type GoogleLike = {
  accounts?: {
    oauth2?: {
      initTokenClient: (options: { callback: (response: TokenResponse) => void, client_id: string, scope: string }) => TokenClient
    }
  }
  picker?: {
    Action: { CANCEL?: string, PICKED: string }
    DocsView: new (viewId: string) => DocsViewLike
    DocsViewMode: { LIST: string }
    Document: { ID: string, MIME_TYPE: string, NAME: string, URL: string }
    Feature: { MULTISELECT_ENABLED: string }
    PickerBuilder: new () => PickerBuilderLike
    Response: { ACTION: string, DOCUMENTS: string }
    ViewId: { DOCS: string, FOLDERS: string }
  }
}

type GapiLike = {
  load: (name: string, callback: () => void) => void
}

export type PickerResponseFields = {
  actionKey: string
  cancelAction?: string
  documentsKey: string
  idKey: string
  mimeTypeKey: string
  nameKey: string
  pickedAction: string
  urlKey: string
}

export type PickerResponseResult =
  | { state: 'cancelled' | 'invalid' | 'pending' }
  | { items: GoogleDrivePickedItem[], state: 'picked' }

declare global {
  interface Window {
    gapi?: GapiLike
    google?: GoogleLike
  }
}

export async function pickGoogleDriveItems(config: GoogleDrivePickerConfig, mode: GoogleDrivePickerMode): Promise<{ accessToken: string, items: GoogleDrivePickedItem[] }> {
  if (!config.configured || !config.clientId || !config.apiKey || !config.appId) {
    throw new Error(`Google Drive Picker is missing: ${config.missing.join(', ')}`)
  }

  await loadScript('https://apis.google.com/js/api.js')
  await loadScript('https://accounts.google.com/gsi/client')
  await loadPickerLibrary()
  const accessToken = await requestAccessToken(config.clientId, mode === 'folders' ? config.scopes.folders : config.scopes.files)
  const items = await showPicker(config, mode, accessToken)

  return { accessToken, items }
}

function loadScript(src: string): Promise<void> {
  if (document.querySelector(`script[src="${src}"]`)) {
    return Promise.resolve()
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`Failed to load ${src}`))
    script.src = src
    document.head.appendChild(script)
  })
}

function loadPickerLibrary(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (!window.gapi) {
      reject(new Error('Google API loader is unavailable.'))
      return
    }
    window.gapi.load('picker', resolve)
  })
}

function requestAccessToken(clientId: string, scope: string): Promise<string> {
  const oauth2 = window.google?.accounts?.oauth2
  if (!oauth2) {
    return Promise.reject(new Error('Google Identity Services is unavailable.'))
  }

  return new Promise((resolve, reject) => {
    const tokenClient = oauth2.initTokenClient({
      callback: (response) => {
        if (response.error || !response.access_token) {
          reject(new Error(response.error ?? 'Google authorization did not return an access token.'))
          return
        }
        resolve(response.access_token)
      },
      client_id: clientId,
      scope,
    })
    tokenClient.requestAccessToken({ prompt: 'consent' })
  })
}

function showPicker(config: GoogleDrivePickerConfig, mode: GoogleDrivePickerMode, accessToken: string): Promise<GoogleDrivePickedItem[]> {
  const picker = window.google?.picker
  if (!picker || typeof config.apiKey !== 'string' || typeof config.appId !== 'string') {
    return Promise.reject(new Error('Google Picker is unavailable.'))
  }
  const apiKey = config.apiKey
  const appId = config.appId

  return new Promise((resolve, reject) => {
    const docsView = new picker.DocsView(mode === 'folders' ? picker.ViewId.FOLDERS : picker.ViewId.DOCS)
      .setIncludeFolders(mode !== 'files')
      .setMode(picker.DocsViewMode.LIST)
      .setSelectFolderEnabled(mode === 'folders')

    let finished = false
    const builder = new picker.PickerBuilder()
      .addView(docsView)
      .setOAuthToken(accessToken)
      .setDeveloperKey(apiKey)
      .setAppId(appId)
      .setCallback((data) => {
        if (finished) {
          return
        }

        const result = parseGoogleDrivePickerResponse(data, {
          actionKey: picker.Response.ACTION,
          cancelAction: picker.Action.CANCEL,
          documentsKey: picker.Response.DOCUMENTS,
          idKey: picker.Document.ID,
          mimeTypeKey: picker.Document.MIME_TYPE,
          nameKey: picker.Document.NAME,
          pickedAction: picker.Action.PICKED,
          urlKey: picker.Document.URL,
        })

        if (result.state === 'pending') {
          return
        }

        if (result.state === 'cancelled') {
          finished = true
          resolve([])
          return
        }

        finished = true
        if (result.state === 'invalid') {
          reject(new Error('Google Picker returned no selected documents.'))
          return
        }
        if (result.state === 'picked') {
          resolve(result.items)
        }
      })

    if (mode === 'files') {
      builder.enableFeature(picker.Feature.MULTISELECT_ENABLED)
    }

    builder.build().setVisible(true)
  })
}

export function parseGoogleDrivePickerResponse(data: Record<string, unknown>, fields: PickerResponseFields): PickerResponseResult {
  const action = data[fields.actionKey] ?? data.action
  if (action === fields.cancelAction || action === 'cancel') {
    return { state: 'cancelled' }
  }
  if (action !== fields.pickedAction && action !== 'picked') {
    return { state: 'pending' }
  }

  const documents = data[fields.documentsKey] ?? data.docs
  if (!Array.isArray(documents)) {
    return { state: 'invalid' }
  }

  return {
    items: documents.map((item) => pickedItem(item, fields)),
    state: 'picked',
  }
}

function pickedItem(item: unknown, fields: PickerResponseFields): GoogleDrivePickedItem {
  const document = item as Record<string, unknown>
  const url = document[fields.urlKey]
  return {
    id: String(document[fields.idKey] ?? ''),
    mimeType: String(document[fields.mimeTypeKey] ?? ''),
    name: String(document[fields.nameKey] ?? 'Google Drive item'),
    ...(typeof url === 'string' ? { url } : {}),
  }
}
