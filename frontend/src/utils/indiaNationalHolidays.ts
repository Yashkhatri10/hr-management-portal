export type CalendarHoliday = {
  date: string;
  name: string;
};

function dateKey(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

/** India's three nationally observed national days. State and festival holidays vary by location. */
export function getIndiaNationalHolidays(year: number): CalendarHoliday[] {
  return [
    { date: dateKey(year, 0, 26), name: 'Republic Day' },
    { date: dateKey(year, 7, 15), name: 'Independence Day' },
    { date: dateKey(year, 9, 2), name: 'Gandhi Jayanti' },
  ];
}
