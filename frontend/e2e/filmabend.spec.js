import { readFileSync } from 'node:fs'
import { expect, test } from '@playwright/test'
import { ADMIN_SITZUNG, KINO, SETUP } from '../playwright.config.js'

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

test.afterAll(async () => {
  // kino.spec.js continues the story: it needs the admin's session to invite its viewers.
  await page.context().storageState({ path: ADMIN_SITZUNG })
  expect(page.errors, 'no console or page errors during the whole story').toEqual([])
})

const nav = (name) => page.getByRole('link', { name, exact: true }).click()
// The genres sit in a small menu in the bar above the grid.
async function genre(name) {
  await page.getByRole('button', { name: 'Genres', exact: true }).click()
  await page.getByRole('group', { name: 'Genres' }).getByRole('button', { name }).click()
  await page.keyboard.press('Escape')
}
// The group's activity lives on the "Neuigkeiten" page (behind the bell), not on the evening page.
async function inDerGruppe(text) {
  await page.getByRole('link', { name: /^Neuigkeiten/ }).click()
  await expect(page.getByRole('heading', { name: 'In der Gruppe' })).toBeVisible()
  await expect(page.locator('.feed')).toContainText(text)
  await nav('Filmabend')
}
// The planning folds away once nothing waits for you: open it where a step needs it.
async function planung() {
  const knopf = page.getByRole('button', { name: 'Planung' })
  if ((await knopf.getAttribute('aria-expanded')) !== 'true') await knopf.click()
  await expect(page.locator('#planung')).toBeVisible()
}
// The same person on a second device (its own browser, same session).
const zweitesGeraet = async () => {
  const ctx = await page.context().browser().newContext({ storageState: await page.context().storageState() })
  return ctx.newPage()
}

test('first visit asks for a name, and the first name needs the setup code', async ({ browser }) => {
  // Whoever finds the fresh server first doesn't become its admin.
  const fremd = await browser.newPage()
  await fremd.goto('/#/abend')
  const tuer = fremd.getByRole('dialog', { name: 'Namen wählen' })
  // The very first request of a freshly started stack can take a while (seeding, cold caches).
  await expect(tuer).toBeVisible({ timeout: 20_000 })
  await expect(tuer).toContainText('Noch niemand da')
  await fremd.getByPlaceholder('Neuer Name').fill('Mallory')
  await fremd.getByRole('button', { name: 'Anlegen' }).click()
  await expect(tuer.getByRole('alert')).toContainText('Einrichtungscode')
  await fremd.close()
  // The operator opens the link from the server log: the code is filled in.
  await page.goto(`/#/setup/${SETUP}`)
  const dialog = page.getByRole('dialog', { name: 'Namen wählen' })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByLabel('Einrichtungscode')).toHaveCount(0)
  await page.getByPlaceholder('Neuer Name').fill('Marc')
  await page.getByRole('button', { name: 'Anlegen' }).click()
  await expect(page.getByRole('dialog', { name: 'Namen wählen' })).toBeHidden()
  await expect(page.locator('.me')).toContainText('Marc')
  // The first name of a fresh install administrates the group.
  await expect(page.locator('.admin-badge')).toBeVisible()
})

test('someone new picks language and colours, then gets three cards – once', async () => {
  const willkommen = page.getByRole('dialog', { name: 'Willkommen bei screenmates' })
  await expect(willkommen).toContainText('Willkommen, Marc!')
  // Language: switches at once and is kept with the profile.
  await willkommen.getByRole('radio', { name: 'English' }).click()
  const welcome = page.getByRole('dialog', { name: 'Welcome to screenmates' })
  await expect(welcome).toContainText('Welcome, Marc!')
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await expect(page.getByRole('link', { name: 'Movie night' }).first()).toBeVisible()
  await welcome.getByRole('radio', { name: 'Deutsch' }).click()
  await expect(willkommen).toContainText('Willkommen, Marc!')
  // Colours: applied right away.
  await willkommen.getByRole('radio', { name: 'Nacht' }).click()
  await expect.poll(() => page.evaluate(() => document.documentElement.style.getPropertyValue('--accent'))).toBe('#3b82f6')
  await willkommen.getByRole('radio', { name: 'Kino' }).click()
  await willkommen.getByRole('button', { name: 'Weiter' }).click()
  await expect(willkommen).toContainText('Vorschlagen')
  await willkommen.getByRole('button', { name: 'Weiter' }).click()
  await expect(willkommen).toContainText('Die Kiste entscheidet')
  await willkommen.getByRole('button', { name: 'Weiter' }).click()
  await willkommen.getByRole('button', { name: 'Los geht’s' }).click()
  await expect(willkommen).toBeHidden()
  await page.reload()
  await expect(page.locator('.me')).toContainText('Marc')
  await expect(willkommen).toHaveCount(0) // once, not on every visit
})

test('newcomers get a first-steps checklist and short explanations', async () => {
  await page.goto('/#/abend')
  const schritte = page.getByRole('region', { name: 'Erste Schritte' })
  await expect(schritte).toBeVisible()
  await expect(schritte.getByRole('link', { name: 'Filme finden' })).toHaveAttribute('href', '#/finden')
  // Notifications can be declined – the step counts as done.
  await schritte.getByRole('button', { name: 'Nein danke' }).click()
  await expect(schritte).toContainText('Übersprungen')
  await expect(schritte.getByRole('button', { name: 'Nein danke' })).toHaveCount(0)
  // A tap on ⓘ explains our own words.
  await page.getByRole('button', { name: 'Was ist „Filmabend-Kiste“?' }).click()
  await expect(page.getByRole('tooltip')).toContainText('zieht zufällig einen Film')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('tooltip')).toHaveCount(0)
  // Put away: gone, also after a reload.
  await schritte.getByRole('button', { name: 'Ausblenden' }).click()
  await expect(schritte).toHaveCount(0)
  await page.reload()
  await expect(page.locator('.me')).toContainText('Marc')
  await expect(schritte).toHaveCount(0)
})

test('joining the next evening', async () => {
  await page.getByRole('button', { name: 'Ich bin dabei!' }).click()
  await expect(page.locator('.crew')).toContainText('Marc')
})

