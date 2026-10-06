import { terminText } from './einladung'

// What happened in the group, as one line each (the feed on the "Neuigkeiten" page).
export const EVENT_TEXT = {
  gesehen: (e) => `„${e.film}“ wurde geschaut`,
  vorschlag: (e) => `${e.wer ?? 'Jemand'} schlägt „${e.film}“ vor`,
  kommentar: (e) => `${e.wer ?? 'Jemand'}: „${e.text}“`,
  wunsch: (e) => `${e.wer ?? 'Jemand'} wünscht sich: ${e.text}`,
  veto: (e) => `${e.wer ?? 'Jemand'} legt ein Veto gegen „${e.film}“ ein`,
  erfolg: (e) => `${e.emoji} ${e.wer ?? 'Jemand'} hat ${e.name} freigeschaltet`,
  gastgeber: (e) =>
    e.art === 'uebergabe'
      ? `${e.von ?? 'Jemand'} gibt den Gastgeber-Stab an ${e.wer ?? 'jemanden'}`
      : e.art === 'abstimmung'
        ? `${e.wer ?? 'Jemand'} ist Gastgeber – per Abstimmung (${e.stand})`
        : `${e.wer ?? 'Jemand'} übernimmt den Gastgeber-Stab`,
  kiste: (e) => `${e.wer ?? 'Jemand'} öffnet die Kiste: „${e.film}“`,
  termin: (e) => {
    const t = terminText({ termin: e.termin })
    return `${e.wer ?? 'Jemand'} legt den Termin fest: ${t.tag}, ${t.zeit}`
  },
  umfrage: (e) => {
    const t = terminText({ termin: e.termin })
    return `${e.wer ?? 'Jemand'} schlägt einen Termin zur Abstimmung vor: ${t.tag}, ${t.zeit}`
  },
}

export const ereignisText = (e) => (EVENT_TEXT[e.typ] ? EVENT_TEXT[e.typ](e) : '')