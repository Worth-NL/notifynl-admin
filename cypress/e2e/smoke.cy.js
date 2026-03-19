
describe('Smoke test', () => {
  it('site is up and returns a page', () => {
    cy.visit('/')
    cy.title().should('not.be.empty')
  })

  it('homepage returns 200', () => {
    cy.request('/').its('status').should('eq', 200)
  })
})
