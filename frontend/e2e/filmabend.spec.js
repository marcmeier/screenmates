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
  // The first name of a fresh install administrates the group.
  await expect(page.locator('.admin-badge')).toBeVisible()
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
  await page.getByRole('button', { name: 'Science Fiction' }).click()
  await expect(page.locator('.card')).toHaveCount(2)
  await page.getByRole('button', { name: 'Science Fiction' }).click()
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
  await page.getByRole('button', { name: 'Science Fiction' }).click() // any change reloads the grid
  await expect(page.locator('.gesamt')).toHaveText('60 Filme')
  await expect(page.locator('.grid .card')).toHaveCount(20)
  for (let i = 0; i < 12 && (await page.locator('.grid .card').count()) < 60; i++) {
    await page.mouse.wheel(0, 4000)
    await page.waitForTimeout(250)
  }
  await expect(page.locator('.grid .card')).toHaveCount(60)
  await expect(page.getByRole('button', { name: 'Mehr laden' })).toHaveCount(0)
  await page.unroute('**/api/discover?**')
  await page.getByRole('button', { name: 'Science Fiction' }).click()
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
  await expect(page.getByRole('list', { name: 'Kiste mit 1 Film' })).toContainText('Shining')
  await alien.getByRole('button', { name: 'Veto zurück' }).click()
  await expect(alien).not.toHaveClass(/vetoed/)
  await expect(page.getByRole('list', { name: 'Kiste mit 2 Filmen' }).getByRole('listitem')).toHaveCount(2)
})

test('the case shows each film with its odds', async () => {
  const inhalt = page.getByRole('list', { name: 'Kiste mit 2 Filmen' })
  await expect(inhalt.getByRole('listitem')).toHaveText([/Alien.*50 %/, /Shining.*50 %/])
})

test('opening the case: Escape skips the animation, the reveal names the winner', async () => {
  await page.getByRole('button', { name: 'Kiste öffnen' }).click()
  const buehne = page.getByRole('dialog', { name: 'Kiste öffnen' })
  await expect(buehne.locator('.item')).toHaveCount(64)
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
  await expect(page.locator('.winner strong')).toHaveText(gezogen)
})

test('the full opening runs by itself and the winner can be marked as watched', async () => {
  await page.getByRole('button', { name: 'Kiste öffnen' }).click()
  const weiter = page.getByRole('dialog', { name: 'Kiste öffnen' }).getByRole('button', { name: 'Weiter' })
  await expect(weiter).toBeVisible({ timeout: 12000 })
  await weiter.click()
  const winner = page.locator('.winner strong')
  await expect(winner).toHaveText(/Alien|Shining/)
  page.winner = await winner.textContent()
  await page.locator('.winner').getByRole('button', { name: 'Geschaut' }).click()
  await expect(page.locator('.sugg')).toHaveCount(1)
})

test('a date for the evening and an invitation card for the group chat', async () => {
  // A 1×1 PNG with the CORS header TMDB sends: the card's posters stay offline and deterministic.
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64')
  await page.route(/image\.tmdb\.org.*[?&]karte/, (r) =>
    r.fulfill({ body: png, contentType: 'image/png', headers: { 'access-control-allow-origin': '*' } }),
  )
  await page.getByRole('button', { name: 'Termin festlegen' }).click()
  const dialog = page.getByRole('dialog', { name: 'Termin für den Filmabend' })
  await dialog.getByPlaceholder('z. B. bei Marc').fill('bei Marc')
  await dialog.getByRole('button', { name: 'Speichern' }).click()
  await expect(dialog).toBeHidden()
  await expect(page.locator('.crew .termin')).toContainText(/Freitag, \d+\. \w+, 20:00 Uhr · bei Marc/)
  await expect(page.locator('.feed')).toContainText('Marc legt den Termin fest: Freitag')

  await page.getByRole('button', { name: 'Einladen' }).click()
  const einladung = page.getByRole('dialog', { name: 'Zum Filmabend einladen' })
  await expect(einladung.locator('.text')).toContainText(/Filmabend am Freitag, .* um 20:00 Uhr \(bei Marc\)/)
  await expect(einladung.locator('.text')).toContainText('Dabei: Marc')
  await expect(einladung.locator('.text')).toContainText('#/abend')
  const karte = einladung.getByRole('img', { name: 'Einladungskarte' })
  await expect(karte).toBeVisible()
  expect(await karte.evaluate((img) => [img.naturalWidth, img.naturalHeight])).toEqual([1080, 1350])
  await expect(einladung.getByRole('link', { name: 'Bild speichern' })).toHaveAttribute('download', 'filmabend.png')
  await page.keyboard.press('Escape')
  await page.unroute(/image\.tmdb\.org.*[?&]karte/)
})

