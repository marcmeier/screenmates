import { terminText } from './einladung'
import { t } from './i18n'

// What happened in the group, as one line each (the feed on the "Neuigkeiten" page).
const wer = (e) => e.wer ?? t('allg.jemand')
const termin = (e) => terminText({ termin: e.termin })

export const EVENT_TEXT = {
  gesehen: (e) => t('aktivitaet.gesehen', { film: e.film }),
  vorschlag: (e) => t('aktivitaet.vorschlag', { wer: wer(e), film: e.film }),
  kommentar: (e) => t('aktivitaet.kommentar', { wer: wer(e), text: e.text }),
  wunsch: (e) => t('aktivitaet.wunsch', { wer: wer(e), text: e.text }),
  veto: (e) => t('aktivitaet.veto', { wer: wer(e), film: e.film }),
  erfolg: (e) => t('aktivitaet.erfolg', { emoji: e.emoji, wer: wer(e), name: e.name }),
  gastgeber: (e) =>
    e.art === 'uebergabe'
      ? t('aktivitaet.stabUebergabe', { von: e.von ?? t('allg.jemand'), an: e.wer ?? t('allg.jemanden') })
      : e.art === 'abstimmung'
        ? t('aktivitaet.stabAbstimmung', { wer: wer(e), stand: e.stand })
        : t('aktivitaet.stabUebernahme', { wer: wer(e) }),
  kiste: (e) => t('aktivitaet.kiste', { wer: wer(e), film: e.film }),
  termin: (e) => t('aktivitaet.termin', { wer: wer(e), tag: termin(e).tag, zeit: termin(e).zeit }),
  umfrage: (e) => t('aktivitaet.umfrage', { wer: wer(e), tag: termin(e).tag, zeit: termin(e).zeit }),
}

export const ereignisText = (e) => (EVENT_TEXT[e.typ] ? EVENT_TEXT[e.typ](e) : '')
