function getCalendarApplication() {
  const candidates = [
    "/System/Applications/Calendar.app",
    "/Applications/Calendar.app",
    "Calendar"
  ];
  let lastError = null;
  for (const candidate of candidates) {
    try {
      const app = Application(candidate);
      app.name();
      return app;
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError || new Error("Calendar application not found");
}

const Calendar = getCalendarApplication();
Calendar.includeStandardAdditions = true;

const CalendarCore = {
  formatDate(date) {
    if (!date) return null;
    try {
      return new Date(date).toISOString();
    } catch (e) {
      return null;
    }
  },

  parseDate(value) {
    if (!value) return null;
    return new Date(value);
  },

  today() {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  },

  safeCalendarId(calendar) {
    try {
      return String(calendar["calendarIdentifier"]());
    } catch (e) {
      const name = calendar.name();
      const color = String(calendar.color());
      const description = calendar.description() || "";
      return `fallback:${name}:${color}:${description}`;
    }
  },

  listCalendars() {
    const calendars = Calendar.calendars();
    const results = [];
    for (let cal of calendars) {
      results.push({
        id: CalendarCore.safeCalendarId(cal),
        name: cal.name(),
        color: String(cal.color()),
        writable: cal.writable(),
        description: cal.description() || null
      });
    }
    return results;
  },

  calendarMatches(calendar, ids) {
    if (!ids || ids.length === 0) return true;
    const id = CalendarCore.safeCalendarId(calendar);
    const name = calendar.name();
    return ids.indexOf(id) !== -1 || ids.indexOf(name) !== -1;
  },

  eventToObject(calendar, event) {
    let attendees = [];
    try {
      attendees = event.attendees().map((att) => ({
        display_name: att.displayName() || null,
        email: att.email() || null,
        participation_status: String(att.participationStatus()) || null
      }));
    } catch (e) {}
    return {
      event_id: event.uid(),
      calendar_id: CalendarCore.safeCalendarId(calendar),
      calendar_name: calendar.name(),
      title: event.summary() || "",
      location: event.location() || "",
      notes: event.description() || "",
      url: event.url() || "",
      status: String(event.status()) || "",
      all_day: event.alldayEvent(),
      start_date: CalendarCore.formatDate(event.startDate()),
      end_date: CalendarCore.formatDate(event.endDate()),
      modified_at: CalendarCore.formatDate(event.stampDate()),
      recurrence: event.recurrence() || "",
      excluded_dates: (event.excludedDates() || []).map(
        CalendarCore.formatDate
      ),
      attendees: attendees
    };
  },

  eventOverlapsRange(event, start, end) {
    const eventStart = event.startDate();
    const eventEnd = event.endDate();
    if (!eventStart || !eventEnd) return false;
    return eventStart < end && eventEnd > start;
  },

  eventsInRange(startValue, endValue, calendarIds) {
    const start = CalendarCore.parseDate(startValue);
    const end = CalendarCore.parseDate(endValue);
    if (!start || !end || start >= end) return [];
    const results = [];
    for (let calendar of Calendar.calendars()) {
      if (!CalendarCore.calendarMatches(calendar, calendarIds)) continue;
      const events = calendar.events.whose({
        endDate: { _greaterThan: start }
      })();
      for (let event of events) {
        if (!CalendarCore.eventOverlapsRange(event, start, end)) continue;
        results.push(CalendarCore.eventToObject(calendar, event));
      }
    }
    return results;
  }
};
