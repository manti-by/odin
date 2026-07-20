/**
 * Convert a Date to the value string used by <input type="datetime-local">
 * in the local timezone (e.g. "2026-07-20T14:30").
 */
export function toLocalDatetimeValue(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

/**
 * Parse a datetime-local value (no timezone, interpreted as local time) and
 * return a proper UTC ISO string for the API.
 *
 * `new Date("2026-07-20T14:30")` is treated as **local** time per the ES
 * spec, so `.toISOString()` correctly shifts to UTC.  This avoids the
 * previous bug where we appended `Z` directly, sending local time as UTC.
 */
export function datetimeLocalToIso(value: string): string {
  if (!value) {
    return "";
  }
  const d = new Date(value);
  if (!Number.isFinite(d.getTime())) {
    return "";
  }
  return d.toISOString();
}