test('rating: the n-th star gives n stars', async () => {
  await nav('Unsere Filme')
  await page.getByRole('navigation', { name: 'Liste' }).getByRole('link', { name: /Gesehen/ }).click()
  await expect(page.locator('.entry h3')).toContainText(page.winner)
  await page.getByRole('radio', { name: '3 von 5 Sternen' }).click()
  await expect(page.locator('.avg .num')).toHaveText('3,0')
})

test('guestbook threads replies', async () => {
  await page.getByLabel('Kommentar').fill('Was für ein Abend!')
  await page.locator('form.add').getByRole('button', { name: 'Senden' }).click()
  await page.getByRole('button', { name: 'Antworten' }).click()
  await page.getByLabel('Antwort').fill('Absolut')
  await page.locator('.reply').getByRole('button', { name: 'Senden' }).click()
  await expect(page.locator('.note.nested')).toContainText('Absolut')
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
  await sheet.getByRole('button', { name: 'Trailer' }).click()
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

test('wishes can be voted on', async () => {
  await nav('Wünsche & Ideen')
  await page.getByLabel('Neuer Wunsch').fill('Serien unterstützen')
  await page.getByRole('button', { name: 'Wünschen' }).click()
  await page.getByRole('button', { name: /Abstimmen, 0 Stimmen/ }).click()
  await expect(page.getByRole('button', { name: /Abstimmen, 1 Stimmen/ })).toBeVisible()
})

test('the admin closes the door with an access question', async () => {
  await nav('Einstellungen')
  await expect(page.getByText('Noch keine Zugangsfrage')).toBeVisible()
  await page.getByLabel('Frage').fill('Welchen Film haben wir zuerst zusammen geschaut?')
  await page.getByRole('button', { name: 'Film wählen' }).click()
  await page.getByPlaceholder('Antwort-Film suchen').fill('halloween')
  await page.locator('.picker .results button', { hasText: 'Halloween' }).first().click()
  await page.getByRole('button', { name: 'Speichern' }).click()
  await expect(page.locator('.toast', { hasText: 'Zugangsfrage gespeichert' })).toBeVisible()
  await expect(page.getByText('Noch keine Zugangsfrage')).toBeHidden()
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

test('who will like a film: an honest hint until there are enough ratings', async () => {
  await page.locator('.erinnerung').getByRole('button', { name: 'Halloween', exact: true }).click()
  const detail = page.getByRole('dialog', { name: 'Halloween' })
  await expect(detail.getByText('Wem gefällt’s?')).toBeVisible()
  await expect(detail.locator('.wem')).toContainText(/Ab 8 Bewertungen .* Noch zu wenig: Marc \(\d\/8\)/)
  await page.keyboard.press('Escape')
})

/** A new browser at the door: answers the access question. */
async function throughTheDoor(p) {
  await p.goto('/#/abend')
  await expect(p.getByRole('heading', { name: 'Welchen Film haben wir zuerst zusammen geschaut?' })).toBeVisible()
  await p.getByLabel('Film suchen').fill('halloween')
  await p.locator('.results button', { hasText: 'Halloween' }).first().click()
  await expect(p.getByRole('dialog', { name: 'Namen wählen' })).toBeVisible()
}

test('a second device must know the film to use the name', async ({ browser }) => {
  const phone = await browser.newPage({ viewport: { width: 390, height: 844 } })
  await phone.goto('/#/abend')
  // First the door: nothing of the group is visible, a wrong film doesn't open it.
  await expect(phone.getByText('Nur für unsere Gruppe')).toBeVisible()
  await expect(phone.getByRole('navigation')).toHaveCount(0)
  await phone.getByLabel('Film suchen').fill('alien')
  await phone.locator('.results button', { hasText: 'Alien' }).first().click()
  await expect(phone.getByRole('alert')).toContainText('nicht der richtige Film')
  await throughTheDoor(phone)
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
  await nav('Einstellungen')
  const antrag = page.locator('.panel', { has: page.getByRole('heading', { name: /Anträge/ }) })
  await expect(antrag).toContainText('Lena')
  await antrag.getByRole('button', { name: 'Freigeben' }).click()
  await expect(page.locator('.toast', { hasText: '„Lena“ freigegeben' })).toBeVisible()
  await expect(page.locator('.antraege')).toHaveCount(0)

  await lena.reload()
  await lena.getByRole('button', { name: 'Lena' }).click()
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
  // Her browser is back at the door with its next request.
  const lena = page.lena
  await lena.getByRole('link', { name: 'Finden', exact: true }).click()
  await expect(lena.getByText('Nur für unsere Gruppe')).toBeVisible()
  await lena.close()
})