test('navigation has three main areas (plus the Kino when a media server runs)', async () => {
  const main = page.getByRole('navigation', { name: 'Hauptbereiche' }).getByRole('link')
  await expect(main).toHaveText(KINO ? ['Filmabend', 'Finden', 'Unsere Filme', /^Kino/] : ['Filmabend', 'Finden', 'Unsere Filme'])
})

test('finding starts with shelves to browse; "Alle zeigen" opens the grid with that filter', async () => {
  await nav('Finden')
  await expect(page.getByRole('tab', { name: 'Stöbern' })).toHaveAttribute('aria-selected', 'true')
  // Without TMDB the shelves come from the local catalogue.
  await expect(page.getByRole('region', { name: 'Beliebt' }).locator('.card')).not.toHaveCount(0)
  const klassiker = page.getByRole('region', { name: 'Klassiker' })
  await expect(klassiker.locator('.card')).not.toHaveCount(0)
  await klassiker.getByRole('button', { name: 'Alle zeigen' }).click()
  await expect(page.getByRole('tab', { name: 'Alle Filme' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByLabel('Sortierung')).toHaveValue('vote_average.desc')
  const jahre = () =>
    page.locator('.card').evaluateAll((els) => els.map((e) => Number(e.textContent.match(/(?:19|20)\d\d/g)?.at(-1))))
  await expect.poll(async () => (await jahre()).length).toBeGreaterThan(0)
  expect(Math.max(...(await jahre()))).toBeLessThanOrEqual(1989)
  await page.getByRole('button', { name: 'Filter zurücksetzen' }).click()
  await page.getByLabel('Sortierung').selectOption('popularity.desc')
})

test('discover filters by extra genre', async () => {
  await nav('Finden')
  await expect(page.getByRole('tab', { name: 'Alle Filme' })).toHaveAttribute('aria-selected', 'true') // remembered
  await expect(page.locator('.card')).toHaveCount(12)
  await genre('Science Fiction')
  await expect(page.locator('.card')).toHaveCount(2)
  await genre('Science Fiction')
  await expect(page.locator('.card')).toHaveCount(12)
})

test('the grid keeps loading TMDB-sized pages (20 films) while scrolling', async () => {
  // Three pages of 20 like TMDB sends them; the grid asks for 24 per page.
  const seiten = (url) => {
    const seite = Number(new URL(url).searchParams.get('seite'))
    const results = Array.from({ length: 20 }, (_, i) => ({ id: 900000 + seite * 100 + i, title: `Testfilm ${seite}-${i}`, year: 2000, genres: [], vote_average: 6 }))
    return { results, mehr: seite < 3, gesamt: 60 }
  }
  await page.route('**/api/discover?**', (r) => r.fulfill({ json: seiten(r.request().url()) }))
  await genre('Science Fiction') // any change reloads the grid
  await expect(page.locator('.gesamt')).toHaveText('60 Filme')
  // The first page (20) – and as many more as the screen has room for right away.
  await expect.poll(() => page.locator('.grid .card').count()).toBeGreaterThanOrEqual(20)
  for (let i = 0; i < 12 && (await page.locator('.grid .card').count()) < 60; i++) {
    await page.mouse.wheel(0, 4000)
    await page.waitForTimeout(250)
  }
  await expect(page.locator('.grid .card')).toHaveCount(60)
  await expect(page.getByRole('button', { name: 'Mehr laden' })).toHaveCount(0)
  // Far down the list a button leads back to the top.
  await page.getByRole('button', { name: 'Nach oben' }).click()
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeLessThan(50)
  await expect(page.getByRole('button', { name: 'Nach oben' })).toHaveCount(0)
  await page.unroute('**/api/discover?**')
  await genre('Science Fiction')
  await expect(page.locator('.card')).toHaveCount(12)
  await page.evaluate(() => window.scrollTo(0, 0))
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

test('a veto keeps a film out of the case', async () => {
  await nav('Filmabend')
  await expect(page.locator('.sugg')).toHaveCount(2)
  const alien = page.locator('.sugg', { hasText: 'Alien' })
  await alien.getByRole('button', { name: 'Veto', exact: true }).click()
  await expect(alien).toHaveClass(/vetoed/)
  await expect(alien.locator('.veto-info')).toContainText('Veto von Marc')
  // Out of the case: only Shining is left in it.
  await expect(alien.locator('.chance-text')).toBeHidden()
  await expect(page.locator('.sugg', { hasText: 'Shining' }).locator('.chance-text')).toHaveText('100 %')
  await alien.getByRole('button', { name: 'Veto zurück' }).click()
  await expect(alien).not.toHaveClass(/vetoed/)
})

test('each suggestion shows its odds in the case; the case itself stays slim', async () => {
  for (const film of ['Alien', 'Shining']) {
    await expect(page.locator('.sugg', { hasText: film }).locator('.chance-text')).toHaveText('50 %')
  }
  await expect(page.getByRole('list', { name: /^Kiste mit/ })).toHaveCount(0)
  await expect(page.locator('.wheelbox')).toContainText('2 Filme in der Kiste')
})

test('a practice spin: Escape skips the animation, the reveal names the winner, nothing counts', async () => {
  await page.getByRole('button', { name: 'Probedrehen (nur für mich)' }).click()
  const buehne = page.getByRole('dialog', { name: 'Kiste öffnen' })
  await expect(buehne).toContainText('Probe – zählt nicht')
  await expect(buehne.locator('.item')).toHaveCount(64)
  await expect(buehne.locator('.countdown')).toHaveCount(0, { timeout: 3000 })
  await page.keyboard.press('Escape') // skip
  await expect(buehne.locator('.enthuellung')).toContainText(/Standard · 50 %(Alien|Shining)/)
  const gezogen = (await buehne.locator('.enthuellung strong').textContent()).trim()
  // The marker stops on the winner's tile.
  const [marke, sieger] = await Promise.all([buehne.locator('.marke').boundingBox(), buehne.locator('.item.sieger').boundingBox()])
  expect(marke.x).toBeGreaterThan(sieger.x)
  expect(marke.x).toBeLessThan(sieger.x + sieger.width)
  await expect(buehne.locator('.item.sieger')).toContainText(gezogen)
  await buehne.getByRole('button', { name: 'Weiter' }).click()
  await expect(buehne).toBeHidden()
  await expect(page.locator('.winner')).toHaveCount(0) // practice: no film of the evening
})

test('the host opens the case for everyone: another tab plays the same opening, wherever it is', async () => {
  const zweit = await zweitesGeraet()
  await zweit.goto('/#/finden')
  await page.getByRole('button', { name: 'Für alle öffnen' }).click()
  const hier = page.getByRole('dialog', { name: 'Kiste öffnen' })
  const dort = zweit.getByRole('dialog', { name: 'Kiste öffnen' })
  await expect(dort).toContainText('Marc öffnet die Kiste für alle', { timeout: 5000 })
  await expect(hier.locator('.countdown')).toBeVisible() // everyone starts together
  const weiterHier = hier.getByRole('button', { name: 'Weiter' })
  const weiterDort = dort.getByRole('button', { name: 'Weiter' })
  await expect(weiterHier).toBeVisible({ timeout: 20_000 })
  await expect(weiterDort).toBeVisible({ timeout: 5000 })
  const gezogen = (await hier.locator('.enthuellung strong').textContent()).trim()
  await expect(dort.locator('.enthuellung strong')).toHaveText(gezogen)
  await expect(hier.locator('.item.sieger .name')).toHaveText(gezogen)
  await expect(dort.locator('.item.sieger .name')).toHaveText(gezogen)
  await weiterDort.click()
  await zweit.context().close()
  await weiterHier.click()
  const winner = page.locator('.winner strong')
  await expect(winner).toHaveText(gezogen)
  await expect(page.locator('.winner')).toContainText('Film des Abends')
  page.winner = gezogen
  await page.locator('.winner').getByRole('button', { name: 'Geschaut' }).click()
  await expect(page.locator('.sugg')).toHaveCount(1)
})

test('a date for the evening and an invitation card for the group chat', async () => {
  // A 1×1 PNG with the CORS header TMDB sends: the card's posters stay offline and deterministic.
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64')
  await page.route(/image\.tmdb\.org.*[?&]karte/, (r) =>
    r.fulfill({ body: png, contentType: 'image/png', headers: { 'access-control-allow-origin': '*' } }),
  )
  // A reload that started before saving must not undo the saved date. The page reloads when someone
  // else changes something; hold that reload's answer back until after saving.
  let unterwegs, zugestellt
  let einmal = true
  const gestartet = new Promise((r) => (unterwegs = r))
  const fertig = new Promise((r) => (zugestellt = r))
  await page.route('**/api/termin', async (route) => {
    if (!einmal || route.request().method() !== 'GET') return route.continue()
    einmal = false
    const alt = await route.fetch() // still without a date
    unterwegs()
    await new Promise((r) => setTimeout(r, 3000))
    await route.fulfill({ response: alt })
    zugestellt()
  })
  const zweit = await zweitesGeraet()
  // Right after its own write ("Geschaut") the page takes changes as its own for 2.5 s: wait that out.
  await page.waitForTimeout(3000)
  await zweit.request.post('/api/users/me/willkommen') // changes nothing, but counts as a change
  await gestartet
  await page.getByRole('button', { name: 'Termin festlegen' }).click()
  const dialog = page.getByRole('dialog', { name: 'Termin für den Filmabend' })
  await dialog.getByPlaceholder('z. B. bei Marc').fill('bei Marc')
  await dialog.getByRole('button', { name: 'Speichern' }).click()
  await expect(dialog).toBeHidden()
  await expect(page.locator('.crew .termin')).toContainText(/Freitag, \d+\. \w+, 20:00 Uhr · bei Marc/)
  await fertig
  await expect(page.locator('.crew .termin')).toContainText(/Freitag, \d+\. \w+, 20:00 Uhr · bei Marc/)
  await page.unroute('**/api/termin')
  await zweit.context().close()
  await inDerGruppe('Marc legt den Termin fest: Freitag')

  await page.getByRole('button', { name: 'Einladen' }).click()
  const einladung = page.getByRole('dialog', { name: 'Zum Filmabend einladen' })
  await expect(einladung.locator('.text')).toContainText(/Filmabend am Freitag, .* um 20:00 Uhr \(bei Marc\)/)
  await expect(einladung.locator('.text')).toContainText('Dabei: Marc')
  await expect(einladung.locator('.text')).toContainText('#/abend')
  const karte = einladung.getByRole('img', { name: 'Einladungskarte' })
  // Drawing the card (fonts, posters, canvas) can take a few seconds on a busy machine.
  await expect(karte).toBeVisible({ timeout: 15_000 })
  expect(await karte.evaluate((img) => [img.naturalWidth, img.naturalHeight])).toEqual([1080, 1350])
  await expect(einladung.getByRole('link', { name: 'Bild speichern' })).toHaveAttribute('download', 'filmabend.png')
  await page.keyboard.press('Escape')
  await page.unroute(/image\.tmdb\.org.*[?&]karte/)
})

test('once nothing waits for you, the planning folds into one line', async () => {
  // Marc is in and the date is set: nothing to do, so it's folded – but the date stays in view.
  await expect(page.getByRole('button', { name: 'Planung' })).toHaveAttribute('aria-expanded', 'false')
  await expect(page.locator('#planung')).toBeHidden()
  await expect(page.locator('.crew .termin')).toContainText('bei Marc')
  await expect(page.locator('.crew .wer')).toContainText('Marc dabei')
  await planung()
  await page.getByRole('button', { name: 'Planung' }).click()
  await expect(page.locator('#planung')).toBeHidden()
})

test('the date goes into the calendar as a file', async () => {
  await planung()
  const [datei] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Kalender' }).click()])
  expect(datei.suggestedFilename()).toBe('filmabend.ics')
  const text = await (await datei.createReadStream()).toArray().then((teile) => Buffer.concat(teile).toString())
  expect(text).toContain('BEGIN:VEVENT')
  expect(text).toContain('LOCATION:bei Marc')
})

test('the group votes on a date; picking one carries the answers over', async () => {
  await planung()
  await page.getByRole('button', { name: 'Abstimmen' }).click()
  const dialog = page.getByRole('dialog', { name: 'Termin für den Filmabend' })
  await expect(dialog.getByRole('radio', { name: 'Abstimmen lassen' })).toHaveAttribute('aria-checked', 'true')
  await dialog.getByRole('button', { name: 'Umfrage starten' }).click()
  await expect(dialog).toBeHidden()
  const optionen = page.locator('.umfrage .option')
  await expect(optionen).toHaveCount(2)
  await expect(optionen.first().getByRole('button', { name: /^Ja/ })).toHaveAttribute('aria-pressed', 'true') // proposed = yes
  const samstag = optionen.filter({ hasText: 'Samstag' })
  await samstag.getByRole('button', { name: /^Vielleicht/ }).click()
  await expect(samstag.getByRole('button', { name: /^Vielleicht/ })).toHaveAttribute('aria-pressed', 'true')
  await inDerGruppe('Marc schlägt einen Termin zur Abstimmung vor: Samstag')
  await optionen.filter({ hasText: 'Freitag' }).getByRole('button', { name: 'Festlegen' }).click()
  await expect(page.locator('.umfrage')).toBeHidden()
  await expect(page.locator('.crew .termin')).toContainText(/Freitag, \d+\. \w+, 20:00 Uhr · bei Marc/)
  await expect(page.getByRole('button', { name: 'Ich bin dabei', exact: true })).toHaveAttribute('aria-pressed', 'true')
})

test('yes, maybe or no for the evening', async () => {
  await planung()
  const rsvp = page.getByRole('group', { name: 'Bist du dabei?' })
  await rsvp.getByRole('button', { name: 'Vielleicht' }).click()
  await expect(page.locator('.crew .andere')).toContainText('Vielleicht:')
  await expect(page.locator('.crew .andere')).toContainText('Marc')
  await expect(rsvp.getByRole('button', { name: 'Ich bin dabei!' })).toBeVisible()
  await rsvp.getByRole('button', { name: 'Kann nicht' }).click()
  await expect(page.locator('.crew .andere')).toContainText('Kann nicht:')
  await rsvp.getByRole('button', { name: 'Ich bin dabei!' }).click()
  await expect(page.locator('.crew .andere')).toBeHidden()
  await expect(page.locator('.crew .who')).toContainText('Marc')
})

test('rating: the n-th star gives n stars', async () => {
  await nav('Unsere Filme')
  await page.getByRole('navigation', { name: 'Liste' }).getByRole('link', { name: /Gesehen/ }).click()
  await expect(page.locator('.entry h3')).toContainText(page.winner)
  await page.getByRole('radio', { name: '3 von 5 Sternen' }).click()
  await expect(page.locator('.avg .num')).toHaveText('3,0')
})

test('guestbook threads replies', async () => {
  await page.getByRole('button', { name: 'Ins Gästebuch schreiben' }).click()
  await page.getByLabel('Kommentar').fill('Was für ein Abend!')
  await page.locator('form.add').getByRole('button', { name: 'Senden' }).click()
  await page.getByRole('button', { name: 'Antworten' }).click()
  await page.getByLabel('Antwort').fill('Absolut')
  await page.locator('.reply').getByRole('button', { name: 'Senden' }).click()
  await expect(page.locator('.note.nested')).toContainText('Absolut')
})

test('a comment with replies leaves a placeholder; the thread stays', async () => {
  page.once('dialog', (d) => d.accept())
  await page.getByRole('button', { name: 'Kommentar löschen' }).first().click()
  await expect(page.locator('.platzhalter')).toHaveText('Vom Ersteller gelöscht')
  await expect(page.locator('.note.nested')).toContainText('Absolut')
})

test('changes show up in other open tabs without reloading', async () => {
  const zweit = await zweitesGeraet()
  await zweit.goto(page.url())
  await expect(zweit.locator('.note.nested')).toContainText('Absolut')
  await page.getByRole('textbox', { name: 'Kommentar' }).fill('Live dabei')
  await page.locator('form.add').getByRole('button', { name: 'Senden' }).click()
  await expect(zweit.locator('.note', { hasText: 'Live dabei' })).toBeVisible({ timeout: 6000 })
  await zweit.context().close()
})

test('a watched film can be rated and discussed right in its detail sheet', async () => {
  await page.getByRole('button', { name: `${page.winner} – Details` }).first().click()
  const sheet = page.getByRole('dialog', { name: page.winner })
  await expect(sheet.getByRole('heading', { name: 'Eure Bewertung' })).toBeVisible()
  await expect(sheet.locator('.ours')).toHaveText('Ihr: ★ 3,0') // the rating given in the chronicle
  await sheet.getByRole('radio', { name: '5 von 5 Sternen' }).click()
  await expect(sheet.locator('.ours')).toHaveText('Ihr: ★ 5,0')
  await sheet.getByLabel('Kommentar', { exact: true }).fill('Aus der Detailansicht')
  await sheet.locator('form.add').getByRole('button', { name: 'Senden' }).click()
  await expect(sheet.locator('.note p', { hasText: 'Aus der Detailansicht' })).toBeVisible()
  await page.keyboard.press('Escape')
  // same data in the chronicle
  await expect(page.locator('main .entry .note p', { hasText: 'Aus der Detailansicht' })).toBeVisible()
  await expect(page.locator('main .entry .avg .num')).toHaveText('5,0')
})

test('detail sheet shows the trailer and where to watch (TMDB answers mocked)', async () => {
  const id = 493922 // Hereditary from the seed catalogue
  await page.route(`**/api/movies/${id}/anbieter`, (r) =>
    r.fulfill({
      json: {
        verfuegbar: true,
        quelle: 'JustWatch',
        link: 'https://www.themoviedb.org/movie/493922/watch?locale=DE',
        abo: [{ id: 9, name: 'Prime Video', logo: null, bei: [1] }, { id: 8, name: 'Netflix', logo: null, bei: [] }],
        kostenlos: [],
        leihen: [{ id: 2, name: 'Apple TV Store', logo: null }],
        kaufen: [],
      },
    }),
  )
  await page.route(`**/api/movies/${id}/trailer`, (r) =>
    r.fulfill({ json: { trailer: { key: 'abc123XYZ', name: 'Kinotrailer', sprache: 'de', typ: 'Trailer' } } }),
  )
  const youtube = []
  await page.route('https://www.youtube-nocookie.com/**', (r) => {
    youtube.push(r.request().url())
    return r.fulfill({ contentType: 'text/html', body: '<p>Trailer</p>' })
  })

  await nav('Finden')
  await page.getByRole('button', { name: 'Hereditary – Das Vermächtnis – Details' }).click()
  const sheet = page.getByRole('dialog', { name: /Hereditary/ })
  await expect(sheet.getByRole('heading', { name: "Wo läuft's?" })).toBeVisible()
  await expect(sheet.locator('.treffer')).toContainText('Läuft bei uns: Prime Video')
  await expect(sheet.locator('.logos li.unser')).toHaveCount(1)
  await expect(sheet.getByText('Daten: JustWatch')).toBeVisible()
  expect(youtube).toEqual([]) // nothing loads from YouTube before you press play
  await sheet.getByRole('button', { name: 'Trailer ansehen' }).click()
  await expect(sheet.locator('iframe')).toHaveAttribute('src', /youtube-nocookie\.com\/embed\/abc123XYZ/)
  await page.keyboard.press('Escape')
  await page.unroute('**/api/movies/**')
  await page.unroute('https://www.youtube-nocookie.com/**')
})

test('films not seen yet have no rating section', async () => {
  await nav('Finden')
  await page.getByRole('button', { name: 'Hereditary – Das Vermächtnis – Details' }).click()
  const sheet = page.getByRole('dialog', { name: /Hereditary/ })
  await expect(sheet.getByText('Ähnliche Filme')).toBeVisible()
  await expect(sheet.getByRole('heading', { name: 'Eure Bewertung' })).toHaveCount(0)
  await page.keyboard.press('Escape')
})

test('the sidebar folds to icons and remembers it', async () => {
  const sidebar = page.locator('.sidebar')
  const wide = (await sidebar.boundingBox()).width
  await page.getByRole('button', { name: 'Leiste einklappen' }).click()
  await expect.poll(async () => (await sidebar.boundingBox()).width).toBeLessThan(90)
  // still fully usable: links keep their names (for tooltips and screen readers)
  await nav('Unsere Filme')
  await expect(page.getByRole('heading', { name: 'Unsere Filme' })).toBeVisible()
  await page.reload()
  await expect.poll(async () => (await page.locator('.sidebar').boundingBox()).width).toBeLessThan(90)
  await page.getByRole('button', { name: 'Leiste ausklappen' }).click()
  await expect.poll(async () => (await page.locator('.sidebar').boundingBox()).width).toBe(wide)
})

test('wishes are off until the admin switches them on, then they can be voted on', async () => {
  await expect(page.getByRole('link', { name: 'Wünsche & Ideen', exact: true })).toHaveCount(0)
  await page.goto('/#/verwaltung/system')
  await page.getByRole('checkbox', { name: /Wünsche & Ideen/ }).check()
  await expect(page.locator('.toast', { hasText: 'Wünsche & Ideen sind jetzt für alle sichtbar' })).toBeVisible()
  await nav('Wünsche & Ideen')
  await page.getByLabel('Neuer Wunsch').fill('Serien unterstützen')
  await page.getByRole('button', { name: 'Wünschen' }).click()
  await page.getByRole('button', { name: /Abstimmen, 0 Stimmen/ }).click()
  await expect(page.getByRole('button', { name: /Abstimmen, 1 Stimmen/ })).toBeVisible()
})

test('the admin creates an invitation link for the group', async () => {
  await nav('Verwaltung')
  // Each group is its own card in the "Gruppen" tab.
  const gruppe = page.getByRole('article', { name: 'Unsere Gruppe' })
  await gruppe.getByRole('button', { name: 'Neuer Link' }).click()
  await gruppe.getByPlaceholder('z. B. Gruppenchat').fill('Gruppenchat')
  await gruppe.getByRole('button', { name: 'Link erzeugen und kopieren' }).click()
  await expect(gruppe.locator('.link', { hasText: 'Gruppenchat' })).toContainText('mit Freigabe')
  const { einladungen } = await (await page.request.get('/api/admin/gruppen/1/einladungen')).json()
  page.einladung = einladungen.find((e) => e.notiz === 'Gruppenchat').token
})


test('settings: notifications by kind, and a calendar feed that works without login', async () => {
  await page.goto('/#/profil/einstellungen/benachrichtigungen')
  await expect(page.getByRole('heading', { name: 'Benachrichtigungen' })).toBeVisible()
  const kino = page.getByRole('checkbox', { name: 'Das Kino geht live' })
  await expect(kino).toBeChecked()
  await kino.uncheck()
  await page.reload()
  await expect(page.getByRole('checkbox', { name: 'Das Kino geht live' })).not.toBeChecked()
  await page.getByRole('checkbox', { name: 'Das Kino geht live' }).check()

  await page.getByRole('button', { name: 'Kalender-Link erstellen' }).click()
  const link = await page.getByLabel('Kalender-Link').inputValue()
  expect(link).toMatch(/\/api\/kalender\/[\w-]{20,}\.ics$/)
  await expect(page.getByRole('link', { name: 'Im Kalender öffnen' })).toHaveAttribute('href', /^webcal:/)
  // A calendar app has no cookie: the token in the link is enough.
  const app = await page.context().browser().newContext()
  const feed = await app.request.get(link)
  expect(feed.ok()).toBeTruthy()
  expect(await feed.text()).toContain('SUMMARY:🎬 Filmabend')
  await app.close()
})

test('a theme and a font of your own, kept with the profile', async () => {
  await page.goto('/#/profil/einstellungen/darstellung')
  const akzent = () => page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim())
  expect(await akzent()).toBe('#e50914')
  // The theme's answer takes a moment; the font picked right after must not undo the theme.
  let erste = true
  await page.route('**/api/users/me/design', async (route) => {
    if (erste) {
      erste = false
      await new Promise((r) => setTimeout(r, 1500))
    }
    await route.continue()
  })
  await page.getByRole('radio', { name: 'Nacht' }).click()
  await page.getByRole('radio', { name: 'Space Grotesk' }).click()
  await expect.poll(akzent).toBe('#3b82f6')
  await page.waitForTimeout(2000) // both requests done
  await page.unroute('**/api/users/me/design')
  await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).fontFamily)).toContain('Space Grotesk')
  await page.reload()
  await expect.poll(akzent).toBe('#3b82f6')
  await expect(page.getByRole('radio', { name: 'Nacht' })).toHaveAttribute('aria-checked', 'true')
  await page.getByRole('radio', { name: 'Kino' }).click()
  await page.getByRole('radio', { name: 'Inter' }).click()
  await expect.poll(akzent).toBe('#e50914')
})

