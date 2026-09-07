import { jest } from '@jest/globals';
import ErrorBanner from '../../app/assets/javascripts/esm/error-banner.mjs';

jest.unstable_mockModule('../../app/assets/javascripts/utils/location.mjs', () => ({
  locationReload: jest.fn()
}));

let RegisterSecurityKey;
let locationReload;

beforeAll( async() => {
  const registerSecurityKeyModule = await import('../../app/assets/javascripts/esm/register-security-key.mjs');
  const locationUtilModule = await import('../../app/assets/javascripts/utils/location.mjs');

  RegisterSecurityKey = registerSecurityKeyModule.default;
  locationReload = locationUtilModule.locationReload;
})

describe('Register security key', () => {
  let button;
  let mockClickEvent;
  let mockFetch;
  let mockOptionsJSON;
  let mockCredentialJSON;
  let registerKeyInstance;
  let errorBannerShowBannerSpy;
  let parseCreationOptionsFromJSON;

  const mockBrowserCredentials = {
    create: jest.fn(),
  };

  afterAll(() => {
    jest.restoreAllMocks();
  });

  beforeEach(() => {
    // disable console.error() so we don't see it in test output
    // you might need to comment this out to debug some failures
    console.error = jest.fn();

    // clear the window.location mock
    locationReload.mockClear();

    document.body.classList.add('govuk-frontend-supported');
    document.body.innerHTML = `
      <button href="#" class="govuk-button govuk-button--secondary" data-notify-module="register-security-key" data-module="govuk-button">
        Register a key
      </button>`;

    button = document.querySelector('[data-notify-module="register-security-key"]');
    // create a mock event for the click handler
    mockClickEvent = { preventDefault: jest.fn() };

    // spy on the showBanner method of ErroBanner class
    // and mock its implementation, allowing us to assert whether it was called
    errorBannerShowBannerSpy = jest.spyOn(ErrorBanner.prototype, 'showBanner').mockImplementation(() => {});

    // mock the window fetch function
    mockFetch = jest.fn();
    window.fetch = mockFetch;

    // mock WebAuthn browser APIs
    window.navigator.credentials = mockBrowserCredentials;
    parseCreationOptionsFromJSON = jest.fn().mockReturnValue('parsedCreationOptions');
    window.PublicKeyCredential = { parseCreationOptionsFromJSON };

    mockOptionsJSON = { publicKey: 'someOptionsJSON' };
    mockCredentialJSON = {
      id: 'credential-id',
      rawId: 'credential-id',
      type: 'public-key',
      response: {
        attestationObject: 'attestation-object',
        clientDataJSON: 'client-data-json',
      }
    };

    // instantiate class
    registerKeyInstance = new RegisterSecurityKey(button);
  })

  afterEach(() => {
    jest.restoreAllMocks();
    jest.resetModules();
    mockFetch.mockClear();
    delete window.fetch;
    delete window.navigator.credentials;
    delete window.PublicKeyCredential;
  });

  it('creates a new credential and reloads', async() => {

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve(mockOptionsJSON)),
    });

    // mock createCredential
    mockBrowserCredentials.create.mockResolvedValueOnce({
      toJSON: () => mockCredentialJSON,
    });

    // mock postCredential
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve('')),
    });

    await registerKeyInstance.registerKey(mockClickEvent);

    expect(parseCreationOptionsFromJSON).toHaveBeenCalledWith('someOptionsJSON');
    expect(mockBrowserCredentials.create).toHaveBeenCalledWith({ publicKey: 'parsedCreationOptions' });

    const mockFetchOptions = mockFetch.mock.calls[1][1];
    expect(mockFetchOptions.headers['X-CSRFToken']).toBe();
    expect(mockFetchOptions.headers['Content-Type']).toBe('application/json');
    expect(mockFetchOptions.method).toBe('POST');

    const decodedData = JSON.parse(mockFetchOptions.body);
    expect(decodedData).toEqual(mockCredentialJSON);

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(locationReload).toHaveBeenCalled();
    expect(ErrorBanner.prototype.showBanner).not.toHaveBeenCalled();
  });

  test.each([
    ['network'],
    ['server'],
  ])('errors if fetching WebAuthn options fails (%s error)', async(errorType) => {

    if (errorType == 'network') {
      mockFetch.mockRejectedValueOnce(new Error('error'));
    } else {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'error'
      });
    }

    await registerKeyInstance.registerKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(locationReload).not.toHaveBeenCalled();
    expect(ErrorBanner.prototype.showBanner).toHaveBeenCalled();
  });

  test.each([
    ['network'],
    ['server'],
  ])('errors if sending WebAuthn credentials fails (%s)', async(errorType) => {

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve(mockOptionsJSON)),
    });

    // mock createCredential
    mockBrowserCredentials.create.mockResolvedValueOnce({
      toJSON: () => mockCredentialJSON,
    });

    // mock postCredential
    if (errorType == 'network') {
      mockFetch.mockRejectedValueOnce(new Error('error'));
    } else {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'FORBIDDEN'
      });
    }

    await registerKeyInstance.registerKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(locationReload).not.toHaveBeenCalled();
    expect(ErrorBanner.prototype.showBanner).toHaveBeenCalled();
  });

  it('errors if comms with the authenticator fails', async() => {

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve(mockOptionsJSON)),
    });

    // mock createCredential
    mockBrowserCredentials.create.mockResolvedValueOnce(new DOMException('error'));

    await registerKeyInstance.registerKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(locationReload).not.toHaveBeenCalled();
    expect(ErrorBanner.prototype.showBanner).toHaveBeenCalled();
  })
});
