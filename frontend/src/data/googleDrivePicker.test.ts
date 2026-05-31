import { afterEach, describe, expect, it, vi } from 'vitest'
import { parseGoogleDrivePickerResponse, pickGoogleDriveItems, type PickerResponseFields } from './googleDrivePicker'

const fields: PickerResponseFields = {
  actionKey: 'action',
  cancelAction: 'cancel',
  documentsKey: 'docs',
  idKey: 'id',
  mimeTypeKey: 'mimeType',
  nameKey: 'name',
  pickedAction: 'picked',
  urlKey: 'url',
}

describe('Google Drive Picker response parsing', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('ignores non-terminal picker callbacks', () => {
    expect(parseGoogleDrivePickerResponse({ action: 'loaded' }, fields)).toEqual({ state: 'pending' })
  })

  it('returns picked file metadata from the standard docs callback field', () => {
    const result = parseGoogleDrivePickerResponse({
      action: 'picked',
      docs: [{
        id: 'drive-file-id',
        mimeType: 'text/plain',
        name: 'contacts.txt',
        url: 'https://drive.google.com/file/d/drive-file-id/view',
      }],
    }, fields)

    expect(result).toEqual({
      items: [{
        id: 'drive-file-id',
        mimeType: 'text/plain',
        name: 'contacts.txt',
        url: 'https://drive.google.com/file/d/drive-file-id/view',
      }],
      state: 'picked',
    })
  })

  it('treats cancel as a terminal empty selection', () => {
    expect(parseGoogleDrivePickerResponse({ action: 'cancel' }, fields)).toEqual({ state: 'cancelled' })
  })

  it('uses a supplied account-binding token without loading Google Identity Services', async () => {
    const loadedScripts: string[] = []
    let pickerToken: string | null = null
    let pickerCallback: ((data: Record<string, unknown>) => void) | null = null

    class FakeDocsView {
      setEnableDrives() { return this }
      setIncludeFolders() { return this }
      setMode() { return this }
      setSelectFolderEnabled() { return this }
    }

    class FakePickerBuilder {
      addView() { return this }
      build() {
        return {
          setVisible: () => pickerCallback?.({
            action: 'picked',
            docs: [{
              id: 'drive-file-id',
              mimeType: 'text/plain',
              name: 'contacts.txt',
              url: 'https://drive.google.com/file/d/drive-file-id/view',
            }],
          }),
        }
      }
      enableFeature() { return this }
      setAppId() { return this }
      setCallback(callback: (data: Record<string, unknown>) => void) {
        pickerCallback = callback
        return this
      }
      setDeveloperKey() { return this }
      setOAuthToken(token: string) {
        pickerToken = token
        return this
      }
    }

    vi.stubGlobal('document', {
      createElement: () => ({ async: false, defer: false, onerror: null, onload: null, src: '' }),
      head: {
        appendChild: (script: { onload?: (event: Event) => void, src: string }) => {
          loadedScripts.push(script.src)
          script.onload?.({} as Event)
        },
      },
      querySelector: () => null,
    })
    vi.stubGlobal('window', {
      gapi: { load: (_name: string, callback: () => void) => callback() },
      google: {
        picker: {
          Action: { CANCEL: 'cancel', PICKED: 'picked' },
          DocsView: FakeDocsView,
          DocsViewMode: { LIST: 'list' },
          Document: { ID: 'id', MIME_TYPE: 'mimeType', NAME: 'name', URL: 'url' },
          Feature: { MULTISELECT_ENABLED: 'multiselect' },
          PickerBuilder: FakePickerBuilder,
          Response: { ACTION: 'action', DOCUMENTS: 'docs' },
          ViewId: { DOCS: 'docs', FOLDERS: 'folders' },
        },
      },
    })

    const result = await pickGoogleDriveItems({
      apiKey: 'picker-api-key',
      appId: '1234567890',
      clientId: 'google-client-id',
      configured: true,
      missing: [],
      scopes: { files: 'https://www.googleapis.com/auth/drive.readonly', folders: 'https://www.googleapis.com/auth/drive.readonly' },
    }, 'files', { accessToken: 'bound_picker_access' })

    expect(result.accessToken).toBe('bound_picker_access')
    expect(result.items).toHaveLength(1)
    expect(pickerToken).toBe('bound_picker_access')
    expect(loadedScripts).toEqual(['https://apis.google.com/js/api.js'])
  })
})
