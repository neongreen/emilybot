# JS examples

These are actually set in the CRC discord.

## util/date/calendar

.set util/date/calendar.run

```js
$nthSunday = (y, m, n) => {
  let first = new Date(Date.UTC(y, m, 1))
  return new Date(Date.UTC(y, m, 1 + ((7 - first.getUTCDay()) % 7) + 7 * (n-1)))
}
$lastSunday = (y, m) => {
  let last = new Date(Date.UTC(y, m + 1, 0))
  return new Date(Date.UTC(y, m, last.getUTCDate() - last.getUTCDay()))
}
```

## util/date/dst

.set util/date/dst.run

```js
$.cmd("util/date/calendar")
$dst = {
  isUS: d => {
    let y = d.getUTCFullYear()
    return d >= $nthSunday(y, 2, 2) && d < $nthSunday(y, 10, 1)
  },
  isEU: d => {
    let y = d.getUTCFullYear()
    return d >= $lastSunday(y, 2) && d < $lastSunday(y, 9)
  },
  isAUSydney: d => {
    let y = d.getUTCFullYear()
    return d < new Date(Date.UTC(y, 6, 1))
      ? d >= $nthSunday(y-1, 9, 1) && d < $nthSunday(y, 3, 1)
      : d >= $nthSunday(y, 9, 1) && d < $nthSunday(y+1, 3, 1)
  }
}
```

## util/date/country

.set util/date/country.run

```js
$.cmd("util/date/dst")
$countryOffsetMinutes = (token, now = new Date()) => {
  let t = token.trim().toLowerCase()

  let FIXED_COUNTRY = {
    china: 480, prc: 480, singapore: 480, malaysia: 480,
    india: 330,
    japan: 540, "south korea": 540, korea: 540, "republic of korea": 540,
    uae: 240, "united arab emirates": 240,
    saudi: 180, "saudi arabia": 180,
    turkey: 180, turkiye: 180
  }
  if (FIXED_COUNTRY[t] != null) return FIXED_COUNTRY[t]

  let UK_NAMES = ["uk","united kingdom","great britain","britain","england","scotland","wales","northern ireland"]
  if (UK_NAMES.includes(t)) return $dst.isEU(now) ? 60 : 0

  let CET_COUNTRIES = [
    "poland","germany","france","italy","spain","netherlands","belgium","austria","switzerland","norway","denmark","sweden","czechia","czech republic","slovakia","hungary","slovenia","croatia","serbia","bosnia","bosnia and herzegovina","montenegro","north macedonia","albania","andorra","monaco","san marino","vatican","vatican city"
  ]
  if (CET_COUNTRIES.includes(t)) return $dst.isEU(now) ? 120 : 60

  let EET_COUNTRIES = [
    "finland","greece","romania","bulgaria","cyprus","estonia","latvia","lithuania","ukraine"
  ]
  if (EET_COUNTRIES.includes(t)) return $dst.isEU(now) ? 180 : 120

  return null
}
```

## util/date/tz

.set util/date/tz.run

```js
$.cmd("util/date/dst")
$.cmd("util/date/country")
$parseUtcOffsetToken = tz => {
  let t = tz.toUpperCase().replace(".", ":")
  if (t.startsWith("GMT+")) t = t.replace("GMT+", "UTC+")
  if (t.startsWith("GMT-")) t = t.replace("GMT-", "UTC-")
  if (!(t.startsWith("UTC+") || t.startsWith("UTC-"))) return null
  let sign = t.includes("+") ? 1 : -1
  let [, offPart] = t.split(sign === 1 ? "UTC+" : "UTC-")
  let [oh, om] = offPart.split(":")
  return sign * (parseInt(oh, 10) * 60 + (om ? parseInt(om, 10) : 0))
}

$tzOffsetMinutes = (token, now = new Date()) => {
  token = token.toUpperCase()
  let FIXED_ABBR = { UTC:0, GMT:0, IST:330, MSK:180, JST:540, KST:540, PST:-480, PDT:-420, MST:-420, MDT:-360, CST:-360, CDT:-300, EST:-300, EDT:-240, CET:60, CEST:120, EET:120, EEST:180, AEST:600, AEDT:660, BST:60 }
  let explicit = $parseUtcOffsetToken(token)
  if (explicit != null) return explicit
  if (FIXED_ABBR[token] != null) return FIXED_ABBR[token]
  let byCountry = $countryOffsetMinutes(token, now)
  if (byCountry != null) return byCountry
  if (["PT","MT","CT","ET"].includes(token)) {
    let us = $dst.isUS(now)
    return token === "PT" ? (us ? -420 : -480) : token === "MT" ? (us ? -360 : -420) : token === "CT" ? (us ? -300 : -360) : (us ? -240 : -300)
  }
  let eu = $dst.isEU(now)
  if (token === "UK") return eu ? 60 : 0
  if (token === "CE" || token === "CET") return eu ? 120 : 60
  if (token === "EE" || token === "EET") return eu ? 180 : 120
  let au = $dst.isAUSydney(now)
  if (token === "AET" || token === "AUET") return au ? 660 : 600
  throw new Error(`unknown timezone: ${token}`)
}
```

## when

.set when.run

```js
$.cmd("util")
$.cmd("util/date/tz")

let TIME_RE_HM = /^\s*(\d{1,2})[:.](\d{2})\s*(am|pm)?\s+(.+)$/i
let TIME_RE_H = /^\s*(\d{1,2})\s*(am|pm)?\s+(.+)$/i

function makeDiscordTimestamp(input, style) {
  let hour, minute, ampm, tzToken
  let m = input.match(TIME_RE_HM)
  if (m) {
    ;[, hour, minute, ampm, tzToken] = m
    hour = parseInt(hour, 10)
    minute = parseInt(minute, 10)
  } else {
    m = input.match(TIME_RE_H)
    if (!m) throw new Error("format: HH[:MM][am|pm] <timezone>")
    ;[, hour, ampm, tzToken] = m
    hour = parseInt(hour, 10)
    minute = 0
  }

  if (ampm) {
    let pm = ampm.toLowerCase() === "pm"
    hour = hour === 12 ? (pm ? 12 : 0) : (pm ? hour + 12 : hour)
  }

  let offsetMin = $tzOffsetMinutes(tzToken, new Date())
  let now = new Date()
  let msUTC = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), hour, minute) - offsetMin * 60000
  return `<t:${Math.floor(msUTC / 1000)}:${style}>`
}

console.log(`**${$msg}** in your local time is ${makeDiscordTimestamp($msg, "F")} (${makeDiscordTimestamp($msg, "R")})`)
```
