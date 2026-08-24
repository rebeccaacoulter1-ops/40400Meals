from tools.update_growth_dashboard import HEADERS, upsert_daily_row


class FakeWorksheet:
    def __init__(self, rows):
        self.rows = [list(row) for row in rows]

    def get_all_values(self):
        return self.rows

    def append_row(self, row, **_kwargs):
        self.rows.append(list(row))

    def update_cell(self, row, column, value):
        self.rows[row - 1][column - 1] = value


def test_creates_header_and_first_daily_row():
    sheet = FakeWorksheet([])
    assert upsert_daily_row(sheet, "2026-08-24", 6, 6) == "created"
    assert sheet.rows == [HEADERS, ["2026-08-24", 6, 6]]


def test_updates_existing_date_without_duplicate():
    sheet = FakeWorksheet([HEADERS, ["2026-08-24", "5", "5"]])
    assert upsert_daily_row(sheet, "2026-08-24", 6, 6) == "updated"
    assert sheet.rows == [HEADERS, ["2026-08-24", 6, 6]]


def test_preserves_unmanaged_columns():
    rows = [[*HEADERS, "Traffic", "Revenue"], ["2026-08-24", "5", "5", "99", "$1"]]
    sheet = FakeWorksheet(rows)
    upsert_daily_row(sheet, "2026-08-24", 6, 6)
    assert sheet.rows[1][3:] == ["99", "$1"]


def test_rejects_missing_required_columns():
    sheet = FakeWorksheet([["Date", "Traffic"]])
    try:
        upsert_daily_row(sheet, "2026-08-24", 6, 6)
    except ValueError as error:
        assert "Recipes Published" in str(error)
    else:
        raise AssertionError("Expected ValueError")
