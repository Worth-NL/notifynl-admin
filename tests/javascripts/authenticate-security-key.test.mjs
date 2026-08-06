import { jest } from '@jest/globals';
import ErrorBanner from '../../app/assets/javascripts/esm/error-banner.mjs';


jest.unstable_mockModule('../../app/assets/javascripts/utils/location.mjs', () => ({
  locationAssign: jest.fn()
}));


let AuthenticateSecurityKey;
let locationAssign;

beforeAll( async() => {
  const authenticateSecurityKeyModule = await import('../../app/assets/javascripts/esm/authenticate-security-key.mjs');
  const locationUtilModule = await import('../../app/assets/javascripts/utils/location.mjs');

  AuthenticateSecurityKey = authenticateSecurityKeyModule.default;
  locationAssign = locationUtilModule.locationAssign;
})

describe('Authenticate with security key', () => {
  let button;
  let mockClickEvent;
  let mockFetch;
  let mockOptionsJSON;
  let mockLoginResponse;
  let authenticateKeyInstance;
  let errorBannerShowBannerSpy;
  let parseRequestOptionsFromJSON;
  let credentialsGetResponse;

  const mockBrowserCredentials = {
    get: jest.fn(),
  };

  afterAll(() => {
    jest.restoreAllMocks();
  });

  beforeEach(() => {
    // disable console.error() so we don't see it in test output
    // you might need to comment this out to debug some failures
    console.error = jest.fn();

    // clear the window.location mock
    locationAssign.mockClear();

    document.body.classList.add('govuk-frontend-supported');
    document.body.innerHTML = `
      <button data-notify-module="authenticate-security-key" data-module="govuk-button" data-csrf-token="abc123"></button>`;

    button = document.querySelector('[data-notify-module="authenticate-security-key"]');

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
    parseRequestOptionsFromJSON = jest.fn().mockReturnValue('parsedRequestOptions');
    window.PublicKeyCredential = { parseRequestOptionsFromJSON };

    mockOptionsJSON = { publicKey: 'someArbitraryOptions' };
    mockLoginResponse = { redirect_url: '/foo' };

    credentialsGetResponse = {
      toJSON: () => ({
        id: 'credential-id',
        rawId: 'credential-id',
        type: 'public-key',
        response: {
          authenticatorData: 'authenticator-data',
          signature: 'signature',
          clientDataJSON: 'client-data-json',
        }
      }),
    };

    // instantiate class
    authenticateKeyInstance = new AuthenticateSecurityKey(button);

  });

  afterEach(() => {
    jest.restoreAllMocks();
    mockFetch.mockClear();
    delete window.fetch;
    delete window.navigator.credentials;
    delete window.PublicKeyCredential;
  });

  it('authenticates a credential and redirects based on the admin app response', async () => {

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve(mockOptionsJSON)),
    });

    // mock getCredential response
    mockBrowserCredentials.get.mockResolvedValueOnce(credentialsGetResponse);

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve(mockLoginResponse)),
    });

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(parseRequestOptionsFromJSON).toHaveBeenCalledWith('someArbitraryOptions');
    expect(mockBrowserCredentials.get).toHaveBeenCalledWith({ publicKey: 'parsedRequestOptions' });

    const mockFetchOptions = mockFetch.mock.calls[1][1]
    expect(mockFetchOptions.headers).toEqual({ 'X-CSRFToken': 'abc123', 'Content-Type': 'application/json' });
    expect(mockFetchOptions.method).toBe('POST');

    const decodedData = JSON.parse(mockFetchOptions.body);
    expect(decodedData).toEqual(credentialsGetResponse.toJSON());

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(locationAssign).toHaveBeenCalledWith('/foo');
    expect(ErrorBanner.prototype.showBanner).not.toHaveBeenCalled();
  });

  it('authenticates and passes a redirect url through to the authenticate admin endpoint', async() => {

    history.pushState({}, '', '/webauth/authenticate?next=%2Ffoo%3Fbar%3Dbaz');

    // mock fetch auth
     mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve(mockOptionsJSON)),
    });

    // mock getCredential response
    mockBrowserCredentials.get.mockResolvedValueOnce(credentialsGetResponse);

    // mock fetch auth
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve(mockLoginResponse)),
    });

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockBrowserCredentials.get).toHaveBeenCalledWith({ publicKey: 'parsedRequestOptions' });
    expect(locationAssign).toHaveBeenCalledWith('/foo');
    expect(ErrorBanner.prototype.showBanner).not.toHaveBeenCalled();
    expect(mockFetch.mock.calls[1][0].toString()).toEqual(
      'https://www.notifications.service.gov.uk/webauthn/authenticate?next=%2Ffoo%3Fbar%3Dbaz'
    );
  });

  test.each([
    ['network'],
    ['server'],
  ])('errors if fetching WebAuthn fails (%s error)', async(errorType) => {

    if (errorType == 'network') {
      mockFetch.mockRejectedValueOnce(new Error('error'));
    } else {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'error'
      });
    }

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(locationAssign).not.toHaveBeenCalled();
    expect(ErrorBanner.prototype.showBanner).toHaveBeenCalled();
  });

  it('errors if comms with the authenticator fails', async() => {

    // mock fetch auth
     mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve(mockOptionsJSON)),
    });

    // mock getCredential response
    mockBrowserCredentials.get.mockResolvedValueOnce(new DOMException('error'));

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(ErrorBanner.prototype.showBanner).toHaveBeenCalled();
  });

  test.each([
    ['network'],
    ['server'],
  ])('errors if POSTing WebAuthn credentials fails (%s)', async(errorType) => {

    // mock fetch auth
     mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve(mockOptionsJSON)),
    });

    // mock getCredential response
    if (errorType == 'network') {
      mockBrowserCredentials.get.mockRejectedValueOnce('error');
    } else {
      mockBrowserCredentials.get.mockResolvedValueOnce({ ok: false, statusText: 'FORBIDDEN' });
    }

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockBrowserCredentials.get).toHaveBeenCalledWith({ publicKey: 'parsedRequestOptions' });
    expect(locationAssign).not.toHaveBeenCalled();
    expect(ErrorBanner.prototype.showBanner).toHaveBeenCalled();
  });

  it('reloads page if POSTing WebAuthn credentials returns 403', async() => {

    // mock fetch auth
     mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn(() => Promise.resolve(mockOptionsJSON)),
    });

    // mock getCredential
    mockBrowserCredentials.get.mockResolvedValueOnce(credentialsGetResponse);

    // mock postCredential fail
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403
    });

    await authenticateKeyInstance.authenticateKey(mockClickEvent);

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(mockBrowserCredentials.get).toHaveBeenCalledWith({ publicKey: 'parsedRequestOptions' });
    expect(locationAssign).not.toHaveBeenCalledWith();
    expect(ErrorBanner.prototype.showBanner).toHaveBeenCalled();
  });
});
