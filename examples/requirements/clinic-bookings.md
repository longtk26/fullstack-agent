# Bright Smile Clinic — appointment booking for a dental clinic

**Mode:** dynamic (web app with its own backend)
**Matches:** `specs/clinic-bookings.json` + `app-outlines/clinic-bookings.json` (drafted by Gemini on 2026-11-06, Story 23.0; the fake engine replays it)

Appointment booking for a dental clinic with four dentists. Patients sign up and book an appointment with a dentist
for a treatment (check-up, cleaning, filling, whitening) at a date and time; each treatment has a duration in minutes
and a price. A dentist cannot have two appointments at the same time. Appointments are requested, then confirmed or
cancelled by the front desk, and marked completed after the visit.

The front desk sees the day's and the week's appointments at a glance and confirms new requests. Patients see
their own upcoming appointments and can cancel them.

Start with the four dentists (with a photo and a speciality), the four treatments and some appointments this week.
