ObjC.import("EventKit");
ObjC.import("Foundation");

const EventKitCore = {
  entityTypeEvent: 0,
  authorizedStatus: 3,

  unwrap(value) {
    if (value === null || value === undefined) return null;
    try {
      return ObjC.unwrap(value);
    } catch (e) {
      return value;
    }
  },

  string(value) {
    const unwrapped = EventKitCore.unwrap(value);
    if (unwrapped === null || unwrapped === undefined) return "";
    return String(unwrapped);
  },

  array(value) {
    const unwrapped = EventKitCore.unwrap(value);
    return Array.isArray(unwrapped) ? unwrapped : [];
  },

  date(value) {
    if (!value) return null;
    const seconds = Number(value.timeIntervalSince1970);
    if (!Number.isFinite(seconds)) return null;
    return new Date(seconds * 1000).toISOString();
  },

  nsDate(value) {
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) {
      throw new Error(`Invalid EventKit date: ${value}`);
    }
    return $.NSDate.dateWithTimeIntervalSince1970(date.getTime() / 1000);
  },

  calendarId(calendar) {
    return EventKitCore.string(calendar.calendarIdentifier);
  },

  calendarName(calendar) {
    return EventKitCore.string(calendar.title);
  },

  calendarToObject(calendar) {
    const source = calendar.source;
    return {
      id: EventKitCore.calendarId(calendar),
      name: EventKitCore.calendarName(calendar),
      color: null,
      writable: Boolean(calendar.allowsContentModifications),
      description: source ? EventKitCore.string(source.title) : null
    };
  },

  eventStatus(value) {
    return ["none", "confirmed", "tentative", "canceled"][Number(value)] || "";
  },

  participantStatus(value) {
    return [
      "unknown",
      "pending",
      "accepted",
      "declined",
      "tentative",
      "delegated",
      "completed",
      "in_process"
    ][Number(value)] || "unknown";
  },

  attendeeToObject(attendee) {
    let email = "";
    if (attendee.URL) {
      email = EventKitCore.string(attendee.URL.absoluteString);
      if (email.startsWith("mailto:")) email = email.slice(7);
    }
    return {
      display_name: EventKitCore.string(attendee.name) || null,
      email: email || null,
      participation_status: EventKitCore.participantStatus(
        attendee.participantStatus
      )
    };
  },

  eventToObject(event) {
    const start = EventKitCore.date(event.startDate);
    const calendar = event.calendar;
    const baseId =
      EventKitCore.string(event.calendarItemIdentifier) ||
      EventKitCore.string(event.eventIdentifier);
    let url = "";
    if (event.URL) url = EventKitCore.string(event.URL.absoluteString);
    return {
      event_id: `${baseId}:${start}`,
      calendar_id: EventKitCore.calendarId(calendar),
      calendar_name: EventKitCore.calendarName(calendar),
      title: EventKitCore.string(event.title),
      location: EventKitCore.string(event.location),
      notes: EventKitCore.string(event.notes),
      url: url,
      status: EventKitCore.eventStatus(event.status),
      all_day: Boolean(event.allDay),
      start_date: start,
      end_date: EventKitCore.date(event.endDate),
      modified_at: EventKitCore.date(event.lastModifiedDate),
      recurrence: "",
      excluded_dates: [],
      attendees: EventKitCore.array(event.attendees).map(
        EventKitCore.attendeeToObject
      )
    };
  },

  snapshot(startValue, endValue, calendarNamesOrIds) {
    const status = Number(
      $.EKEventStore.authorizationStatusForEntityType(
        EventKitCore.entityTypeEvent
      )
    );
    if (status !== EventKitCore.authorizedStatus) {
      throw new Error(`EventKit calendar access unavailable: status=${status}`);
    }

    const store = $.EKEventStore.alloc.init;
    const requested = calendarNamesOrIds || [];
    const allCalendars = EventKitCore.array(
      store.calendarsForEntityType(EventKitCore.entityTypeEvent)
    );
    const selected = allCalendars.filter((calendar) => {
      if (requested.length === 0) return true;
      return (
        requested.indexOf(EventKitCore.calendarId(calendar)) !== -1 ||
        requested.indexOf(EventKitCore.calendarName(calendar)) !== -1
      );
    });
    if (requested.length > 0 && selected.length === 0) {
      throw new Error("Configured EventKit calendars were not found");
    }

    const predicate = store.predicateForEventsWithStartDateEndDateCalendars(
      EventKitCore.nsDate(startValue),
      EventKitCore.nsDate(endValue),
      $(selected)
    );
    const events = EventKitCore.array(store.eventsMatchingPredicate(predicate));
    return {
      source: "eventkit",
      calendars: selected.map(EventKitCore.calendarToObject),
      events: events.map(EventKitCore.eventToObject),
      failed_jobs: []
    };
  }
};
