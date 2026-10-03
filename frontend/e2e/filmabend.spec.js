import { expect, test } from '@playwright/test'
import { KINO } from '../playwright.config.js'

// One story, in order: a new group plans a movie night from scratch.
test.describe.configure({ mode: 'serial' })

/** @type {import('@playwright/test').Page} */
let page

test.beforeAll(async ({ browser }) => {
  page = await browser.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  page.errors = errors
  await page.goto('/#/abend')
})

test.afterAll(() => {
  expect(page.errors, 'no console or page errors during the whole story').toEqual([])
})

const nav = (name) => page.getByRole('link', { name, exact: true }).click()

test('first visit asks for a name', async () => {
  await expect(page.getByRole('dialog', { name: 'Namen wählen' })).toBeVisible()
  await page.getByPlaceholder('Neuer Name').fill('Marc')
  await page.getByRole('button', { name: 'Anlegen' }).click()
  await expect(page.getByRole('dialog')).toBeHidden()
  await expect(page.locator('.me')).toContainText('Marc')
})

test('joining the next evening', async () => {
  await page.getByRole('button', { name: 'Ich bin dabei!' }).click()
  await expect(page.locator('.crew')).toContainText('Marc')
})

test('navigation has three main areas (plus the Kino when a media server runs)', async () => {
  const main = page.getByRole('navigation', { name: 'Hauptbereiche' }).getByRole('link')
  await expect(main).toHaveText(KINO ? ['Filmabend', 'Finden', 'Unsere Filme', /^Kino/] : ['Filmabend', 'Finden', 'Unsere Filme'])
})

test('discover filters by extra genre', async () => {
  await nav('Finden')
  await expect(page.locator('.card')).toHaveCount(12)
  await page.getByRole('button', { name: 'Science Fiction' }).click()
  await expect(page.locator('.card')).toHaveCount(2)
  await page.getByRole('button', { name: 'Science Fiction' }).click()
  await expect(page.locator('.card')).toHaveCount(12)
})

test('cards bookmark and suggest', async () => {
  for (const title of ['Alien', 'Shining']) {
    const card = page.locator('.card', { hasText: title }).first()
    await card.hover()
    await card.getByRole('button', { name: 'Vorschlagen' }).click()
    await expect(card.getByRole('button', { name: 'Vorschlagen' })).toHaveAttribute('aria-pressed', 'true')
  }
  const alien = page.locator('.card', { hasText: 'Alien' })
  await alien.hover()
  await alien.getByRole('button', { name: 'Merken' }).click()
  await expect(alien.getByRole('button', { name: 'Merken' })).toHaveAttribute('aria-pressed', 'true')
})

test('detail sheet is a real dialog', async () => {
  await page.getByRole('button', { name: 'Hereditary – Das Vermächtnis – Details' }).click()
  const dialog = page.getByRole('dialog', { name: /Hereditary/ })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('Ähnliche Filme')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
})

test('one search field: typing searches titles, clearing returns to discover', async () => {
  const field = page.getByRole('searchbox', { name: 'Suchen' })
  await field.fill('the thing')
  await expect(page.locator('.card')).toHaveCount(1)
  await expect(page.locator('.card')).toContainText('Das Ding')
  await field.fill('')
  await expect(page.locator('.card')).toHaveCount(12)
})

test('old links still work', async () => {
  await page.goto('/#/merkliste')
  await expect(page).toHaveURL(/#\/sammlung\/merkliste$/)
  await expect(page.locator('.card', { hasText: 'Alien' })).toBeVisible()
  await page.goto('/#/abend')
})

test('the wheel picks a suggested film', async () => {
  await nav('Filmabend')
  await expect(page.locator('.sugg')).toHaveCount(2)
  await page.getByRole('button', { name: 'Drehen' }).click()
  const winner = page.locator('.winner strong')
  await expect(winner).toHaveText(/Alien|Shining/, { timeout: 8000 })
  page.winner = await winner.textContent()
  await page.locator('.winner').getByRole('button', { name: 'Geschaut' }).click()
  await expect(page.locator('.sugg')).toHaveCount(1)
})

test('rating: the n-th star gives n stars', async () => {
  await nav('Unsere Filme')
  await page.getByRole('navigation', { name: 'Liste' }).getByRole('link', { name: /Gesehen/ }).click()
  await expect(page.locator('.entry h3')).toContainText(page.winner)
  await page.getByRole('radio', { name: '3 von 5 Sternen' }).click()
  await expect(page.locator('.avg .num')).toHaveText('3.0')
})

test('guestbook threads replies', async () => {
  await page.getByLabel('Kommentar').fill('Was für ein Abend!')
  await page.locator('form.add').getByRole('button', { name: 'Senden' }).click()
  await page.getByRole('button', { name: 'Antworten' }).click()
  await page.getByLabel('Antwort').fill('Absolut')
  await page.locator('.reply').getByRole('button', { name: 'Senden' }).click()
  await expect(page.locator('.note.nested')).toContainText('Absolut')
})

test('wishes can be voted on', async () => {
  await nav('Wünsche & Ideen')
  await page.getByLabel('Neuer Wunsch').fill('Serien unterstützen')
  await page.getByRole('button', { name: 'Wünschen' }).click()
  await page.getByRole('button', { name: /Abstimmen, 0 Stimmen/ }).click()
  await expect(page.getByRole('button', { name: /Abstimmen, 1 Stimmen/ })).toBeVisible()
})

test('host mode via the secret shortcut and a film', async () => {
  await page.keyboard.press('Control+Shift+H')
  await expect(page.getByRole('heading', { name: 'Host-Modus' })).toBeVisible()
  await page.getByPlaceholder('Host-Film suchen').fill('alien')
  await page.locator('.picker .results button', { hasText: 'Alien' }).first().click()
  await expect(page.locator('.host-badge')).toBeVisible()
})

test('own name gets film protection', async () => {
  await page.getByRole('button', { name: 'Schutz einrichten' }).click()
  await page.getByPlaceholder('Deinen Passwort-Film').fill('midsommar')
  await page.locator('.picker .results button', { hasText: 'Midsommar' }).click()
  await expect(page.locator('.chip.ok', { hasText: 'geschützt' })).toBeVisible()
})

test('info card on the evening page renders sanitised markdown', async () => {
  await nav('Filmabend')
  await page.getByRole('button', { name: 'Infos hinzufügen' }).click()
  await page.getByLabel('Infos (Markdown)').fill('# Regeln\n\n**Keine Handys.**\n\n<img src=x onerror="window.pwned=1">')
  await page.getByRole('button', { name: 'Speichern' }).click()
  await expect(page.locator('.prose h1')).toHaveText('Regeln')
  expect(await page.evaluate(() => window.pwned)).toBeUndefined()
})

test('a second device must know the film to use the name', async ({ browser }) => {
  const phone = await browser.newPage({ viewport: { width: 390, height: 844 } })
  await phone.goto('/#/abend')
  await phone.getByRole('button', { name: 'Marc' }).click()
  await expect(phone.getByRole('heading', { name: 'Film-Passwort für Marc' })).toBeVisible()
  await phone.getByLabel('Film suchen').fill('alien')
  await phone.locator('.results button', { hasText: 'Alien' }).click()
  await expect(phone.getByRole('alert')).toContainText('nicht der richtige Film')
  await phone.getByLabel('Film suchen').fill('midsommar')
  await phone.locator('.results button', { hasText: 'Midsommar' }).click()
  await expect(phone.getByRole('dialog')).toBeHidden()
  await expect(phone.locator('.me')).toContainText('Marc')
  await phone.close()
})