test('a profile picture replaces the initials everywhere', async () => {
  // A 1600×1200 "photo", drawn in the browser – the app shrinks it before uploading.
  const png = await page.evaluate(() => {
    const c = document.createElement('canvas')
    c.width = 1600
    c.height = 1200
    const x = c.getContext('2d')
    x.fillStyle = '#4a90e2'
    x.fillRect(0, 0, 1600, 1200)
    x.fillStyle = '#ffffff'
    x.beginPath()
    x.arc(800, 500, 300, 0, Math.PI * 2)
    x.fill()
    return c.toDataURL('image/png').split(',')[1]
  })
  await page.goto('/#/profil/einstellungen/profil')
  await page.getByLabel('Profilbild auswählen').setInputFiles({ name: 'ich.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') })
  await expect(page.locator('.toast', { hasText: 'Profilbild gespeichert' })).toBeVisible()
  const avatar = page.locator('.me .avatar img')
  await expect(avatar).toBeVisible()
  await expect.poll(() => avatar.evaluate((img) => img.naturalWidth)).toBe(256)
  await expect(page.getByRole('button', { name: 'Bild ändern' })).toBeVisible()
})

test('achievements: the unlock pops up, and the showcase shows it', async () => {
  // Unlocks are shown one after another; the picture's may queue behind another one.
  await expect(page.locator('.popup', { hasText: 'Gesicht zeigen' })).toBeVisible({ timeout: 15_000 })
  await nav('Profil & Erfolge')
  await expect(page.getByRole('heading', { name: 'Marc', exact: true })).toBeVisible()
  await expect(page.locator('.stand')).toContainText('Level 1')
  await expect(page.locator('.kachel', { hasText: 'Gesicht zeigen' })).toHaveClass(/offen/)
  // The catalogue is folded by category; secret ones stay hidden even when opened.
  await page.locator('details.kategorie', { hasText: 'Geheim' }).locator('summary').click()
  await expect(page.locator('.kachel', { hasText: '???' }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Meine Vitrine' }).click()
  await page.getByRole('button', { name: 'Gesicht zeigen in die Vitrine' }).click()
  await expect(page.locator('.vitrine')).toContainText('Gesicht zeigen')
  await nav('Filmabend')
})

test('the sidebar shows facts about screenmates, the about page takes an imprint and donation links', async () => {
  await expect(page.locator('.statistik .fakt')).toContainText(/\d/)
  await page.getByRole('link', { name: 'Über · Impressum' }).click()
  await expect(page.getByRole('heading', { name: 'Über screenmates' })).toBeVisible()
  const impressum = page.locator('section#impressum')
  await impressum.getByRole('button', { name: 'Bearbeiten' }).click()
  await page.getByLabel('Impressum (Markdown)').fill('Marc Muster\n\nkontakt@example.org')
  await page.getByRole('button', { name: 'Speichern' }).click()
  await expect(impressum).toContainText('kontakt@example.org')
  const spenden = page.locator('section#spenden')
  await spenden.getByRole('button', { name: 'Bearbeiten' }).click()
  await page.getByLabel('Ko-fi-Name').fill('https://ko-fi.com/screenmates')
  await page.getByRole('button', { name: 'Speichern' }).click()
  await expect(spenden.getByRole('link', { name: 'Ko-fi' })).toHaveAttribute('href', 'https://ko-fi.com/screenmates')
  await expect(spenden.getByRole('img', { name: 'QR-Code für Ko-fi' })).toBeVisible()
  // Without an invitation the app stays closed, the imprint doesn't.
  const fremd = await page.context().browser().newPage()
  await fremd.goto('/#/ueber')
  await expect(fremd.getByText('Nur mit Einladung')).toBeVisible()
  await expect(fremd.locator('section#impressum')).toContainText('kontakt@example.org')
  await fremd.close()
})

test('info card on the evening page renders sanitised markdown', async () => {
  await nav('Filmabend')
  await page.getByRole('button', { name: 'Infos hinzufügen' }).click()
  await page.getByLabel('Infos (Markdown)').fill('# Regeln\n\n**Keine Handys.**\n\n<img src=x onerror="window.pwned=1">')
  await page.getByRole('button', { name: 'Speichern' }).click()
  await expect(page.locator('.prose h1')).toHaveText('Regeln')
  expect(await page.evaluate(() => window.pwned)).toBeUndefined()
})

test('a film watched a year ago comes back as a memory', async () => {
  const vorEinemJahr = new Date()
  vorEinemJahr.setFullYear(vorEinemJahr.getFullYear() - 1)
  vorEinemJahr.setHours(20, 0, 0, 0)
  const r = await page.request.post('/api/watched', { data: { movie_id: 948, watched_at: vorEinemJahr.toISOString() } })
  expect(r.ok()).toBeTruthy()
  await page.reload()
  const erinnerung = page.locator('.erinnerung')
  // CI clocks run on UTC; near midnight the German date may already differ by a day.
  await expect(erinnerung.getByRole('heading', { name: /^(Heute|Diese Woche) vor einem Jahr$/ })).toBeVisible()
  await expect(erinnerung).toContainText('Halloween')
})

test('the year in review sums up the group’s films, also as a story to tap through', async () => {
  await nav('Unsere Filme')
  await page.getByRole('navigation', { name: 'Liste' }).getByRole('link', { name: /Rückblick/ }).click()
  const jahr = new Date().getFullYear()
  await expect(page.getByRole('heading', { name: `Euer Filmjahr ${jahr}` })).toBeVisible()
  await expect(page.locator('.kachel').first()).toContainText(/\d+\s*Filme?/)
  await expect(page.locator('.film').first()).toBeVisible()
  await page.getByRole('button', { name: 'Als Story ansehen' }).click()
  const story = page.getByRole('dialog', { name: `Euer Filmjahr ${jahr}` })
  await expect(story).toContainText('Euer Filmjahr.')
  await page.keyboard.press('ArrowRight')
  await expect(story).toContainText('Ihr habt')
  await page.keyboard.press('Escape')
  await expect(story).toBeHidden()
  await nav('Filmabend') // the story goes on there
})

test('who will like a film: an honest hint until there are enough ratings', async () => {
  await page.locator('.erinnerung').getByRole('button', { name: 'Halloween', exact: true }).click()
  const detail = page.getByRole('dialog', { name: 'Halloween' })
  await expect(detail.getByText('Wem gefällt’s?')).toBeVisible()
  await expect(detail.locator('.wem')).toContainText(/Ab 8 Bewertungen .* Noch zu wenig: Marc \(\d\/8\)/)
  await page.keyboard.press('Escape')
})

/** A new browser opens the invitation link it got. */
async function throughTheDoor(p) {
  await p.goto(`/#/einladung/${page.einladung}`)
  await expect(p.getByRole('dialog', { name: 'Namen wählen' })).toBeVisible()
  await expect(p.getByRole('dialog')).toContainText('Du bist eingeladen in „Unsere Gruppe“')
}

test('a second device needs a login code to use the name', async ({ browser }) => {
  const phone = await browser.newPage({ viewport: { width: 390, height: 844 } })
  await phone.goto('/#/abend')
  // First the door: nothing of the group is visible, a made-up code doesn't open it.
  await expect(phone.getByText('Nur mit Einladung')).toBeVisible()
  await expect(phone.getByRole('navigation')).toHaveCount(0)
  await phone.getByLabel('Einladungslink oder Code').fill('ausgedachter-code')
  await phone.getByRole('button', { name: 'Rein' }).click()
  await expect(phone.getByRole('alert')).toContainText('gilt nicht')
  // An invitation lets you in – but nobody else's name can simply be picked.
  await throughTheDoor(phone)
  const dialog = phone.getByRole('dialog', { name: 'Namen wählen' })
  await expect(dialog.getByRole('button', { name: 'Marc' })).toHaveCount(0)
  await dialog.getByRole('button', { name: 'Ich habe schon einen Namen' }).click()
  await dialog.getByLabel('Anmeldecode').fill('AAAA-BBBB')
  await dialog.getByRole('button', { name: 'Anmelden', exact: true }).click()
  await expect(dialog.getByRole('alert')).toContainText('gilt nicht')
  // Marc makes a code on his laptop …
  await page.goto('/#/profil/einstellungen')
  await expect(page.getByText('Auf 1 Gerät angemeldet')).toBeVisible()
  await page.getByRole('button', { name: 'Anderes Gerät verbinden' }).click()
  await expect(page.getByRole('img', { name: 'QR-Code mit dem Anmeldelink' })).toBeVisible()
  const code = await page.locator('.anmeldecode output').textContent()
  expect(code).toMatch(/^[A-Z2-9]{4}-[A-Z2-9]{4}$/)
  // … and types it on the phone (capitals and dash don't matter).
  await dialog.getByLabel('Anmeldecode').fill(code.toLowerCase().replace('-', ''))
  await dialog.getByRole('button', { name: 'Anmelden', exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(phone.locator('.me')).toContainText('Marc')
  await page.reload()
  await expect(page.getByText('Auf 2 Geräten angemeldet')).toBeVisible()
  // On the phone the areas sit in a bar at the bottom; "Mehr" holds the rest.
  await phone.getByRole('button', { name: 'Mehr' }).click()
  await phone.getByRole('menuitem', { name: /Wünsche & Ideen/ }).click()
  await expect(phone).toHaveURL(/#\/wuensche/)
  // The picture at the top leads to the profile.
  await phone.locator('.me').click()
  await expect(phone.locator('.stand')).toContainText('Level')
  await phone.close()
})

test('the door speaks English to an English browser, and switches back', async ({ browser }) => {
  const ctx = await browser.newContext({ locale: 'en-GB' })
  const gast = await ctx.newPage()
  await gast.goto('/')
  await expect(gast.getByRole('heading', { name: 'You need an invitation link to get in here.' })).toBeVisible()
  await gast.getByRole('button', { name: 'Deutsch' }).click()
  await expect(gast.getByRole('button', { name: 'Rein' })).toBeVisible()
  await gast.reload()
  await expect(gast.getByRole('button', { name: 'Rein' })).toBeVisible() // this device remembers
  await ctx.close()
})

test('a newcomer requests a name and an admin approves it', async ({ browser }) => {
  const lena = await browser.newPage()
  await throughTheDoor(lena)
  await lena.getByPlaceholder('Neuer Name').fill('Lena')
  await lena.getByRole('button', { name: 'Beantragen' }).click()
  await expect(lena.getByRole('heading', { name: 'Antrag gestellt' })).toBeVisible()
  await lena.getByRole('button', { name: 'Alles klar' }).click()

  // The admin sees the request in the navigation and approves it.
  await page.reload()
  await expect(page.locator('.antraege')).toHaveText('1')
  await nav('Verwaltung')
  await page.getByRole('link', { name: /^Personen/ }).click()
  const antrag = page.locator('.panel', { has: page.getByRole('heading', { name: /Anträge/ }) })
  await expect(antrag).toContainText('Lena')
  await antrag.getByRole('button', { name: 'Freigeben' }).click()
  await expect(page.locator('.toast', { hasText: '„Lena“ freigegeben' })).toBeVisible()
  await expect(page.locator('.antraege')).toHaveCount(0)

  await lena.reload()
  await lena.getByRole('button', { name: 'Lena' }).click()
  await lena.getByRole('dialog', { name: 'Willkommen bei screenmates' }).getByRole('button', { name: 'Überspringen' }).click()
  await expect(lena.locator('.me')).toContainText('Lena')
  await expect(lena.locator('.admin-badge')).toHaveCount(0)
  page.lena = lena
})

test('admins rename someone and log them out everywhere', async () => {
  const person = page.locator('.person', { hasText: 'Lena' })
  await person.getByRole('button', { name: 'Umbenennen' }).click()
  await page.getByLabel('Neuer Name für Lena').fill('Lena M.')
  await page.getByLabel('Neuer Name für Lena').press('Enter')
  await expect(page.locator('.toast', { hasText: 'Umbenannt in „Lena M.“' })).toBeVisible()
  await expect(page.locator('.person', { hasText: 'Lena M.' })).toContainText('1 Gerät')

  page.once('dialog', (d) => d.accept())
  await page.locator('.person', { hasText: 'Lena M.' }).getByRole('button', { name: 'Überall abmelden' }).click()
  await expect(page.locator('.person', { hasText: 'Lena M.' })).toContainText('nicht angemeldet')
  // Her browser is back at the door (its next request – a click, or a background poll – finds it closed).
  const lena = page.lena
  // The page may already be reloading itself; either way it ends up at the door.
  await lena.reload().catch(() => {})
  await expect(lena.getByText('Nur mit Einladung')).toBeVisible({ timeout: 15_000 })
  await lena.close()
})

test('after clearing the evening, the case opens for everyone again', async () => {
  // A seen opening used to be remembered by its id – and ids start at 1 again after a reset.
  await page.evaluate(() => localStorage.setItem('screenmates.kisteGesehen', '999'))
  await page.goto('/#/verwaltung/gefahr')
  const zone = page.getByRole('region', { name: 'Gefahrenzone' })
  await zone.getByRole('checkbox', { name: /Filmabend/ }).check()
  await zone.getByRole('button', { name: 'Ausgewähltes löschen' }).click()
  const dialog = page.getByRole('dialog', { name: 'Wirklich löschen?' })
  await dialog.getByLabel('Bestätigung').fill('LÖSCHEN')
  await dialog.getByRole('button', { name: 'Endgültig löschen' }).click()
  await page.waitForEvent('load')
  expect((await page.request.post('/api/suggestions', { data: { movie_id: 694 } })).ok()).toBeTruthy()
  await page.goto('/#/abend')
  await page.getByRole('button', { name: 'Für alle öffnen' }).click()
  const buehne = page.getByRole('dialog', { name: 'Kiste öffnen' })
  await expect(buehne).toBeVisible()
  await page.keyboard.press('Escape')
  await page.keyboard.press('Enter')
  await expect(buehne).toBeHidden()
  // Take the film of the evening down again: later steps (and the Kino's newcomers) start clean.
  const { aktuell } = await (await page.request.get('/api/kiste')).json()
  expect((await page.request.delete(`/api/kiste/${aktuell.id}`)).ok()).toBeTruthy()
})

test('the danger zone clears an area of the group only after typing the word', async () => {
  expect((await page.request.post('/api/kino/chat', { data: { text: 'Test, Test' } })).ok()).toBeTruthy()
  await page.goto('/#/verwaltung/gefahr')
  const zone = page.getByRole('region', { name: 'Gefahrenzone' })
  await expect(zone).toContainText('in der Gruppe „Unsere Gruppe“')
  await expect(zone.getByRole('checkbox', { name: /Wünsche/ })).toHaveCount(0) // server-wide: command line only
  await zone.getByRole('checkbox', { name: /Kino/ }).check()
  await zone.getByRole('button', { name: 'Ausgewähltes löschen' }).click()
  const dialog = page.getByRole('dialog', { name: 'Wirklich löschen?' })
  const los = dialog.getByRole('button', { name: 'Endgültig löschen' })
  await expect(los).toBeDisabled()
  await dialog.getByLabel('Bestätigung').fill('löschen')
  await los.click()
  await expect(page.getByText(/Gelöscht – Sicherung: backup-vor-reset-/)).toBeVisible()
  await page.waitForEvent('load') // the app starts afresh
  expect((await (await page.request.get('/api/kino/chat')).json()).eintraege).toEqual([])
  await page.goto('/#/wuensche') // wishes belong to the server: still there
  await expect(page.locator('main')).toContainText('Serien unterstützen')
  await page.goto('/#/abend')
})

test('a second group has its own movie night', async () => {
  await nav('Verwaltung')
  await page.getByRole('tab', { name: 'Neue Gruppe' }).click()
  await page.getByRole('textbox', { name: 'Neue Gruppe' }).fill('Horror-Crew')
  await page.getByRole('button', { name: 'Gruppe anlegen' }).click()
  // The new group opens right away, as a card of its own.
  const crew = page.getByRole('article', { name: 'Horror-Crew' })
  await crew.getByLabel('Mitglied für Horror-Crew wählen').selectOption({ label: 'Marc' })
  await crew.getByRole('button', { name: 'Aufnehmen' }).click()
  await expect(crew.locator('.mitglieder li')).toHaveCount(1)
  // Now in two groups: the sidebar offers to switch.
  await page.reload()
  const wahl = page.getByLabel('Gruppe wechseln')
  await expect(wahl).toHaveValue('1')
  const gesehen = async () => (await (await page.request.get('/api/watched')).json()).watched.length
  expect(await gesehen()).toBeGreaterThan(0)
  await Promise.all([page.waitForEvent('load'), wahl.selectOption({ label: 'Horror-Crew' })])
  expect(await gesehen()).toBe(0)
  // In this group Marc hasn't said he's in yet (he did in the first one).
  await nav('Filmabend')
  await expect(page.locator('.crew')).toBeVisible()
  await expect(page.locator('.crew')).not.toContainText('Marc')
  await Promise.all([page.waitForEvent('load'), page.getByLabel('Gruppe wechseln').selectOption({ label: 'Unsere Gruppe' })])
  expect(await gesehen()).toBeGreaterThan(0)
})

test('someone downloads their data and then deletes their name', async ({ browser }) => {
  const link = await (await page.request.post('/api/admin/gruppen/1/einladungen', { data: { direkt: true } })).json()
  const tom = await browser.newPage()
  await tom.goto(`/#/einladung/${link.token}`)
  await tom.getByPlaceholder('Neuer Name').fill('Tom')
  await tom.getByRole('button', { name: 'Anlegen' }).click()
  await tom.getByRole('dialog', { name: 'Willkommen bei screenmates' }).getByRole('button', { name: 'Überspringen' }).click()
  await tom.goto('/#/profil/einstellungen')
  const [download] = await Promise.all([tom.waitForEvent('download'), tom.getByRole('link', { name: 'Alles herunterladen' }).click()])
  expect(download.suggestedFilename()).toBe('screenmates-Tom.json')
  const daten = JSON.parse(readFileSync(await download.path(), 'utf8'))
  expect(daten.profile.name).toBe('Tom')
  expect(daten.groups.map((g) => g.group)).toEqual(['Unsere Gruppe'])

  tom.once('dialog', (d) => d.accept('Tom'))
  await tom.getByRole('button', { name: 'Namen löschen' }).click()
  // The name is gone; the browser still holds its invitation and may make a new one.
  await expect(tom.getByRole('dialog', { name: 'Namen wählen' })).toBeVisible({ timeout: 10_000 })
  const namen = (await (await page.request.get('/api/users')).json()).users.map((u) => u.name)
  expect(namen).not.toContain('Tom')
  await tom.close()
})

