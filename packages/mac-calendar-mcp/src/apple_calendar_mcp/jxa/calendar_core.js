const Calendar = Application("Calendar");
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

  listCalendars() {
    const calendars = Calendar.calendars();
    const results = [];
    for (let cal of calendars) {
      results.push({
        id: cal.calendarIdentifier(),
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
    const id = calendar.calendarIdentifier();
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
      calendar_id: calendar.calendarIdentifier(),
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

  eventsInRange(startValue, endValue, calendarIds) {
    const start = CalendarCore.parseDate(startValue);
    const end = CalendarCore.parseDate(endValue);
    const results = [];
    for (let calendar of Calendar.calendars()) {
      if (!CalendarCore.calendarMatches(calendar, calendarIds)) continue;
      const events = calendar.events.whose({
        _and: [
          { startDate: { _lt: end } },
          { endDate: { _gt: start } }
        ]
      })();
      for (let event of events) {
        results.push(CalendarCore.eventToObject(calendar, event));
      }
    }
    return results;
  }
};
