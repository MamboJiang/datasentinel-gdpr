import { describe, expect, it } from 'vitest'
import { parseGoogleDrivePickerResponse, type PickerResponseFields } from './googleDrivePicker'

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
})
